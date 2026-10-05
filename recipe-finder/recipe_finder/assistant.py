"""Claude layer: turns a natural-language request into recipe searches and recommendations."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterator
from typing import Literal, Optional

import anthropic
from anthropic import beta_tool

from .search import MAX_LIMIT, RecipeIndex

MODEL = "claude-opus-5-5"
_RECIPE_LINK = re.compile(r"food\.com/recipe/[\w-]*-(\d+)(?![\w-])")
DEFAULT_EFFORT = "medium"

SYSTEM_PROMPT = """\
You help someone choose and cook great meals from a database of tens of thousands of \
well-reviewed Food.com recipes. Every recipe has a star rating from home cooks, a review \
count, ingredients, steps, times, nutrition and a few reviews.

How to work:
- Ground every recommendation in the tools. Only recommend recipes that search_recipes \
returned, and never invent ingredients, amounts, steps, ratings or review content.
- Turn the request into searches: what they have or want to use goes in `ingredients`, \
must-haves in `require`, dislikes, allergies and diet exclusions in `exclude`, and dish \
type, cuisine or style words in `query` (matched against recipe names, categories and \
Food.com tags such as "soup", "italian", "grill", "breakfast", "vegan"). Keep query words \
few and specific. If results are empty or weak, loosen the search (fewer query words, \
lower min_reviews, drop max_missing) and try again. For open-ended requests, search from \
a couple of angles.
- "Highly rated" means weighted_rating: the star average blended with how many people \
rated it. A 4.8 from 300 cooks is a safer bet than a 5.0 from 2.
- Before recommending, open the strongest candidates with get_recipe to confirm they fit \
and to read the reviews. Pass along concrete tweaks reviewers recommend.
- Recommend 3 recipes unless asked otherwise. For each give: name, rating (average and \
count), total time, which of their ingredients it uses, what they'd need to buy (skip \
basic pantry items), why it's a good pick, and the link.
- The data has no reliable ingredient amounts: amounts_without_units (when present) lines \
up with the ingredient list but lost its units. Give an amount only when a step states it \
with a unit (for example "stir in 1/2 teaspoon salt"); otherwise list the ingredient and \
point to the Food.com link for exact amounts. Never guess amounts.
- Ingredient lists in this data are sometimes incomplete, and `exclude` matches ingredient \
names, not categories: for an allergy or diet, exclude the specific items (for a nut \
allergy: peanut, almond, walnut, pecan, cashew, hazelnut, pistachio...), check the steps \
from get_recipe too, and tell them to confirm against the full recipe at the link.
- You may suggest swaps (for example chicken thighs for breasts, with timing changes), \
clearly marked as your suggestion rather than part of the recipe.
- When asked for a full recipe, give the ingredients and numbered steps from get_recipe.
- Keep replies easy to scan on a phone: light markdown only (bold, bullets, numbered \
steps, plain URLs). No tables and no # headings.
"""


def make_tools(index: RecipeIndex) -> list:
    @beta_tool(eager_input_streaming=True)
    def search_recipes(
        ingredients: Optional[list[str]] = None,
        require: Optional[list[str]] = None,
        exclude: Optional[list[str]] = None,
        pantry: Optional[list[str]] = None,
        query: Optional[str] = None,
        max_minutes: Optional[int] = None,
        max_calories: Optional[int] = None,
        max_missing: Optional[int] = None,
        min_reviews: int = 5,
        min_rating: Optional[float] = None,
        sort: Literal["best", "rating", "fewest_missing", "quickest"] = "best",
        limit: int = 10,
    ) -> str:
        """Search rated Food.com recipes by ingredients, dish words, time and other filters.

        Ingredient names are matched loosely: "chicken thighs" matches "boneless skinless
        chicken thighs", and "lemon" matches "fresh lemon juice". Basic pantry items (salt,
        pepper, cooking oils, butter, sugar, flour, water) are assumed on hand.

        Each result has id, name, rating (exact star average), reviews (number of star
        ratings), weighted_rating (rating blended with review count; use this to judge
        quality), total_minutes, category, calories_per_serving, servings, uses (which of
        `ingredients` it contains), missing (ingredients not covered by `ingredients`,
        `require`, or the pantry), and url.

        Args:
            ingredients: Ingredients the person has or wants to cook with. Each recipe uses at least one; recipes using more of them rank higher.
            require: Ingredients every recipe must contain.
            exclude: Ingredients no recipe may contain, matched broadly ("peanut" also excludes "peanut butter chips"). Name specific items, not categories: "pork", "bacon", "ham" rather than "meat".
            pantry: Extra items the person has on hand, so they don't count as missing (e.g. "garlic", "eggs", "soy sauce").
            query: Words that must all appear in the recipe's name, category or Food.com tags, e.g. "soup", "curry", "mexican", "breakfast", "slow cooker", "vegan".
            max_minutes: Maximum total time in minutes, including prep.
            max_calories: Maximum calories per serving.
            max_missing: Maximum number of ingredients the person would need to buy.
            min_reviews: Minimum number of star ratings (default 5). Lower it only if results are thin.
            min_rating: Minimum average star rating, 1 to 5.
            sort: "best" balances ingredient use, rating and items to buy; "rating" is by weighted rating only; "fewest_missing" minimizes shopping; "quickest" is by total time.
            limit: Number of results, 1 to 25 (default 10).
        """
        result = index.search(
            ingredients=ingredients,
            require=require,
            exclude=exclude,
            pantry=pantry,
            query=query,
            max_minutes=max_minutes,
            max_calories=max_calories,
            max_missing=max_missing,
            min_reviews=min_reviews,
            min_rating=min_rating,
            sort=sort,
            limit=min(limit, MAX_LIMIT),
        )
        return json.dumps(result.to_dict(), ensure_ascii=False)

    @beta_tool(eager_input_streaming=True)
    def get_recipe(recipe_id: int) -> str:
        """Get one recipe's full details and a few of its reviews.

        Returns ingredients, steps, times, servings, nutrition per serving, description,
        link, and up to 4 reviews: the most detailed positive ones (favoring reviews that
        describe tweaks) plus the most detailed critical one. amounts_without_units, when
        not null, gives each ingredient's amount with its unit missing.

        Args:
            recipe_id: The recipe id from search_recipes results.
        """
        recipe = index.get(recipe_id)
        if recipe is None:
            return json.dumps({"error": f"No rated recipe with id {recipe_id}."})
        recipe.pop("image", None)
        return json.dumps(recipe, ensure_ascii=False)

    return [search_recipes, get_recipe]


def _describe_call(index: RecipeIndex, name: str, args: dict) -> str:
    """A short, human-readable line for a tool call, shown while Claude works."""
    if name == "get_recipe":
        card = index.card(args.get("recipe_id", -1))
        return f"Reading reviews of {card['name']}" if card else "Opening a recipe"
    parts = []
    if args.get("ingredients") or args.get("require"):
        parts.append("with " + ", ".join([*(args.get("require") or []), *(args.get("ingredients") or [])]))
    if args.get("query"):
        parts.append(f"matching \"{args['query']}\"")
    if args.get("exclude"):
        parts.append("without " + ", ".join(args["exclude"]))
    if args.get("max_minutes"):
        parts.append(f"under {args['max_minutes']} min")
    return "Searching recipes " + " · ".join(parts) if parts else "Searching recipes"


def to_jsonable(messages: list) -> list:
    """Conversation history as plain JSON, exactly as the API expects it back.

    Assistant turns hold SDK objects (thinking blocks with signatures, tool calls); they
    are dumped the way the SDK itself sends them in a request.
    """

    def dump(value):
        if hasattr(value, "model_dump"):
            exclude = getattr(value, "__api_exclude__", None)
            return value.model_dump(mode="json", by_alias=True, exclude_unset=True, exclude=exclude)
        if isinstance(value, dict):
            return {k: dump(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [dump(v) for v in value]
        return value

    return dump(messages)


def _mentioned_ids(index: RecipeIndex, text: str, seen: dict[int, str]) -> list[int]:
    """Recipes the reply recommends, in order of appearance: any Food.com recipe link to a
    recipe in the index, plus recipes seen this turn whose exact name appears."""
    found: dict[int, int] = {}
    for m in _RECIPE_LINK.finditer(text):
        rid = int(m.group(1))
        if index.card(rid) is not None:
            found.setdefault(rid, m.start())
    lowered = text.lower()
    for rid, name in seen.items():
        pos = lowered.find(name.lower())
        if pos >= 0 and pos < found.get(rid, len(text)):
            found[rid] = pos
    return sorted(found, key=found.get)


def run_turn(
    client: anthropic.Anthropic,
    index: RecipeIndex,
    messages: list,
    text: str,
    model: str = MODEL,
    effort: str = DEFAULT_EFFORT,
) -> Iterator[dict]:
    """Send one user message and stream back what happens, as event dicts:

    {"type": "status", "text": ...}    a search or recipe lookup is running
    {"type": "text", "text": ...}      a piece of Claude's reply
    {"type": "recipes", "recipes": [...]}  cards for the recipes the reply recommends
    {"type": "notice", "text": ...}    the reply was cut short or declined

    `messages` is the conversation so far; this turn is appended to it in place, never
    editing earlier entries, so it can be passed back unchanged next turn.
    """
    messages.append({"role": "user", "content": text})
    runner = client.beta.messages.tool_runner(
        model=model,
        max_tokens=16000,
        system=SYSTEM_PROMPT,
        tools=make_tools(index),
        messages=messages,
        output_config={"effort": effort},
        # If a safety classifier declines, the API retries on a fallback model.
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        cache_control={"type": "ephemeral"},
        max_iterations=12,
        stream=True,
    )
    reply: list[str] = []
    seen: dict[int, str] = {}  # recipes Claude saw this turn, for the cards
    for stream in runner:
        for event in stream:
            if event.type == "content_block_delta" and event.delta.type == "text_delta":
                reply.append(event.delta.text)
                yield {"type": "text", "text": event.delta.text}
        message = stream.get_final_message()
        # The runner keeps its own copy of the history; mirror it here.
        messages.append(message.to_param())
        for block in message.content:
            if block.type == "tool_use":
                yield {"type": "status", "text": _describe_call(index, block.name, block.input)}
        tool_results = runner.generate_tool_call_response()
        if tool_results is not None:
            messages.append(tool_results)
            for result in tool_results["content"]:
                content = result.get("content")
                payload = content[0].get("text", "") if isinstance(content, list) and content else content
                try:
                    data = json.loads(payload or "{}")
                except (TypeError, json.JSONDecodeError):
                    continue
                for r in data.get("recipes", []) + ([data] if "id" in data else []):
                    seen[int(r["id"])] = r["name"]
        if message.stop_reason == "refusal":
            yield {"type": "notice", "text": "Claude declined to answer this request."}
        elif message.stop_reason == "max_tokens":
            yield {"type": "notice", "text": "The reply was cut off at the length limit."}
    cards = [index.card(rid) for rid in _mentioned_ids(index, "".join(reply), seen)]
    if cards:
        yield {"type": "recipes", "recipes": cards}


class RecipeChat:
    """A terminal conversation with Claude over the recipe index."""

    def __init__(
        self,
        index: RecipeIndex,
        client: anthropic.Anthropic | None = None,
        model: str = MODEL,
        effort: str = DEFAULT_EFFORT,
        out=sys.stdout,
        status=sys.stderr,
    ):
        self.client = client or anthropic.Anthropic()
        self.index = index
        self.model = model
        self.effort = effort
        self.messages: list = []
        self.out = out
        self.status = status

    def send(self, text: str) -> str:
        """Send one user message, stream Claude's reply to `out`, and return the reply text."""
        reply = []
        for event in run_turn(self.client, self.index, self.messages, text, self.model, self.effort):
            if event["type"] == "text":
                self.out.write(event["text"])
                self.out.flush()
                reply.append(event["text"])
            elif event["type"] in ("status", "notice"):
                self.status.write(f"  [{event['text']}]\n")
                self.status.flush()
        self.out.write("\n")
        return "".join(reply)
