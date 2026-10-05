# Recipe Finder

Tell Claude what's in your kitchen and what you're in the mood for. It searches about
268,000 rated Food.com recipes, picks the best-loved ones that fit, and passes along what
reviewers changed to make them even better.

```
you> I have chicken thighs, a lemon, feta and some spinach. Something cozy, under 45 minutes.

  [searching ingredients=['chicken thighs', 'lemon', 'feta', 'spinach'], max_minutes=45]
  [opening recipe 49414]
  ...
```

## Quick start

```bash
cd recipe-finder
pip install -r requirements.txt
python -m recipe_finder build          # one-time: downloads ~350 MB from Kaggle, ~1 min to process
export ANTHROPIC_API_KEY=sk-ant-...    # https://console.anthropic.com
python -m recipe_finder chat
```

`build` needs no Kaggle account. It writes everything to `recipe-finder/data/` (about
550 MB on disk; the folder is git-ignored).

## Commands

| Command | What it does |
|---|---|
| `chat` | Conversation with Claude: ask for ideas, then follow up ("the second one, full recipe please", "no dairy") |
| `ask "..."` | One question, one answer |
| `search --have "a,b" [...]` | Search directly, no AI and no API key needed. Run `search -h` for filters |
| `show RECIPE_ID` | Print one recipe: ingredients, steps, and highlighted reviews |

`chat` and `ask` take `--effort low|medium|high|xhigh|max` (default `medium`; higher means
more thorough searching but slower and pricier) and `--model`.

Good prompts to try:

- "What can I make with ground beef, black beans and tortillas? Mexican, family-friendly."
- "Best-rated chocolate chip cookies that reviewers say stay chewy."
- "Vegetarian dinner with chickpeas and coconut milk, under 30 minutes, nothing too spicy."
- "I'm allergic to tree nuts. Fall dessert for 8 people."

## How it works

**Data.** [Food.com – Recipes and Reviews](https://www.kaggle.com/datasets/irkaal/foodcom-recipes-and-reviews)
on Kaggle (listed as CC0; the recipes and reviews were written by Food.com users, through
2020). The build step keeps recipes that have at least one star rating and drops
non-food entries.

**Ratings.** The recipe file's rating is rounded to the nearest half star, and 65% of
recipes show 5.0, so it can't separate great from fine. The build recomputes each
recipe's exact average from 1.3M individual star ratings. Ranking then uses a *weighted
rating* (a Bayesian average). Each recipe is scored as if it also had 10 extra ratings
at the site-wide average (4.58). So a 4.9 from 150 cooks beats a 5.0 from 2.

**Ingredient matching** (`recipe_finder/ingredients.py`). "chicken thighs" matches
"boneless skinless chicken thighs", and "lemon" matches "fresh lemon juice". But
"chicken" does not match "chicken broth", "egg" does not match "egg noodles", and
"garlic" does not match "garlic salt". Salt, pepper, cooking oils, butter, sugar, flour
and water are assumed to be on hand.

**Ranking** (`recipe_finder/search.py`, `sort="best"`). Using more of your ingredients
counts most. Then comes weighted rating, and then a small penalty for each item you'd
need to buy. Other sorts: `rating`, `fewest_missing`, `quickest`.

**Claude layer** (`recipe_finder/assistant.py`). Claude (`claude-opus-5-5`) gets two
tools, `search_recipes` and `get_recipe`. It turns your request into searches and
loosens them if results are thin. It opens the best candidates to read their reviews,
then recommends three with ratings, times, a shopping list and reviewer tweaks.
Recommendations come only from the database: the system prompt forbids inventing
recipes, amounts or reviews. Requests opt into server-side refusal fallbacks
(`fallbacks: "default"`). This is very unlikely to matter for recipes, but means a
rare false-positive safety decline is retried on another model instead of failing.

## Known limitations

- **No reliable amounts.** The scraped data lost ingredient units: "1/4 feta" could mean
  cups or ounces. Amounts line up with ingredient names for only ~25% of recipes. Claude
  gives an amount only when a step states it ("stir in 1/2 teaspoon salt"); otherwise use
  the Food.com link.
- **Ingredient lists can be incomplete.** The scrape dropped some ingredient names. For
  allergies, Claude excludes specific items and checks the steps, but always confirm
  against the full recipe at the link.
- **Snapshot from 2020.** No newer recipes, and some links may have moved.
- Matching is word-based, so oddly named ingredients can slip through or be missed.

## Tests

```bash
python -m pytest -q
```

The tests build a tiny synthetic dataset, so they don't need the download or an API key.
`tests/test_assistant.py` drives the full Claude tool loop against a fake Messages API
that streams scripted replies. It checks that searches run, results reach Claude, and
multi-turn history is only ever appended to.

## Ideas for next steps

- **Your NYT Cooking favorites:** save them into a recipe manager (Paprika, Mela),
  export, and load them as a second source alongside Food.com.
- A small web UI so it works from your phone.
- Semantic search with embeddings ("something like a Tuscan white bean soup").
- Weekly meal plans with a combined shopping list.
