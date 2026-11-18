import json

import pytest
from pydantic import BaseModel, ConfigDict

from meal_agent.config import Settings
from meal_agent.harness.tools import ToolRegistry
from meal_agent.tools.basics import register_basic_tools


class EchoArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str


@pytest.fixture
def registry() -> ToolRegistry:
    registry = ToolRegistry()

    @registry.tool(args=EchoArgs)
    async def echo(args: EchoArgs) -> str:
        """Repeats the text back."""
        return args.text

    @registry.tool()
    async def boom(args) -> str:
        """Always fails."""
        raise RuntimeError("kaboom")

    return registry


def test_definitions_come_from_the_args_model(registry):
    echo, boom = registry.definitions()
    assert echo["name"] == "echo"
    assert echo["description"] == "Repeats the text back."
    assert echo["input_schema"]["properties"]["text"]["type"] == "string"
    assert echo["input_schema"]["required"] == ["text"]
    assert echo["input_schema"]["additionalProperties"] is False
    assert boom["input_schema"]["properties"] == {}


async def test_dispatch_runs_the_tool(registry):
    outcome = await registry.dispatch("echo", {"text": "hi"})
    assert outcome.content == "hi"
    assert outcome.is_error is False


@pytest.mark.parametrize(
    ("name", "raw_input", "expected"),
    [
        ("nope", {}, "Unknown tool 'nope'"),
        ("echo", {}, "Invalid input for echo: text: Field required"),
        ("echo", {"text": "hi", "extra": 1}, "Invalid input for echo: extra"),
        ("boom", {}, "boom failed: RuntimeError: kaboom"),
    ],
)
async def test_failures_become_error_outcomes(registry, name, raw_input, expected):
    outcome = await registry.dispatch(name, raw_input)
    assert outcome.is_error is True
    assert expected in outcome.content


async def test_listeners_hear_every_call(registry):
    heard = []
    registry.add_listener(heard.append)
    await registry.dispatch("echo", {"text": "hi"})
    await registry.dispatch("boom", {})
    assert [(c.name, c.outcome.is_error) for c in heard] == [("echo", False), ("boom", True)]


async def test_get_today_and_read_profile(tmp_path):
    registry = ToolRegistry()
    register_basic_tools(registry, Settings(data_dir=tmp_path))

    today = json.loads((await registry.dispatch("get_today", {})).content)
    assert set(today) == {"date", "weekday", "iso_week", "time"}

    example = json.loads((await registry.dispatch("read_profile", {})).content)
    assert example["source"].startswith("profile.example.json")
    assert {p["diet"] for p in example["people"]} == {"omnivore", "lacto-ovo vegetarian"}

    (tmp_path / "profile.json").write_text(json.dumps({"people": [], "cooking_minutes": {}}))
    personal = json.loads((await registry.dispatch("read_profile", {})).content)
    assert personal["source"] == "data/profile.json"
