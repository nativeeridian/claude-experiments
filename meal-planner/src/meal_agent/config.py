"""Runtime settings, read from environment variables (or a .env file)."""

import os
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    model: str = "claude-opus-5-5"
    # Opus 5.5 defaults to "medium"; set explicitly so a default change can't surprise us.
    effort: str = "medium"
    max_tokens: int = 16000
    # Model calls allowed per user message before the loop gives up (decision 0004).
    max_iterations: int = 10
    data_dir: Path = PROJECT_ROOT / "data"

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            model=os.environ.get("MEAL_AGENT_MODEL", cls.model),
            effort=os.environ.get("MEAL_AGENT_EFFORT", cls.effort),
            max_iterations=int(os.environ.get("MEAL_AGENT_MAX_ITERATIONS", cls.max_iterations)),
            data_dir=Path(os.environ.get("MEAL_AGENT_DATA_DIR", cls.data_dir)),
        )
