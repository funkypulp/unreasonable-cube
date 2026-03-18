// cubebot_esp32.ino — CubeBot firmware
//
// Display: 3x3 Rubik's grid (like teammate's working code)
// Visible area: 2.25"x2.25" (~300x300px) centered on 4" screen
// Encoder: rotates orbit cells locally + sends event to laptop
//
// Libraries: Arduino_GFX_Library, ArduinoJson

#include <Arduino_GFX_Library.h>
#include <ArduinoJson.h>

// ── Rubik's colors (RGB565) ───────────────────────────────────────
#define RUB_RED     0xF800
#define RUB_ORANGE  0xFD20
#define RUB_YELLOW  0xFFE0
#define RUB_GREEN   0x07E0
#define RUB_BLUE    0x001F
#define RUB_WHITE   0xFFFF
#define HEX_BLACK   0x0000
#define HEX_GREY    0x7BEF

uint16_t RCOLORS[] = {RUB_RED, RUB_ORANGE, RUB_YELLOW,
                      RUB_GREEN, RUB_BLUE, RUB_WHITE};

// ── Board ID ──────────────────────────────────────────────────────
#define BOARD_ID 1
#if BOARD_ID == 1
  #define FACE_A 0
  #define FACE_B 1
#elif BOARD_ID == 2
  #define FACE_A 2
  #define FACE_B 3
#else
  #define FACE_A 4
  #define FACE_B 5
#endif

// ── Pins ──────────────────────────────────────────────────────────
#define TFT_SCK  18
#define TFT_MOSI 23
#define TFT_RST  32
#define TFT_CS1  2
#define TFT_DC1  21
#define TFT_CS2  5
#define TFT_DC2  19
#define ENC_CLK  33
#define ENC_DT   25
#define ENC_BTN  26

// ── Screens ───────────────────────────────────────────────────────
Arduino_DataBus *bus1 = new Arduino_ESP32SPI(TFT_DC1, TFT_CS1, TFT_SCK, TFT_MOSI, -1);
Arduino_GFX    *gfx1  = new Arduino_ST7796(bus1, TFT_RST, 3, false, 320, 480);
Arduino_DataBus *bus2 = new Arduino_ESP32SPI(TFT_DC2, TFT_CS2, TFT_SCK, TFT_MOSI, -1);
Arduino_GFX    *gfx2  = new Arduino_ST7796(bus2, TFT_RST, 3, false, 320, 480);

// ── Grid state ────────────────────────────────────────────────────
int gridA[9];
int gridB[9];

String labelA    = "";
String labelB    = "";
bool selectedA   = false;
bool selectedB   = false;

// Weights for each face (6 perspectives: red,orange,yellow,green,blue,white)
float weightsA[6] = {0.17, 0.17, 0.17, 0.17, 0.17, 0.17};
float weightsB[6] = {0.17, 0.17, 0.17, 0.17, 0.17, 0.17};

// ── Grid layout ───────────────────────────────────────────────────
// Visible 2.25"x2.25" ≈ 300x300px centered on 480x320 screen
// Match teammate's offset: offX = (480-300)/2 + 20, offY = (320-300)/2
#define CELL_SIZE  100
#define CELL_DRAW   88   // cell size minus gap
#define GRID_OFF_X 110
#define GRID_OFF_Y  10

// ── Encoder state ─────────────────────────────────────────────────
int  lastClk      = HIGH;
int  stepCounter  = 0;
bool btnLastState = false;
bool btnHandled   = false;
unsigned long btnPressTime = 0;

// ── Color map ─────────────────────────────────────────────────────
int colorIndex(const String &name) {
  if (name == "red")    return 0;
  if (name == "orange") return 1;
  if (name == "yellow") return 2;
  if (name == "green")  return 3;
  if (name == "blue")   return 4;
  if (name == "white")  return 5;
  return 5;
}

// ── Init grid to solid color ──────────────────────────────────────
void initGrid(int *grid, int colorIdx) {
  for (int i = 0; i < 9; i++) grid[i] = colorIdx;
}

// ── Weight-based grid fill ───────────────────────────────────────
// Fills 9 cells with colors proportional to 6 perspective weights.
// Center cell (index 4) reserved for label — filled separately.
// weights[6]: float 0.0–1.0 for each color (red,orange,yellow,green,blue,white)

// Cell draw order — skip center (4), fill 8 outer cells by weight
int outerCells[] = {0, 1, 2, 3, 5, 6, 7, 8};

void fillGridFromWeights(int *grid, float weights[6]) {
  // Convert weights to cell counts out of 8 outer cells
  // Use a simple largest-remainder allocation
  float total = 0;
  for (int i = 0; i < 6; i++) total += weights[i];
  if (total <= 0) total = 1;

  int counts[6] = {0};
  float remainders[6];
  int assigned = 0;

  for (int i = 0; i < 6; i++) {
    float exact = (weights[i] / total) * 8.0;
    counts[i] = (int)exact;
    remainders[i] = exact - counts[i];
    assigned += counts[i];
  }

  // Distribute remaining cells to largest remainders
  while (assigned < 8) {
    int best = 0;
    for (int i = 1; i < 6; i++)
      if (remainders[i] > remainders[best]) best = i;
    counts[best]++;
    remainders[best] = 0;
    assigned++;
  }

  // Fill outer cells with colors in proportion
  int pos = 0;
  for (int c = 0; c < 6; c++) {
    for (int n = 0; n < counts[c]; n++) {
      grid[outerCells[pos++]] = c;
    }
  }
  // Shuffle outer cells so colors aren't just grouped in blocks
  // Simple Fisher-Yates with millis() seed
  for (int i = 7; i > 0; i--) {
    int j = (millis() * (i + 1)) % (i + 1);
    int tmp = grid[outerCells[i]];
    grid[outerCells[i]] = grid[outerCells[j]];
    grid[outerCells[j]] = tmp;
  }
}

// ── Draw grid ─────────────────────────────────────────────────────
void drawGrid(Arduino_GFX *gfx, int *grid, const String &label, bool selected) {
  gfx->fillScreen(HEX_BLACK);

  // Draw 3x3 cells
  for (int i = 0; i < 9; i++) {
    int x = GRID_OFF_X + (i % 3) * CELL_SIZE + 6;
    int y = GRID_OFF_Y + (i / 3) * CELL_SIZE + 6;
    gfx->fillRect(x, y, CELL_DRAW, CELL_DRAW, RCOLORS[grid[i]]);
  }

  // Center cell (index 4): overlay label text (1-2 words, line break if 2)
  if (label.length() > 0) {
    int cx = GRID_OFF_X + 1 * CELL_SIZE + 6;
    int cy = GRID_OFF_Y + 1 * CELL_SIZE + 6;

    // Black out center cell
    gfx->fillRect(cx, cy, CELL_DRAW, CELL_DRAW, HEX_BLACK);
    gfx->setTextColor(RUB_WHITE);
    gfx->setTextSize(1);

    // Split on first space if two words
    int spaceIdx = label.indexOf(' ');
    if (spaceIdx == -1) {
      // Single word — center vertically and horizontally
      int charWidth = 6;
      int textX = cx + (CELL_DRAW - label.length() * charWidth) / 2;
      int textY = cy + CELL_DRAW / 2 - 4;
      gfx->setCursor(max(cx + 2, textX), textY);
      gfx->print(label);
    } else {
      // Two words — draw each on its own line, centered
      String word1 = label.substring(0, spaceIdx);
      String word2 = label.substring(spaceIdx + 1);
      int charWidth = 6;
      int x1 = cx + (CELL_DRAW - word1.length() * charWidth) / 2;
      int x2 = cx + (CELL_DRAW - word2.length() * charWidth) / 2;
      gfx->setCursor(max(cx + 2, x1), cy + CELL_DRAW / 2 - 10);
      gfx->print(word1);
      gfx->setCursor(max(cx + 2, x2), cy + CELL_DRAW / 2 + 2);
      gfx->print(word2);
    }
  }

  // Selected: white border around entire grid
  if (selected) {
    gfx->drawRect(GRID_OFF_X + 2, GRID_OFF_Y + 2, 298, 298, RUB_WHITE);
    gfx->drawRect(GRID_OFF_X + 4, GRID_OFF_Y + 4, 294, 294, RUB_WHITE);
  }
}

// ── Idle screen ───────────────────────────────────────────────────
void drawIdle(Arduino_GFX *gfx) {
  gfx->fillScreen(HEX_BLACK);
  gfx->setTextColor(HEX_GREY);
  gfx->setTextSize(2);
  gfx->setCursor(GRID_OFF_X + 20, GRID_OFF_Y + 130);
  gfx->println("waiting");
}

// ── Handle JSON from laptop ───────────────────────────────────────
void handleMessage(const String &line) {
  StaticJsonDocument<256> doc;
  if (deserializeJson(doc, line) != DeserializationError::Ok) return;

  String cmd  = doc["cmd"] | "";
  int faceIdx = doc["face"] | -1;

  // init: solid single color — weights only affect grid after rotation
  if (cmd == "init") {
    int colorIdx = colorIndex(doc["color"] | "white");
    if (faceIdx == FACE_A) {
      labelA = doc["label"] | "";
      selectedA = false;
      for (int i = 0; i < 9; i++) gridA[i] = colorIdx;  // solid color
      drawGrid(gfx1, gridA, labelA, false);
    } else if (faceIdx == FACE_B) {
      labelB = doc["label"] | "";
      selectedB = false;
      for (int i = 0; i < 9; i++) gridB[i] = colorIdx;  // solid color
      drawGrid(gfx2, gridB, labelB, false);
    }
  }

  // select: highlight the face
  else if (cmd == "select") {
    if (faceIdx == FACE_A) { selectedA = true;  drawGrid(gfx1, gridA, labelA, true); }
    if (faceIdx == FACE_B) { selectedB = true;  drawGrid(gfx2, gridB, labelB, true); }
  }

  // deselect: remove highlight
  else if (cmd == "deselect") {
    if (faceIdx == FACE_A) { selectedA = false; drawGrid(gfx1, gridA, labelA, false); }
    if (faceIdx == FACE_B) { selectedB = false; drawGrid(gfx2, gridB, labelB, false); }
  }

  // story: show word on center cell
  else if (cmd == "story") {
    String word = doc["word"] | "";
    if (faceIdx == FACE_A) {
      drawGrid(gfx1, gridA, "", false);
      gfx1->setTextColor(HEX_BLACK);
      gfx1->setTextSize(2);
      gfx1->setCursor(GRID_OFF_X + CELL_SIZE + 10, GRID_OFF_Y + CELL_SIZE + 30);
      gfx1->println(word.substring(0, 8));
    }
    if (faceIdx == FACE_B) {
      drawGrid(gfx2, gridB, "", false);
      gfx2->setTextColor(HEX_BLACK);
      gfx2->setTextSize(2);
      gfx2->setCursor(GRID_OFF_X + CELL_SIZE + 10, GRID_OFF_Y + CELL_SIZE + 30);
      gfx2->println(word.substring(0, 8));
    }
  }

  // weights — update weights and reshuffle grid
  else if (cmd == "weights") {
    float w[6] = {0.17, 0.17, 0.17, 0.17, 0.17, 0.17};
    if (doc.containsKey("weights")) {
      JsonArray wa = doc["weights"].as<JsonArray>();
      for (int i = 0; i < 6 && i < (int)wa.size(); i++) w[i] = wa[i].as<float>();
    }
    if (faceIdx == FACE_A) {
      for (int i = 0; i < 6; i++) weightsA[i] = w[i];
      fillGridFromWeights(gridA, weightsA);
      drawGrid(gfx1, gridA, labelA, selectedA);
    } else if (faceIdx == FACE_B) {
      for (int i = 0; i < 6; i++) weightsB[i] = w[i];
      fillGridFromWeights(gridB, weightsB);
      drawGrid(gfx2, gridB, labelB, selectedB);
    }
  }

  // redraw — force refresh of current grid state
  else if (cmd == "redraw") {
    if      (faceIdx == FACE_A) drawGrid(gfx1, gridA, labelA, selectedA);
    else if (faceIdx == FACE_B) drawGrid(gfx2, gridB, labelB, selectedB);
  }

  // reset
  else if (cmd == "reset") {
    initGrid(gridA, 0); initGrid(gridB, 1);
    labelA = ""; labelB = "";
    selectedA = false; selectedB = false;
    drawIdle(gfx1); drawIdle(gfx2);
  }
}

// ── Send events ───────────────────────────────────────────────────
void sendRotate(bool clockwise) {
  StaticJsonDocument<64> doc;
  doc["event"]     = "rotate";
  doc["face"]      = FACE_A;
  doc["clockwise"] = clockwise;
  serializeJson(doc, Serial);
  Serial.println();
}

void sendButton() {
  StaticJsonDocument<64> doc;
  doc["event"] = "button";
  doc["face"]  = FACE_A;
  serializeJson(doc, Serial);
  Serial.println();
}

// ── Setup ─────────────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);

  pinMode(TFT_RST, OUTPUT);
  digitalWrite(TFT_RST, HIGH); delay(100);
  digitalWrite(TFT_RST, LOW);  delay(500);
  digitalWrite(TFT_RST, HIGH); delay(500);

  if (gfx1->begin(12000000)) { gfx1->setRotation(1); gfx1->fillScreen(HEX_BLACK); }
  if (gfx2->begin(12000000)) { gfx2->setRotation(1); gfx2->fillScreen(HEX_BLACK); }

  initGrid(gridA, FACE_A);
  initGrid(gridB, FACE_B);
  drawIdle(gfx1);
  drawIdle(gfx2);

  pinMode(ENC_CLK, INPUT_PULLUP);
  pinMode(ENC_DT,  INPUT_PULLUP);
  pinMode(ENC_BTN, INPUT_PULLUP);
  lastClk = digitalRead(ENC_CLK);

  StaticJsonDocument<64> doc;
  doc["event"]  = "ready";
  doc["board"]  = BOARD_ID;
  doc["face_a"] = FACE_A;
  doc["face_b"] = FACE_B;
  serializeJson(doc, Serial);
  Serial.println();
}

// ── Loop ──────────────────────────────────────────────────────────
void loop() {

  // Encoder rotation
  int curClk = digitalRead(ENC_CLK);
  if (curClk != lastClk && curClk == LOW) {
    bool cw = (digitalRead(ENC_DT) != curClk);
    if (cw) stepCounter++; else stepCounter--;
    if (abs(stepCounter) >= 5) {
      bool clockwise = (stepCounter > 0);
      // Scatter 2-3 random cells to mimic multi-side rotation
      for (int n = 0; n < 2 + (millis() % 2); n++) {
        int cell = millis() % 8;  // outer cells 0-7 (skip center 4 handled in draw)
        if (cell >= 4) cell++;    // skip index 4
        gridA[cell] = (gridA[cell] + 1 + (millis() % 2)) % 6;
        gridB[cell] = (gridB[cell] + 1 + (millis() % 3)) % 6;
      }
      drawGrid(gfx1, gridA, labelA, selectedA);
      drawGrid(gfx2, gridB, labelB, selectedB);
      // Tell laptop for weight calculation
      sendRotate(clockwise);
      stepCounter = 0;
    }
  }
  lastClk = curClk;

  // Button
  bool btnState = (digitalRead(ENC_BTN) == LOW);
  if (btnState && !btnLastState) {
    btnPressTime = millis();
    btnHandled   = false;
  }
  if (btnState && !btnHandled && (millis() - btnPressTime > 50)) {
    sendButton();
    btnHandled = true;
  }
  btnLastState = btnState;

  // Serial input
  if (Serial.available()) {
    String line = Serial.readStringUntil('\n');
    line.trim();
    if (line.length() > 2) handleMessage(line);
  }
}
