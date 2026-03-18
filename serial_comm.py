# serial_comm.py — USB serial bridge to real ESP32 boards

import json
import threading
import time
import sys

try:
    import serial
    import serial.tools.list_ports
except ImportError:
    print("\n[ERROR] pip install pyserial\n")
    sys.exit(1)

from config import SERIAL_PORTS, BAUD_RATE, COLORS


class SerialComm:

    def __init__(self, event_cb):
        self.event_cb  = event_cb
        self.ports     = {}
        self.face_map  = {}
        self._running  = True
        self._lock     = threading.Lock()   # protects all serial writes
        self._connect_all()

    # ── Connection ────────────────────────────────────────────────

    def _connect_all(self):
        for port in SERIAL_PORTS:
            try:
                s = serial.Serial(port, BAUD_RATE, timeout=0.1)
                time.sleep(0.1)   # let port settle
                s.reset_input_buffer()
                s.reset_output_buffer()
                self.ports[port] = s
                print(f"[serial] Connected: {port}")
                threading.Thread(
                    target=self._read_loop,
                    args=(port, s),
                    daemon=True
                ).start()
            except serial.SerialException as e:
                print(f"[serial] Could not open {port}: {e}")
                print("  Available ports:")
                for p in serial.tools.list_ports.comports():
                    print(f"    {p.device} — {p.description}")

        # Wait for ESP32 ready events
        print("[serial] Waiting for boards to announce...")
        deadline = time.time() + 5.0
        while time.time() < deadline:
            if len(self.face_map) >= 2:
                break
            time.sleep(0.05)
        if self.face_map:
            print(f"[serial] Faces registered: {sorted(self.face_map.keys())}")
        else:
            print("[serial] Warning: no ready events received — will try anyway")

    # ── Reader thread (one per port) ──────────────────────────────

    def _read_loop(self, port_path, ser):
        buffer = ""
        while self._running:
            try:
                raw = ser.read(64)   # blocking read with timeout=0.1
                if raw:
                    buffer += raw.decode("utf-8", errors="ignore")
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        line = line.strip()
                        if line:
                            self._handle_incoming(port_path, line)
            except (serial.SerialException, OSError):
                print(f"[serial] Lost connection: {port_path}")
                break

    def _handle_incoming(self, port_path, line):
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            print(f"[serial] Non-JSON: {line}")
            return

        if event.get("event") == "ready":
            fa = event.get("face_a")
            fb = event.get("face_b")
            if fa is not None: self.face_map[fa] = port_path
            if fb is not None: self.face_map[fb] = port_path
            print(f"[serial] Board ready — faces {fa},{fb} on {port_path}")
            return

        print(f"[serial] ← {event}")
        self.event_cb(event)

    # ── Thread-safe write ─────────────────────────────────────────

    def _send_json(self, face_index, payload):
        path = self.face_map.get(face_index)
        if not path:
            # fallback to first port
            if not self.ports:
                return
            path = list(self.ports.keys())[0]
        ser = self.ports.get(path)
        if not ser:
            return
        with self._lock:
            try:
                ser.write((json.dumps(payload) + "\n").encode("utf-8"))
                ser.flush()
            except serial.SerialException as e:
                print(f"[serial] Write error: {e}")

    # ── Public API ────────────────────────────────────────────────

    def send_all_faces(self, dimensions):
        print("[serial] Sending face data...")
        for d in dimensions:
            self._send_json(d["id"], {
                "cmd":   "init",
                "face":  d["id"],
                "color": d["color"],
                "label": d["label"],
            })
            time.sleep(0.08)   # give ESP32 time to process + draw each face

        # Explicit redraw after all inits sent
        time.sleep(0.2)
        for i in range(6):
            self._send_json(i, {"cmd": "redraw", "face": i})
            time.sleep(0.08)
        print("[serial] All faces initialised.")

    def send(self, face_index, payload):
        self._send_json(face_index, payload)

    def show_weights(self, weights, selected=None):
        pass   # weights shown via grid rotation on ESP32 side

    def show_story(self, text):
        words = text.split()
        chunk = max(1, len(words) // 6)
        for i in range(6):
            word = words[i * chunk] if i * chunk < len(words) else ""
            self._send_json(i, {"cmd": "story", "face": i, "word": word})
            time.sleep(0.08)

    def reset(self):
        for i in range(6):
            self._send_json(i, {"cmd": "reset", "face": i})
            time.sleep(0.05)

    def stop(self):
        self._running = False
        for ser in self.ports.values():
            try: ser.close()
            except: pass
        print("[serial] Ports closed.")
