# ============================================================
#  main_with_hardware.py — CubeBot (REAL ESP32 cube)
#  Run: python main.py
#  Hardware: ESP32-S3 via USB serial, ST7796 screens, EC11 encoders
#  Use this for: physical cube testing and demos
#  Before running: set SERIAL_PORTS in config.py
# ============================================================

# main.py — CubeBot entry point
#
# Run with mock hardware:   python main.py
# Run with real cube:       set USE_MOCK_HARDWARE = False in config.py

import time
import sys
from config import USE_MOCK_HARDWARE, ANTHROPIC_API_KEY, COLORS, WAKE_PHRASE, WAKE_MODE, MAX_FOLLOWUPS

# ── Validate API key ──────────────────────────────────────────────
if not ANTHROPIC_API_KEY:
    print("\n[ERROR] ANTHROPIC_API_KEY not set.")
    print("  Fix: export ANTHROPIC_API_KEY=sk-ant-...\n")
    sys.exit(1)

# ── Import hardware layer ─────────────────────────────────────────
if False:  # always real hardware in this folder
    from serial_comm import SerialComm as Hardware
    print("[main] Using MOCK hardware (keyboard input).")
else:
    from serial_comm import SerialComm as Hardware
    print("[main] Using REAL hardware (USB serial).")

from voice    import listen_for_wake, record_challenge, speak, preload
from state    import ConversationState
from weights  import rotate_weights
from ai_brain import ai_generate_perspectives, ai_respond


# ── Global state ──────────────────────────────────────────────────
state    = ConversationState()
hardware = None


# ── Hardware event callback ───────────────────────────────────────

def on_hardware_event(event: dict):
    """
    Called from background threads when hardware fires an event.
    Handles two event types:
      - rotate: encoder turned → cycle adjacent face weights
      - button: encoder pressed → select that face
    """
    print(f"[main] ← Hardware event: {event} (phase={state.phase})")
    if event.get("event") == "rotate":
        face_index = event["face"]
        clockwise  = event["clockwise"]
        face_color = COLORS[face_index]

        # Rotate adjacent weights Rubik's-cube style
        state.weights = rotate_weights(state.weights, face_color, clockwise)

        # Push updated weights to all screens
        if hardware and state.phase == "explore":
            hardware.show_weights(state.weights, state.selected_face)

    elif event.get("event") == "button":
        state.pending_selection = event["face"]


# ── Phase handlers ────────────────────────────────────────────────

def phase_idle() -> bool:
    """Wake word or Enter key, depending on WAKE_MODE."""
    if WAKE_MODE == "enter":
        input("\n[CubeBot] Press Enter to start a new session...")
        return True
    elif WAKE_MODE == "voice":
        print(f"\n[CubeBot] Listening for '{WAKE_PHRASE}'...")
        return listen_for_wake()
    else:  # "both"
        import threading
        triggered = [False]
        def wait_enter():
            input(f"\n[CubeBot] Say '{WAKE_PHRASE}' or press Enter...")
            triggered[0] = True
        threading.Thread(target=wait_enter, daemon=True).start()
        while not triggered[0]:
            if listen_for_wake():
                return True
        return True


def phase_listening() -> str:
    """Record and transcribe. Returns transcript or empty string."""
    text = record_challenge()
    if not text.strip():
        speak("Sorry, I didn't catch that. Try again.")
        return ""
    return text


def phase_generating(challenge: str):
    """Generate 6 perspectives, send to cube screens."""
    speak("Thinking about your challenge.")
    dims = ai_generate_perspectives(challenge)
    state.set_perspectives(dims)
    hardware.send_all_faces(dims)

    print("\n[main] ── Perspectives ──")
    for d in dims:
        print(f"  [{d['color'].upper():6}] {d['label']:<22} — {d['descriptor']}")

    speak(
        "I've mapped your challenge to six perspectives. "
        "Rotate the faces to shape the weights, "
        "then press a face when you're ready."
    )

    # Show initial equal weights
    hardware.show_weights(state.weights)


def phase_explore() -> int:
    """
    Wait for a button press event.
    During this phase, rotate events update weights in real time via callback.
    Returns the selected face index.
    """
    state.phase = "explore"

    if False:  # always real hardware in this folder
        print("\n[CubeBot] Rotate faces (r/l + number) or press a face (p/number):")
        print("  Example: r 0  →  rotate red face clockwise")
        print("           p 2  →  press yellow face\n")

    # Wait for a button press — rotations are handled by the callback
    print("\n[CubeBot] Rotate faces to shape weights, then press encoder to select...")
    print(f"[main] Waiting for button press (pending={state.pending_selection})")
    while state.pending_selection is None:
        time.sleep(0.05)
    print(f"[main] Button press received: face {state.pending_selection}")

    face = state.pending_selection
    state.pending_selection = None
    state.selected_face = face

    sel_color = COLORS[face]
    sel_dim   = state.get_perspective(face)
    sel_label = sel_dim["label"] if sel_dim else sel_color

    hardware.send(face, {"cmd": "select", "face": face})

    print(f"\n[main] Selected: face {face} — {sel_color} — '{sel_label}'"  )

    return face


def phase_respond(face: int) -> str:
    """Call Claude, speak response. Returns 'followup' or 'story'."""
    response = ai_respond(state, face)

    if response["type"] == "followup":
        question = response["question"]
        state.add_followup_question(question)

        print(f"\n[main] Follow-up: {question}")
        speak(question)
        # Deselect so user knows to rotate/pick again
        hardware.send(face, {"cmd": "deselect", "face": face})
        return "followup"

    else:
        story = response["story"]
        hardware.show_story(story)
        print(f"\n[main] ── Speculative Future ──\n{story}\n")
        speak(story, slow=True)
        return "story"


# ── Restart ───────────────────────────────────────────────────────

def prompt_restart() -> bool:
    print("\n" + "─" * 40)
    print("  Session complete.")
    print("─" * 40)
    choice = input("  New session? (Enter = yes, q = quit): ").strip().lower()
    return choice != "q"


# ── Main loop ─────────────────────────────────────────────────────

def main():
    global hardware

    print("\n" + "=" * 55)
    print("  CubeBot — Tangible AI Oracle")
    print(f"  Hardware : {'MOCK (keyboard)' if USE_MOCK_HARDWARE else 'REAL (USB)'}")
    print(f"  Wake mode: {WAKE_MODE}")
    print("=" * 55 + "\n")

    preload()   # load Whisper before first session
    hardware = Hardware(on_hardware_event)

    # Load Whisper into RAM now so first recording has no delay
    preload()

    try:
        while True:
            state.reset()
            state.phase = "idle"

            # 1. Wake
            if not phase_idle():
                continue
            speak("I'm listening. What's your challenge?")
            state.phase = "listening"

            # 2. Record challenge
            challenge = phase_listening()
            if not challenge:
                continue
            state.add_input(challenge)

            # 3. Generate perspectives
            state.phase = "generating"
            phase_generating(challenge)

            # 4. User selects face once via button press
            face = phase_explore()

            # 5. Conversation loop — fully voice driven after initial selection
            while True:
                result = phase_respond(face)

                if result == "story":
                    if not prompt_restart():
                        print("\n[CubeBot] Goodbye.\n")
                        return
                    break

                # Follow-up: brief pause so mic doesn't catch TTS tail, then listen
                state.phase = "listening"
                time.sleep(0.5)
                print(f"[main] Listening for follow-up answer ({state.followup_count}/{MAX_FOLLOWUPS})...")
                answer = phase_listening()
                if answer:
                    state.add_input(answer)
                    print(f"[main] Answer recorded: '{answer[:50]}'")

    except KeyboardInterrupt:
        print("\n\n[CubeBot] Shutting down.")
        if hasattr(hardware, "stop"):
            hardware.stop()


if __name__ == "__main__":
    main()
