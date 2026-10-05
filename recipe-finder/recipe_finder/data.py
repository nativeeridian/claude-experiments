"""Download the Food.com dataset and build the recipe bundle the app searches.

Source: "Food.com - Recipes and Reviews" on Kaggle (irkaal/foodcom-recipes-and-reviews):
~522K recipes and ~1.4M reviews scraped from Food.com. Kaggle serves public datasets
without a login. Building needs pandas and pyarrow; the app itself only needs the bundle
(see bundle.py).
"""

from __future__ import annotations

import datetime
import html
import re
import shutil
import urllib.request
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

from . import bundle

KAGGLE_URL = "https://www.kaggle.com/api/v1/datasets/download/irkaal/foodcom-recipes-and-reviews/{}"
DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RAW_RECIPES = "recipes.parquet"
RAW_REVIEWS = "reviews.parquet"

# Recipes need this many star ratings to be included. 5 keeps ~61K proven recipes and
# a bundle small enough to commit and deploy; use 1 locally to include everything rated.
DEFAULT_MIN_RATINGS = 5

# Food.com files a few non-food things (cleaning sprays, home remedies) as recipes.
NON_FOOD_CATEGORIES = {"Household Cleaner", "Homeopathy/Remedies"}

SNIPPET_MAX_CHARS = 450

_DURATION = re.compile(r"^P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?$")
_BOILERPLATE = re.compile(r"^Make and share this .* recipe from Food\.com\.?$", re.I)
# Reviews that describe a change the reviewer made are the most useful to a cook.
_TWEAK = re.compile(
    r"\b(?:added|instead of|substitut\w*|next time|i used|reduced|cut back|doubled|halved|"
    r"omitted|left out|skipped|tweak\w*|swap\w*|changed|less \w+|more \w+|extra \w+)\b",
    re.I,
)


def download(data_dir: Path = DEFAULT_DATA_DIR, force: bool = False) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    for name, size in ((RAW_RECIPES, "~180 MB"), (RAW_REVIEWS, "~170 MB")):
        if (data_dir / name).exists() and not force:
            continue
        archive = data_dir / (name + ".zip")
        print(f"Downloading {name} from Kaggle ({size}) ...")
        with urllib.request.urlopen(KAGGLE_URL.format(name)) as resp, open(archive, "wb") as out:
            shutil.copyfileobj(resp, out)
        with zipfile.ZipFile(archive) as zf:
            zf.extract(name, data_dir)
        archive.unlink()


def parse_minutes(value) -> float:
    """ISO-8601 duration ("PT1H20M") -> minutes; NaN if missing, zero or unparseable."""
    if not isinstance(value, str):
        return np.nan
    m = _DURATION.match(value)
    if not m or not any(m.groups()):
        return np.nan
    days, hours, minutes, seconds = (int(g) if g else 0 for g in m.groups())
    total = days * 1440 + hours * 60 + minutes + seconds / 60
    return total if total > 0 else np.nan


def _as_list(value) -> list:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return []
    return [x for x in list(value) if x is not None]


def _clean_text(value) -> str | None:
    if not isinstance(value, str):
        return None
    text = " ".join(html.unescape(value).split())
    return text or None


def _clean_description(value) -> str | None:
    text = _clean_text(value)
    return None if text is None or _BOILERPLATE.match(text) else text


def _truncate(text: str, limit: int = SNIPPET_MAX_CHARS) -> str:
    return text if len(text) <= limit else text[: limit - 1].rsplit(" ", 1)[0] + "…"


def rating_stats(reviews: pd.DataFrame) -> pd.DataFrame:
    """Exact mean star rating and number of star ratings per recipe.

    The recipe file's AggregatedRating is rounded to the nearest half star (and 65% of
    rated recipes show 5.0), so it can't separate great from good. Reviews with a 0
    rating are comments without stars and are left out.
    """
    rated = reviews[reviews["Rating"] > 0]
    stats = rated.groupby("RecipeId")["Rating"].agg(rating="mean", reviews="count")
    stats.index = stats.index.astype("int64")
    return stats


def process(raw: pd.DataFrame, stats: pd.DataFrame | None = None) -> pd.DataFrame:
    """Turn the raw Kaggle recipes frame into one tidy row per rated recipe."""
    df = raw[~raw["RecipeCategory"].isin(NON_FOOD_CATEGORIES)].copy()
    df["RecipeId"] = df["RecipeId"].astype("int64")
    if stats is not None:
        df = df.join(stats, on="RecipeId")
    else:
        df["rating"], df["reviews"] = np.nan, np.nan
    # Prefer exact stats from the reviews; fall back to the recipe's rounded rating.
    df["rating"] = df["rating"].fillna(df["AggregatedRating"])
    df["reviews"] = df["reviews"].fillna(df["ReviewCount"]).fillna(1)
    df = df[df["rating"].notna()]

    ingredients = df["RecipeIngredientParts"].map(
        lambda parts: [p.strip() for p in _as_list(parts) if isinstance(p, str) and p.strip()]
    )
    quantities = df["RecipeIngredientQuantities"].map(_as_list)
    # The quantity and ingredient-name lists only line up one-to-one in ~25% of
    # recipes (the scrape dropped some names). Keep quantities only when they do.
    aligned = [list(q) if len(q) == len(i) else None for q, i in zip(quantities, ingredients)]

    out = pd.DataFrame(
        {
            "id": df["RecipeId"],
            "name": df["Name"].map(_clean_text),
            "category": df["RecipeCategory"].map(_clean_text),
            "keywords": df["Keywords"].map(lambda k: [html.unescape(x) for x in _as_list(k)]),
            "rating": df["rating"].astype("float64"),
            "reviews": df["reviews"].astype("int64"),
            "total_minutes": df["TotalTime"].map(parse_minutes),
            "prep_minutes": df["PrepTime"].map(parse_minutes),
            "cook_minutes": df["CookTime"].map(parse_minutes),
            "servings": df["RecipeServings"],
            "yield": df["RecipeYield"].map(_clean_text),
            "calories": df["Calories"],
            "fat_g": df["FatContent"],
            "saturated_fat_g": df["SaturatedFatContent"],
            "cholesterol_mg": df["CholesterolContent"],
            "sodium_mg": df["SodiumContent"],
            "carbs_g": df["CarbohydrateContent"],
            "fiber_g": df["FiberContent"],
            "sugar_g": df["SugarContent"],
            "protein_g": df["ProteinContent"],
            "ingredients": ingredients.to_list(),
            "quantities": aligned,
            "instructions": df["RecipeInstructions"].map(
                lambda steps: [t for t in map(_clean_text, _as_list(steps)) if t]
            ),
            "description": df["Description"].map(_clean_description),
            "image": df["Images"].map(lambda imgs: (_as_list(imgs) or [None])[0]),
            "author": df["AuthorName"].map(_clean_text),
            "published": df["DatePublished"].dt.strftime("%Y-%m-%d"),
        }
    )
    out = out[out["name"].notna() & out["ingredients"].map(len).gt(0)]
    return out.sort_values("id").reset_index(drop=True)


def top_reviews(reviews: pd.DataFrame, recipe_ids: pd.Series) -> pd.DataFrame:
    """Up to 3 positive reviews (preferring ones that describe tweaks) and the most
    detailed critical review for each recipe in `recipe_ids`."""
    r = reviews[(reviews["Rating"] > 0) & reviews["RecipeId"].isin(recipe_ids)].copy()
    r["text"] = r["Review"].map(_clean_text)
    r = r[r["text"].notna() & (r["text"].str.len() >= 60)]
    r["tweak"] = r["text"].str.contains(_TWEAK)
    r["length"] = r["text"].str.len().clip(upper=SNIPPET_MAX_CHARS)
    r = r.sort_values(["RecipeId", "tweak", "length"], ascending=[True, False, False])
    positive = r[r["Rating"] >= 4].groupby("RecipeId").head(3)
    critical = r[r["Rating"] <= 3].groupby("RecipeId").head(1)
    picked = pd.concat([positive, critical]).sort_values(["RecipeId", "Rating"], ascending=[True, False])
    return pd.DataFrame(
        {
            "recipe_id": picked["RecipeId"].astype("int64"),
            "stars": picked["Rating"].astype("int8"),
            "date": picked["DateSubmitted"].dt.strftime("%Y-%m-%d"),
            "text": picked["text"].map(_truncate),
        }
    ).reset_index(drop=True)


def build_bundle(
    raw_recipes: pd.DataFrame, reviews: pd.DataFrame, bundle_dir: Path, min_ratings: int
) -> int:
    """Process the raw Kaggle frames and write a bundle; returns the recipe count."""
    clean = process(raw_recipes, rating_stats(reviews))
    mean_rating = float(clean["rating"].mean())  # prior for the weighted rating
    clean = clean[clean["reviews"] >= min_ratings]
    snippets: dict[int, list[dict]] = {}
    for r in top_reviews(reviews, clean["id"]).itertuples(index=False):
        snippets.setdefault(r.recipe_id, []).append({"stars": int(r.stars), "date": r.date, "text": r.text})
    bundle.write(
        clean,
        snippets,
        bundle_dir,
        meta={
            "source": "Food.com - Recipes and Reviews (kaggle.com/datasets/irkaal/foodcom-recipes-and-reviews)",
            "min_ratings": min_ratings,
            "mean_rating": mean_rating,
            "built": datetime.date.today().isoformat(),
        },
    )
    return len(clean)


def build(
    data_dir: Path = DEFAULT_DATA_DIR,
    bundle_dir: Path = bundle.DEFAULT_BUNDLE_DIR,
    min_ratings: int = DEFAULT_MIN_RATINGS,
    force_download: bool = False,
) -> Path:
    download(data_dir, force=force_download)
    print("Processing recipes and reviews (about a minute) ...")
    count = build_bundle(
        pd.read_parquet(data_dir / RAW_RECIPES), pd.read_parquet(data_dir / RAW_REVIEWS), bundle_dir, min_ratings
    )
    size = sum(f.stat().st_size for f in bundle_dir.iterdir()) / 1e6
    print(f"Wrote {count:,} recipes with {min_ratings}+ ratings to {bundle_dir} ({size:.0f} MB)")
    return bundle_dir
