# weights.py — Rubik's cube style weight rotation
#
# When an encoder rotates, the weights of the 4 adjacent faces
# cycle — just like how turning a face on a real Rubik's cube
# moves the 4 surrounding strips.
#
# The rotated face's own weight never changes.
# Only the ring of 4 neighbors cycles.
#
# Test this file directly:
#   python weights.py

from config import COLORS, WEIGHT_STEP, WEIGHT_MIN, WEIGHT_MAX

# ── Adjacency map ─────────────────────────────────────────────────
# For each face, the 4 adjacent faces listed in clockwise order.
# Clockwise rotation cycles: [0]→[1]→[2]→[3]→[0]
# Counter-clockwise reverses that cycle.

ADJACENT = {
    "red":    ["yellow", "blue",  "green", "white"],   # top
    "orange": ["yellow", "white", "green", "blue" ],   # bottom
    "yellow": ["red",    "blue",  "orange","white"],   # front
    "green":  ["red",    "white", "orange","blue" ],   # back
    "blue":   ["red",    "yellow","orange","green"],   # right
    "white":  ["red",    "green", "orange","yellow"],  # left
}


def initial_weights() -> dict:
    """All faces start at equal weight."""
    return {color: round(1.0 / len(COLORS), 3) for color in COLORS}


def rotate_weights(weights: dict, face_color: str, clockwise: bool) -> dict:
    """
    Simulate turning the face of a Rubik's cube.

    The rotated face's weight stays fixed.
    The 4 adjacent face weights cycle clockwise or counter-clockwise.

    Args:
        weights:    current weight dict {color: float}
        face_color: which face was turned
        clockwise:  True = clockwise, False = counter-clockwise

    Returns:
        new weight dict with cycled adjacent values, clamped and normalised
    """
    new_weights = weights.copy()
    ring = ADJACENT[face_color]   # 4 adjacent colors in CW order

    if clockwise:
        # Each face takes the value of the previous face in the ring
        # [0]←[3], [1]←[0], [2]←[1], [3]←[2]
        prev = weights[ring[-1]]
        for i in range(len(ring)):
            new_val = prev + WEIGHT_STEP
            prev = weights[ring[i]]
            new_weights[ring[i]] = round(min(WEIGHT_MAX, max(WEIGHT_MIN, new_val)), 3)
    else:
        # Counter-clockwise: opposite direction
        prev = weights[ring[0]]
        for i in range(len(ring) - 1, -1, -1):
            new_val = prev + WEIGHT_STEP
            prev = weights[ring[i]]
            new_weights[ring[i]] = round(min(WEIGHT_MAX, max(WEIGHT_MIN, new_val)), 3)

    return new_weights


def normalize_weights(weights: dict) -> dict:
    """Normalize so all weights sum to 1.0."""
    total = sum(weights.values())
    if total < 1e-6:
        return initial_weights()
    return {k: round(v / total, 3) for k, v in weights.items()}


def weights_as_list(weights: dict) -> list:
    """Return weights in COLORS order as a plain list."""
    return [weights[c] for c in COLORS]


# ── Standalone test ───────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 55)
    print("CubeBot weights — Rubik's cube rotation test")
    print("=" * 55)

    def display(w, highlight=None):
        for color in COLORS:
            val   = w[color]
            bar   = "█" * int(val * 20) + "░" * (20 - int(val * 20))
            mark  = " ◀" if color == highlight else ""
            color_codes = {
                "red":"\033[91m","orange":"\033[93m","yellow":"\033[33m",
                "green":"\033[92m","blue":"\033[94m","white":"\033[97m"
            }
            c = color_codes.get(color, "")
            print(f"  {c}{color:7}\033[0m [{bar}] {val:.2f}{mark}")
        print(f"  sum = {sum(w.values()):.3f}\n")

    w = initial_weights()
    print("\nInitial (equal weights):")
    display(w)

    print("After turning RED face clockwise:")
    w = rotate_weights(w, "red", clockwise=True)
    display(w, "red")

    print("After turning RED face clockwise again:")
    w = rotate_weights(w, "red", clockwise=True)
    display(w, "red")

    print("After turning BLUE face counter-clockwise:")
    w = rotate_weights(w, "blue", clockwise=False)
    display(w, "blue")

    print("Interactive test — type a color and direction:")
    print("  e.g.  red cw   or   blue ccw")
    while True:
        try:
            line = input("> ").strip().lower().split()
            if len(line) < 2:
                break
            color, direction = line[0], line[1]
            if color not in COLORS:
                print(f"  Unknown color. Choose from: {COLORS}")
                continue
            cw = direction in ("cw", "clockwise", "r", "right")
            w = rotate_weights(w, color, clockwise=cw)
            display(w, color)
        except (EOFError, KeyboardInterrupt):
            break
