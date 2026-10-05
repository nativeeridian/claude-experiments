"""A tiny synthetic dataset in the Kaggle schema, so tests run without the download."""

import numpy as np
import pandas as pd
import pytest

from recipe_finder import data
from recipe_finder.search import RecipeIndex


def _recipe(rid, name, parts, *, category="Chicken", rating=4.5, count=10, time="PT40M", keywords=()):
    return {
        "RecipeId": float(rid),
        "Name": name,
        "AuthorName": "cook",
        "CookTime": "PT30M",
        "PrepTime": "PT10M",
        "TotalTime": time,
        "DatePublished": pd.Timestamp("2010-01-01", tz="UTC"),
        "Description": f"Make and share this {name} recipe from Food.com.",
        "Images": np.array([], dtype=object),
        "RecipeCategory": category,
        "Keywords": np.array(list(keywords), dtype=object),
        "RecipeIngredientQuantities": np.array(["1"] * len(parts), dtype=object),
        "RecipeIngredientParts": np.array(parts, dtype=object),
        "AggregatedRating": rating,
        "ReviewCount": float(count),
        "Calories": 400.0,
        "FatContent": 10.0,
        "SaturatedFatContent": 3.0,
        "CholesterolContent": 50.0,
        "SodiumContent": 300.0,
        "CarbohydrateContent": 30.0,
        "FiberContent": 2.0,
        "SugarContent": 5.0,
        "ProteinContent": 25.0,
        "RecipeServings": 4.0,
        "RecipeYield": None,
        "RecipeInstructions": np.array(["Cook it.", "Eat it."], dtype=object),
    }


RAW = [
    _recipe(1, "Lemon Garlic Chicken Thighs", ["boneless skinless chicken thighs", "fresh lemon juice", "garlic cloves", "salt", "olive oil"], keywords=["Easy", "< 60 Mins"]),
    _recipe(2, "Greek Chicken With Feta", ["chicken thighs", "lemon", "feta cheese", "spinach", "dried oregano"], time="PT1H10M", keywords=["Greek"]),
    _recipe(3, "Chicken Noodle Soup", ["chicken broth", "egg noodles", "carrots", "celery"], category="Soups", keywords=["Soup"]),
    _recipe(4, "Lemonade", ["lemons", "sugar", "water"], category="Beverages"),
    _recipe(5, "Peanut Chicken", ["chicken breasts", "peanut butter", "soy sauce"], category="Chicken Breast"),
    _recipe(6, "Window Spray", ["lemon juice", "water", "vinegar"], category="Household Cleaner"),
    _recipe(7, "Unrated Stew", ["beef", "potatoes"], rating=np.nan, count=np.nan),
]

# Star ratings per recipe: recipe 2 is loved by many, recipe 1 is perfect but barely rated.
REVIEWS = [
    (rid, stars, text)
    for rid, stars_list in {1: [5, 5], 2: [5] * 40 + [4] * 10, 3: [4] * 12, 4: [5] * 30, 5: [3] * 20}.items()
    for stars, text in zip(
        stars_list,
        [
            "I added extra garlic and a pinch of red pepper flakes and it was fantastic, will make again.",
            "Great as written, my whole family asked for seconds and the leftovers were even better.",
        ]
        * 50,
    )
] + [(2, 0, "No stars from me, just saying hi to everyone who made this lovely dish.")]


@pytest.fixture(scope="session")
def index(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("data")
    reviews = pd.DataFrame(
        {
            "RecipeId": [r[0] for r in REVIEWS],
            "Rating": [r[1] for r in REVIEWS],
            "Review": [r[2] for r in REVIEWS],
            "DateSubmitted": pd.Timestamp("2015-06-01", tz="UTC"),
        }
    )
    clean = data.process(pd.DataFrame(RAW), data.rating_stats(reviews))
    data._write(clean, tmp / data.PROCESSED_FILE, row_group_size=2)
    data._write(data.top_reviews(reviews, clean["id"]), tmp / data.REVIEWS_FILE, row_group_size=2)
    return RecipeIndex(tmp / data.PROCESSED_FILE)
