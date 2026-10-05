"""Command line: build the data, search without AI, or chat with Claude."""

from __future__ import annotations

import argparse
import json
import sys

from .search import SORTS

EXAMPLES = """\
examples:
  python -m recipe_finder chat
  python -m recipe_finder serve
  python -m recipe_finder ask "I have chicken thighs, lemon, feta and spinach. Something cozy under 45 minutes."
  python -m recipe_finder search --have "chicken thighs,lemon,feta" --max-minutes 45
  python -m recipe_finder show 49414
"""


def _csv(value: str) -> list[str]:
    return [v.strip() for v in value.split(",") if v.strip()]


def _load_index():
    from .search import RecipeIndex

    print("Loading recipes ...", file=sys.stderr)
    try:
        return RecipeIndex()
    except FileNotFoundError as exc:
        sys.exit(str(exc))


def cmd_build(args) -> None:
    from .data import build

    build(min_ratings=args.min_ratings, force_download=args.force_download)


def cmd_serve(args) -> None:
    import uvicorn

    print(f"Recipe Finder running at http://localhost:{args.port}", file=sys.stderr)
    uvicorn.run("recipe_finder.web:app", host=args.host, port=args.port)


def cmd_search(args) -> None:
    index = _load_index()
    result = index.search(
        ingredients=args.have,
        require=args.require,
        exclude=args.exclude,
        pantry=args.pantry,
        query=args.query,
        max_minutes=args.max_minutes,
        max_calories=args.max_calories,
        max_missing=args.max_missing,
        min_reviews=args.min_reviews,
        sort=args.sort,
        limit=args.limit,
    )
    if args.json:
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
        return
    for note in result.notes:
        print(f"note: {note}")
    print(f"{result.total_matches:,} matching recipes\n")
    for i, r in enumerate(result.recipes, 1):
        minutes = f"{r['total_minutes']} min" if r["total_minutes"] else "time n/a"
        print(f"{i:>2}. {r['name']}  (id {r['id']})")
        print(f"    {r['rating']:.2f} stars from {r['reviews']} ratings | {minutes} | {r['category']}")
        if r.get("uses"):
            print(f"    uses: {', '.join(r['uses'])}")
        print(f"    need: {', '.join(r['missing']) or 'nothing else'}")
        print(f"    {r['url']}\n")


def cmd_show(args) -> None:
    index = _load_index()
    recipe = index.get(args.recipe_id)
    if recipe is None:
        sys.exit(f"No rated recipe with id {args.recipe_id}.")
    if args.json:
        print(json.dumps(recipe, indent=2, ensure_ascii=False))
        return
    minutes = f"{recipe['total_minutes']:.0f} min" if recipe["total_minutes"] else "time n/a"
    serves = f"serves {recipe['servings']:.0f}" if recipe["servings"] else recipe["yield"] or ""
    print(f"{recipe['name']}\n{recipe['url']}")
    print(f"{recipe['rating']:.2f} stars from {recipe['reviews']} ratings | {minutes} | {serves}\n")
    if recipe["description"]:
        print(recipe["description"] + "\n")
    amounts = recipe["amounts_without_units"]
    print("Ingredients (Food.com's data dropped the units; exact amounts are at the link):")
    for i, item in enumerate(recipe["ingredients"]):
        print(f"  - {item}" + (f"  [{amounts[i]}]" if amounts and amounts[i] else ""))
    print("\nSteps:")
    for i, step in enumerate(recipe["instructions"], 1):
        print(f"  {i}. {step}")
    if recipe["review_snippets"]:
        print("\nFrom the reviews:")
        for rv in recipe["review_snippets"]:
            print(f"  [{rv['stars']} stars] {rv['text']}")


def _chat(args):
    import anthropic

    from .assistant import RecipeChat

    index = _load_index()
    try:
        return RecipeChat(index, model=args.model, effort=args.effort)
    except anthropic.AnthropicError as exc:
        sys.exit(f"Couldn't start the Claude client: {exc}\nSet ANTHROPIC_API_KEY and try again.")


def _send(chat, text: str) -> None:
    import anthropic

    try:
        chat.send(text)
    except anthropic.AuthenticationError:
        sys.exit("\nClaude rejected the API key. Check ANTHROPIC_API_KEY.")
    except anthropic.RateLimitError:
        print("\nRate limited by the API; wait a moment and try again.", file=sys.stderr)
    except anthropic.APIStatusError as exc:
        print(f"\nAPI error {exc.status_code}: {exc.message}", file=sys.stderr)
    except anthropic.APIConnectionError:
        print("\nCouldn't reach the Claude API. Check your connection.", file=sys.stderr)
    except TypeError as exc:
        # The SDK raises a TypeError when no credentials are configured at all.
        if "authentication" not in str(exc):
            raise
        sys.exit("\nNo Claude API credentials found. Set ANTHROPIC_API_KEY and try again.")


def cmd_ask(args) -> None:
    _send(_chat(args), " ".join(args.prompt))


def cmd_chat(args) -> None:
    chat = _chat(args)
    print("Tell me what you have and what you're in the mood for. Ctrl-D or 'quit' to exit.\n")
    while True:
        try:
            text = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if text.lower() in {"quit", "exit"}:
            return
        if text:
            print()
            _send(chat, text)
            print()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="recipe_finder",
        description="Find highly rated Food.com recipes for the ingredients you have.",
        epilog=EXAMPLES,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("build", help="download Food.com data from Kaggle and build the recipe bundle")
    p.add_argument("--min-ratings", type=int, default=5, help="skip recipes with fewer star ratings")
    p.add_argument("--force-download", action="store_true")
    p.set_defaults(func=cmd_build)

    p = sub.add_parser("serve", help="run the web app locally")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000)
    p.set_defaults(func=cmd_serve)

    p = sub.add_parser("search", help="search recipes directly (no AI)")
    p.add_argument("--have", type=_csv, default=[], help="comma-separated ingredients you have")
    p.add_argument("--require", type=_csv, default=[], help="ingredients that must be used")
    p.add_argument("--exclude", type=_csv, default=[], help="ingredients to avoid")
    p.add_argument("--pantry", type=_csv, default=[], help="extra items on hand")
    p.add_argument("--query", help="words in the name/category/tags, e.g. 'soup' or 'thai'")
    p.add_argument("--max-minutes", type=int)
    p.add_argument("--max-calories", type=int)
    p.add_argument("--max-missing", type=int, help="max ingredients you'd need to buy")
    p.add_argument("--min-reviews", type=int, default=5)
    p.add_argument("--sort", choices=SORTS, default="best")
    p.add_argument("--limit", type=int, default=10)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_search)

    p = sub.add_parser("show", help="show one recipe in full")
    p.add_argument("recipe_id", type=int)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_show)

    for name, func, help_text in (
        ("ask", cmd_ask, "ask Claude one question"),
        ("chat", cmd_chat, "chat with Claude about what to cook"),
    ):
        p = sub.add_parser(name, help=help_text)
        if name == "ask":
            p.add_argument("prompt", nargs="+")
        p.add_argument("--model", default="claude-opus-5-5")
        p.add_argument("--effort", default="medium", choices=["low", "medium", "high", "xhigh", "max"])
        p.set_defaults(func=func)

    args = parser.parse_args(argv)
    args.func(args)
