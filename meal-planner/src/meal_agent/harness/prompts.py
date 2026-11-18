"""System prompt loading.

The system prompt is procedural memory: how the agent should work. It is read once per session
and never changed mid-session, because editing it would invalidate the prompt cache and the
model's earlier thinking (Stage 3 covers why).
"""

from importlib.resources import files


def load_system_prompt() -> str:
    return files("meal_agent.harness").joinpath("system.md").read_text(encoding="utf-8").strip()
