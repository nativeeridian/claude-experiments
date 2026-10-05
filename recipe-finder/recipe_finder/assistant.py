"""Claude layer: turns a natural-language request into recipe searches and recommendations."""

from __future__ import annotations

import json
import sys
from typing import Literal, Optional

import anthropic
from anthropic import beta_tool

from .search import MAX_LIMIT, RecipeIndex

MODEL = "claude-opus-5-5"
DEFAULT_EFFORT = "medium"

SYSTEM_PROMPT = """\
You help someone choose and cook great meals from a database of about 268,000 Food.com \
recipes. Every recipe has a star rating from home cooks, a review count, ingredients, \
steps, times and nutrition, and well-reviewed recipes include a few reviews.

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
- Replies are shown in a terminal: use plain text with light markdown (bold, bullets, \
numbered steps). No tables and no # headings.
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


def _describe_call(name: str, args: dict) -> str:
    if name == "get_recipe":
        return f"opening recipe {args.get('recipe_id')}"
    parts = [f"{k}={v}" for k, v in args.items() if v not in (None, [], "")]
    return "searching " + ", ".join(parts)


class RecipeChat:
    """A multi-turn conversation with Claude over the recipe index."""

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
        self.tools = make_tools(index)
        self.model = model
        self.effort = effort
        self.messages: list = []
        self.out = out
        self.status = status

    def send(self, text: str) -> str:
        """Send one user message, stream Claude's reply to `out`, and return the reply text."""
        self.messages.append({"role": "user", "content": text})
        runner = self.client.beta.messages.tool_runner(
            model=self.model,
            max_tokens=16000,
            system=SYSTEM_PROMPT,
            tools=self.tools,
            messages=self.messages,
            output_config={"effort": self.effort},
            # If a safety classifier declines, the API retries on a fallback model.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            cache_control={"type": "ephemeral"},
            max_iterations=12,
            stream=True,
        )
        reply: list[str] = []
        for stream in runner:
            for event in stream:
                if event.type == "content_block_delta" and event.delta.type == "text_delta":
                    self.out.write(event.delta.text)
                    self.out.flush()
                    reply.append(event.delta.text)
            message = stream.get_final_message()
            # Mirror the runner's history (it keeps its own copy) so later turns see
            # every tool call and result, appended in order and never edited.
            self.messages.append(message.to_param())
            for block in message.content:
                if block.type == "tool_use":
                    self.status.write(f"  [{_describe_call(block.name, block.input)}]\n")
                    self.status.flush()
            tool_results = runner.generate_tool_call_response()
            if tool_results is not None:
                self.messages.append(tool_results)
            if message.stop_reason == "refusal":
                self.out.write("\n(Claude declined to answer this request.)\n")
            elif message.stop_reason == "max_tokens":
                self.out.write("\n(Reply was cut off at the length limit.)\n")
        self.out.write("\n")
        return "".join(reply)
