# CubeBot — with_hardware

Single ESP32-S3 + ST7796 4" TFT + EC11 encoder test.
Face 0 (Red) only for now — expand to all 6 once validated.

## Setup

### 1. Install Python dependencies
```bash
pip install pyserial openai-whisper sounddevice numpy
```

### 2. Flash the ESP32

Open `esp32/cubebot_esp32.ino` in Arduino IDE.

**Board settings:**
- Board: ESP32S3 Dev Module
- USB Mode: USB-OTG (TinyUSB)
- Upload Speed: 921600

**Before flashing, edit TFT_eSPI/User_Setup.h:**
```cpp
#define ST7796_DRIVER
#define TFT_WIDTH  320
#define TFT_HEIGHT 480
#define TFT_MOSI   11
#define TFT_SCLK   12
#define TFT_CS     10
#define TFT_DC      9
#define TFT_RST     8
#define SPI_FREQUENCY 40000000
```

**Libraries needed (Arduino Library Manager):**
- TFT_eSPI (by Bodmer)
- ArduinoJson

### 3. Wiring

| ST7796 Pin | ESP32-S3 Pin |
|------------|--------------|
| MOSI       | GPIO 11      |
| SCLK       | GPIO 12      |
| CS         | GPIO 10      |
| DC         | GPIO 9       |
| RST        | GPIO 8       |
| VCC        | 3.3V         |
| GND        | GND          |

| EC11 Pin | ESP32-S3 Pin |
|----------|--------------|
| CLK (A)  | GPIO 4       |
| DT  (B)  | GPIO 5       |
| SW       | GPIO 6       |
| +        | 3.3V         |
| GND      | GND          |

### 4. Find your serial port
```bash
ls /dev/cu.usb*
```
Update `SERIAL_PORTS` in `config.py` with the correct port.

### 5. Run
```bash
export ANTHROPIC_API_KEY=sk-ant-...
python main.py
```

## What to expect
1. Screen shows "waiting..." on boot
2. Press Enter on laptop → speak challenge
3. Screen updates with dimension label + weight bar
4. Turn encoder → weight bar updates on screen
5. Press encoder button → triggers AI response
6. Story appears on screen + spoken aloud

## If the screen is blank
- Check TFT_eSPI User_Setup.h pins match your wiring
- Try `tft.setRotation(1)` in the .ino if orientation is wrong
- Verify 3.3V supply — 5V will damage the screen
