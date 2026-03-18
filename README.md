# Unreasonable Cube

**A tangible AI oracle built from a Rubik's Cube.**

> *When you're stuck on a problem, the worst thing you can do is keep thinking about it the same way.*

![Unreasonable Cube](assets/cube.jpg)

---

## What It Is

Most AI interfaces are linear — you type, it responds, you go deeper into the same thread of thought. Unreasonable Cube is an attempt to break that pattern.

You speak a challenge into the cube. It maps your challenge to **six perspectives** — the different facets of how humans naturally understand a problem: emotional affinity, relationships, timing, systemic forces, blind spots, and the angle you haven't named yet. Each perspective is assigned to a face of the cube.

You then rotate the cube's gears to shift the weight between perspectives, and press a face to select your primary lens. The cube asks up to four follow-up questions shaped by the full weight distribution you've dialed in. Then it speaks a short speculative story — vivid, specific, set seven years from now — that reflects the blend of perspectives you chose.

The experience takes about three minutes. It doesn't give you an answer. It gives you a more honest question.

---

## How It Works

```
You speak a challenge
        ↓
Claude maps it to 6 perspectives (one per face)
        ↓
You rotate the cube → shifts perspective weights
        ↓
You press a face → selects primary lens
        ↓
Claude asks follow-up questions (up to 4)
        ↓
Claude speaks a speculative future story
```

---

## Hardware

- 5× ESP32 microcontrollers
- 5× 4" ST7796 TFT displays
- 5× EC11 rotary encoders
- Custom 3D printed mechanical enclosure with gear-based encoder decoupling system
- Connected to laptop via USB

Each face has one screen, one encoder, and one ESP32. The gear system — designed by Tim — lets you rotate the encoder by turning the outer gear ring without touching or stressing the screen behind it.

---

## Software Stack

| Component | Technology |
|-----------|------------|
| AI | Claude API (claude-sonnet) |
| Speech-to-text | OpenAI Whisper |
| Text-to-speech | macOS native |
| Firmware | Arduino (C++) + Arduino GFX Library |
| Application | Python |

---

## Project Structure

```
cubebot_with_hardware/
├── main.py          — main interaction loop
├── config.py        — serial ports, model settings, tuning
├── ai_brain.py      — Claude API calls (perspectives + story)
├── state.py         — conversation state
├── weights.py       — Rubik's-style weight rotation logic
├── voice.py         — speech input/output
├── serial_comm.py   — USB communication with ESP32s
└── esp32/
    └── cubebot_esp32.ino   — ESP32 firmware
```

---

## Setup

### Requirements
```bash
pip install openai-whisper sounddevice numpy anthropic pyserial
```

### API Key
```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

### Serial Ports
Plug in your ESP32s, find their ports:
```bash
ls /dev/cu.*
```

Update `SERIAL_PORTS` in `config.py` to map each port to the correct face:
```python
SERIAL_PORTS = {
    0: "/dev/cu.usbserial-0001",   # red
    1: "/dev/cu.usbserial-0002",   # orange
    ...
}
```

### Run
```bash
python main.py
```

---

## The Team

Built at the **MIT Hardware + AI Hackathon**

| Person | Role |
|--------|------|

| Tim Qi | Product & Mechanical cube |
| Haoyang Li | Mechanical cube & hardware |
| Pranav Chaparala | Hardware |
| Shu Ou | Software & AI |

---

## Devpost

[Read the full project writeup →](https://devpost.com/software/team-18-unreasonable-cube)
