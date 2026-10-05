# Recipe Finder

Find the best-loved Food.com recipes for what's in your kitchen. Search 61,000
well-reviewed recipes by ingredient for free, or ask Claude, which picks recipes that fit
your request and passes along what reviewers changed to make them even better.

## Two versions in one app

| | **Search** (free, public) | **Ask Claude** |
|---|---|---|
| What it does | Type ingredients and filters; get top-rated recipes with full steps and reviews | Describe what you want in plain words; Claude searches, reads reviews and recommends |
| Needs | Nothing | An Anthropic API key (roughly 10 to 30 cents per question, by my estimate) |
| Who can use it | Anyone who opens the site | You, plus anyone you give the password to |

Both are tabs on the same site. With no API key configured, the site is search-only, and
the Ask Claude tab offers a button for visitors to deploy their own copy with their own
key. The key is never in the code (this repository is public); it lives in the hosting
settings.

## Deploy your own copy

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2Fnativeeridian%2Fclaude-experiments%2Ftree%2Fmain%2Frecipe-finder&project-name=recipe-finder&repository-name=recipe-finder&env=ANTHROPIC_API_KEY,APP_PASSWORD&envDescription=Your%20Anthropic%20API%20key%20%28console.anthropic.com%29,%20and%20a%20password%20visitors%20must%20enter%20to%20chat%20so%20others%20can%27t%20spend%20your%20credits.&envLink=https%3A%2F%2Fgithub.com%2Fnativeeridian%2Fclaude-experiments%2Ftree%2Fmain%2Frecipe-finder%23deploy-your-own-copy)

The button copies this folder into a new repository in your GitHub account and sets it
up on Vercel (the free Hobby plan is enough). It asks for two values:

- `ANTHROPIC_API_KEY`: your key from [console.anthropic.com](https://console.anthropic.com).
  Setting a monthly spend limit there (Settings → Limits) is a good idea.
- `APP_PASSWORD`: a password you choose. Anyone using Ask Claude on your site must enter
  it, so strangers can't spend your credits. Search stays open to everyone.

Then open your new URL. The recipe data ships in `bundle/` (53 MB), so there is no
database or build step.

## Deploy this repository's public site

To publish this repository itself (the free, search-only version):

1. On [vercel.com/new](https://vercel.com/new), import `claude-experiments` and set
   **Root Directory** to `recipe-finder`. Vercel detects the FastAPI app on its own.
2. Deploy with no environment variables. Search works for everyone; Ask Claude shows the
   "deploy your own copy" button.
3. To turn on Ask Claude for yourself later, add `ANTHROPIC_API_KEY` and `APP_PASSWORD`
   under Project → Settings → Environment Variables, then redeploy.

Optional variables: `CLAUDE_MODEL` (default `claude-opus-5-5`; `claude-sonnet-5-5` is about
half the price) and `CLAUDE_EFFORT` (`low`, `medium` (default), `high`, `xhigh` or `max`;
higher is more thorough but slower and costs more).

## Run locally

```bash
cd recipe-finder
pip install -r requirements-dev.txt
export ANTHROPIC_API_KEY=sk-ant-...
python -m recipe_finder serve          # web app at http://localhost:8000 (chat open locally)
python -m recipe_finder chat           # or chat in the terminal
```

| Command | What it does |
|---|---|
| `serve` | Run the web app locally |
| `chat` | Conversation with Claude in the terminal |
| `ask "..."` | One question, one answer |
| `search --have "a,b" [...]` | Search directly. No AI and no API key needed; see `search -h` for filters |
| `show RECIPE_ID` | Print one recipe: ingredients, steps and highlighted reviews |
| `build` | Rebuild `bundle/` from the Kaggle data (see below) |

Good prompts to try:

- "What can I make with ground beef, black beans and tortillas? Mexican, family-friendly."
- "Best-rated chocolate chip cookies that reviewers say stay chewy."
- "Vegetarian dinner with chickpeas and coconut milk, under 30 minutes, nothing too spicy."
- "I'm allergic to tree nuts. Fall dessert for 8 people."

## How it works

**Data.** [Food.com – Recipes and Reviews](https://www.kaggle.com/datasets/irkaal/foodcom-recipes-and-reviews)
on Kaggle (listed as CC0; the recipes and reviews were written by Food.com users, through
2020). `python -m recipe_finder build` downloads it (~350 MB, no Kaggle account needed)
and writes `bundle/`. The bundle keeps recipes with at least 5 star ratings, plus a few
reviews for each. `--min-ratings 1` includes every rated recipe (~268K), but that bundle is
too big to commit.

**Bundle format** (`recipe_finder/bundle.py`). Search columns and indexes live in
`index.npz` and `strings.json.gz`, loaded with numpy in about 0.2 s. Full recipes are
compressed JSON in blocks of 64, split into files under 25 MB. The app needs only
`anthropic`, `fastapi` and `numpy`; pandas and pyarrow are needed only for `build`.

**Ratings.** The recipe file's rating is rounded to the nearest half star, and 65% of
recipes show 5.0, so it can't separate great from fine. The build recomputes each
recipe's exact average from 1.3M individual star ratings. Ranking then uses a *weighted
rating* (a Bayesian average). Each recipe is scored as if it also had 10 extra ratings
at the site-wide average (4.58). So a 4.9 from 150 cooks beats a 5.0 from 2.

**Ingredient matching** (`recipe_finder/ingredients.py`). "chicken thighs" matches
"boneless skinless chicken thighs", and "lemon" matches "fresh lemon juice". But
"chicken" does not match "chicken broth", and "garlic" does not match "garlic salt".
Exclusions match broadly, so excluding "peanut" also removes "peanut butter chips".
Salt, pepper, cooking oils, butter, sugar, flour and water are assumed to be on hand.

**Ranking** (`recipe_finder/search.py`, `sort="best"`). Using more of your ingredients
counts most. Then comes weighted rating, and then a small penalty for each item you'd
need to buy.

**Claude** (`recipe_finder/assistant.py`). Claude (`claude-opus-5-5`) gets two tools,
`search_recipes` and `get_recipe`. It turns your request into searches and loosens them
if results are thin. It opens the best candidates to read their reviews, then
recommends three with ratings, times, a shopping list and reviewer tweaks. It only
recommends recipes from the database, and never invents amounts or reviews. Requests opt
into server-side refusal fallbacks (`fallbacks: "default"`), so a rare false-positive
safety decline is retried on another model instead of failing.

**Web app** (`recipe_finder/web.py`, `recipe_finder/static/index.html`). One FastAPI
function serves the page, a free search API (`/api/search`, `/api/recipe/{id}`, cached
by Vercel's CDN), and a streaming chat endpoint. Chat is *open* when run locally,
*password*-protected when `APP_PASSWORD` is set, and *off* on Vercel otherwise, so a
deployment never spends credits without a password in front. The browser keeps the
conversation and sends it back each turn, so the server stores nothing. Search results
are shareable links (`/?have=salmon,asparagus&max_minutes=45`).

## Known limitations

- **No reliable amounts.** The scraped data lost ingredient units: "1/4 feta" could mean
  cups or ounces. Claude gives an amount only when a step states it ("stir in 1/2
  teaspoon salt"); otherwise use the Food.com link.
- **Ingredient lists can be incomplete.** The scrape dropped some ingredient names. For
  allergies, Claude excludes specific items and checks the steps, but always confirm
  against the full recipe at the link.
- **Snapshot from 2020.** No newer recipes, and some links or photos may have moved.

## Tests

```bash
python -m pytest -q
```

The tests build a tiny synthetic bundle, so they need neither the download nor an API key.
`tests/fake_api.py` is a fake Messages API that streams scripted replies, used to drive
the full tool loop, the web endpoints and the password gate. The tests also check that
the conversation history sent back from the browser matches exactly what the SDK sent.
