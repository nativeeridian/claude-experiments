"""Starter tools: the date and the household profile.

The model has no clock and no knowledge of this household. These two tools are the smallest
possible demonstration that tools exist to give the model facts it cannot know.
"""

import json
from datetime import datetime

from meal_agent.config import PROJECT_ROOT, Settings
from meal_agent.harness.tools import NoArgs, ToolRegistry

EXAMPLE_PROFILE = PROJECT_ROOT / "profile.example.json"


def register_basic_tools(registry: ToolRegistry, settings: Settings) -> None:
    @registry.tool()
    async def get_today(args: NoArgs) -> dict:
        """Returns today's local date, day of the week, and ISO week number."""
        now = datetime.now().astimezone()
        return {
            "date": now.date().isoformat(),
            "weekday": now.strftime("%A"),
            "iso_week": now.isocalendar().week,
            "time": now.strftime("%H:%M"),
        }

    @registry.tool()
    async def read_profile(args: NoArgs) -> dict:
        """Returns the household profile: each person's diet and goals, and the hands-on cooking
        minutes available on each day of the week."""
        path = settings.data_dir / "profile.json"
        source = "data/profile.json"
        if not path.exists():
            path, source = EXAMPLE_PROFILE, "profile.example.json (no personal profile yet)"
        profile = json.loads(path.read_text(encoding="utf-8"))
        return {"source": source, **profile}
