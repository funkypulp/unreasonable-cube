# ai_brain.py — Claude API calls for CubeBot
#
# Two functions:
#   ai_generate_dimensions(challenge) → list of 6 dimension dicts
#   ai_respond(state, face)           → {"type": "followup"|"story", ...}
#
# Test this file directly:
#   python ai_brain.py

import json
import anthropic
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL, MAX_FOLLOWUPS, COLORS

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


# ── System prompts ────────────────────────────────────────────────

SYSTEM_DIMENSIONS = """\
You are CubeBot, a tangible oracle embedded in a physical Rubik's Cube.

When given a challenge, identify exactly 6 distinct dimensions or aspects of that challenge.
Each dimension will be shown on one face of the cube. They must be genuinely different from
each other — covering emotional, systemic, temporal, relational, resource-based, and wildcard angles.
The wildcard (white face) should surface something the user hasn't said out loud yet.

Rules:
- Labels: 1 word strongly preferred, 2 words max (displayed on a small screen)
- Descriptors: 8–10 words max, phrased as an open question or tension
- No overlap between dimensions
- Be specific to the challenge, not generic

Return ONLY valid JSON with no markdown formatting, no code fences, no extra text:
{"perspectives":[{"id":0,"color":"red","label":"...","descriptor":"..."},{"id":1,"color":"orange","label":"...","descriptor":"..."},{"id":2,"color":"yellow","label":"...","descriptor":"..."},{"id":3,"color":"green","label":"...","descriptor":"..."},{"id":4,"color":"blue","label":"...","descriptor":"..."},{"id":5,"color":"white","label":"...","descriptor":"..."}]}
"""

SYSTEM_RESPOND = """\
You are CubeBot, a speculative futures oracle embedded in a physical Rubik's Cube.

The user has been physically rotating the cube's faces using encoders — each rotation cycles
the weights of the 4 adjacent dimensions, like a real Rubik's cube. This creates a weight
vector reflecting how much the user emphasized each dimension through their physical interaction.
They then pressed one face to select it as the primary lens.

Your job: decide whether to ask one more clarifying question, or generate the speculative future.

The SELECTED dimension is the primary lens. The WEIGHT VECTOR shapes the depth and texture
of your response — higher-weight dimensions bleed into the narrative more strongly.

If asking a follow-up question (max {max} total):
- Return: {{"type":"followup","question":"..."}}
- One short, direct question. Under 20 words.
- Probe the selected dimension, but let high-weight dimensions color the framing.
- Don't repeat a dimension already explored.

If generating the speculative future:
- Return: {{"type":"story","story":"..."}}
- 55–75 words. Set ~7 years from now.
- Vivid, specific, sensory. A possibility not a prediction.
- The selected dimension drives the narrative. High-weight dimensions appear as texture and context.
- Do NOT summarize the challenge. Open in the middle of a scene.

Always return ONLY valid JSON with no markdown, no code fences, no extra text.
""".format(max=MAX_FOLLOWUPS)


# ── JSON parsing helper ───────────────────────────────────────────

def _parse_json(raw: str) -> dict:
    """Strip markdown fences if present, then parse JSON."""
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    return json.loads(text)


# ── Dimension generation ──────────────────────────────────────────

def ai_generate_perspectives(challenge: str) -> list:
    """
    Call Claude to generate 6 perspectives for the given challenge.
    Returns a list of 6 dicts: {id, color, label, descriptor}
    """
    print("[ai] Generating dimensions...")

    msg = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=600,
        system=SYSTEM_DIMENSIONS,
        messages=[{
            "role": "user",
            "content": (
                f"Challenge: \"{challenge}\"\n\n"
                "Generate 6 perspectives. Assign colors in order: "
                "red, orange, yellow, green, blue, white."
            )
        }]
    )

    try:
        data = _parse_json(msg.content[0].text)
        dims = data["perspectives"]
        print(f"[ai] Got {len(dims)} perspectives.")
        return dims
    except (json.JSONDecodeError, KeyError) as e:
        print(f"[ai] Parse error: {e}\nRaw:\n{msg.content[0].text}")
        raise


# ── Response generation ───────────────────────────────────────────

def ai_respond(state, selected_face: int) -> dict:
    """
    Given conversation state + weights + selected face,
    return a follow-up question or speculative story.
    """
    print(f"[ai] Responding (follow-ups: {state.followup_count}/{MAX_FOLLOWUPS})...")

    sel_color      = COLORS[selected_face]
    sel_dim        = state.get_perspective(selected_face)
    sel_label      = sel_dim["label"]      if sel_dim else sel_color
    sel_descriptor = sel_dim["descriptor"] if sel_dim else ""

    # Build a readable weight summary with dimension labels
    weight_summary = {}
    for i, color in enumerate(COLORS):
        dim = state.get_perspective(i)
        label = dim["label"] if dim else color
        weight_summary[label] = state.weights[color]

    user_msg = (
        f'Original challenge: "{state.challenge}"\n'
        f"Follow-up exchanges: {json.dumps(state.followups)}\n"
        f'Selected dimension: "{sel_label}" — {sel_descriptor}\n'
        f"Perspective weights (shaped by how the user rotated the cube — higher = more influential in questions + story): {json.dumps(weight_summary)}\n"
        f"Follow-ups used: {state.followup_count} of {MAX_FOLLOWUPS}"
    )

    system = SYSTEM_RESPOND
    if state.followup_count >= MAX_FOLLOWUPS:
        system += "\n\nCRITICAL: Maximum follow-ups reached. You MUST return a story now."

    msg = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=600,
        system=system,
        messages=state.get_history() + [{
            "role": "user",
            "content": user_msg
        }]
    )

    try:
        result = _parse_json(msg.content[0].text)
        print(f"[ai] Response type: {result.get('type', '?')}")
        return result
    except json.JSONDecodeError as e:
        print(f"[ai] Parse error: {e}\nRaw:\n{msg.content[0].text}")
        raise


# ── Standalone test ───────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    if not ANTHROPIC_API_KEY:
        print("[ERROR] ANTHROPIC_API_KEY not set.")
        print("  Fix: export ANTHROPIC_API_KEY=sk-ant-...")
        sys.exit(1)

    print("=" * 55)
    print("CubeBot ai_brain — standalone test")
    print("=" * 55)

    challenge = input("\nEnter a challenge: ").strip()
    if not challenge:
        challenge = "help me figure out my career"

    print(f'\nGenerating dimensions for: "{challenge}"\n')
    dims = ai_generate_dimensions(challenge)

    print("\n── 6 Dimensions ──")
    for d in dims:
        print(f"  [{d['color'].upper():6}] {d['label']:<22} — {d['descriptor']}")

    # Simulate some encoder rotations
    from state   import ConversationState
    from weights import rotate_weights

    state = ConversationState()
    state.challenge = challenge
    state.set_perspectives(dims)

    print("\n── Simulating encoder rotations ──")
    print("Turning RED face clockwise twice...")
    state.weights = rotate_weights(state.weights, "red", clockwise=True)
    state.weights = rotate_weights(state.weights, "red", clockwise=True)
    print("Turning BLUE face counter-clockwise once...")
    state.weights = rotate_weights(state.weights, "blue", clockwise=False)

    print("\nWeight vector after rotations:")
    for color in COLORS:
        bar = "█" * int(state.weights[color] * 20)
        print(f"  {color:7}: {bar:<20} {state.weights[color]:.3f}")

    print("\nSimulating press on face 0 (red)...")
    response = ai_respond(state, 0)

    if response["type"] == "followup":
        print(f"\n  Follow-up: {response['question']}")
    else:
        print(f"\n  Story:\n{response['story']}")
