# state.py — conversation state machine

from config import MAX_FOLLOWUPS
from weights import initial_weights


class ConversationState:

    def __init__(self):
        self.reset()

    def reset(self):
        self.phase             = "idle"
        self.challenge         = ""
        self.dimensions        = []
        self.followups         = []
        self.followup_count    = 0
        self.weights           = initial_weights()   # {color: float}
        self.selected_face     = None
        self.pending_selection = None
        self.pending_rotation  = None   # (face_index, clockwise)

    # ── Input ─────────────────────────────────────────────────────

    def add_input(self, text: str):
        if not self.challenge:
            self.challenge = text
        else:
            if self.followups and "a" not in self.followups[-1]:
                self.followups[-1]["a"] = text
            self.followup_count += 1

    def add_followup_question(self, question: str):
        self.followups.append({"q": question})

    # ── Dimensions ────────────────────────────────────────────────

    def set_perspectives(self, dims: list):
        self.dimensions = dims

    def get_perspective(self, face_index: int) -> dict:
        if 0 <= face_index < len(self.dimensions):
            return self.dimensions[face_index]
        return None

    # ── History for Claude ────────────────────────────────────────

    def get_history(self) -> list:
        messages = []
        for exchange in self.followups:
            if "q" in exchange and "a" in exchange:
                messages.append({"role": "assistant", "content": exchange["q"]})
                messages.append({"role": "user",      "content": exchange["a"]})
        return messages

    # ── Status ────────────────────────────────────────────────────

    @property
    def at_followup_limit(self) -> bool:
        return self.followup_count >= MAX_FOLLOWUPS

    def summary(self) -> str:
        return (
            f"Phase: {self.phase} | "
            f"Challenge: '{self.challenge[:40]}' | "
            f"Follow-ups: {self.followup_count}/{MAX_FOLLOWUPS} | "
            f"Selected: {self.selected_face}"
        )
