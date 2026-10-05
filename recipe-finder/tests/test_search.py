import pytest

from recipe_finder import ingredients as ing
from recipe_finder.data import parse_minutes


@pytest.mark.parametrize(
    "query, ingredient",
    [
        ("chicken thighs", "boneless skinless chicken thighs"),
        ("lemon", "fresh lemon juice"),
        ("lemon", "lemon, zest of"),
        ("garlic", "garlic cloves"),
        ("cumin", "ground cumin"),
        ("cloves", "ground cloves"),
        ("tomatoes", "tomato"),
        ("fresh spinach", "spinach"),
        ("chicken broth", "low sodium chicken broth"),
        ("vanilla", "vanilla extract"),
    ],
)
def test_matches(query, ingredient):
    assert ing.matches(query, ingredient)


@pytest.mark.parametrize(
    "query, ingredient",
    [
        ("chicken", "chicken broth"),
        ("chicken", "cream of chicken soup"),
        ("egg", "egg noodles"),
        ("garlic", "garlic salt"),
        ("cloves", "garlic cloves"),
        ("apple", "apple juice"),
        ("flour", "cake flour"),
        ("chicken thighs", "chicken breasts"),
        ("tortillas", "tortilla chips"),
    ],
)
def test_does_not_match(query, ingredient):
    assert not ing.matches(query, ingredient)


def test_broad_matching_for_exclusions():
    assert not ing.matches("peanut", "peanut butter chips")
    assert ing.matches("peanut", "peanut butter chips", broad=True)


def test_singularize():
    assert [ing.singularize(w) for w in ["berries", "potatoes", "olives", "leaves", "peaches", "hummus", "swiss"]] == [
        "berry", "potato", "olive", "leaf", "peach", "hummus", "swiss",
    ]


def test_parse_minutes():
    assert parse_minutes("PT1H20M") == 80
    assert parse_minutes("P1DT2H") == 1560
    assert parse_minutes("PT0S") != parse_minutes("PT0S")  # zero means unknown -> NaN
    assert parse_minutes(None) != parse_minutes(None)


def test_process_keeps_rated_food_with_exact_ratings(index):
    assert sorted(index.ids.tolist()) == [1, 2, 3, 4, 5]  # no cleaner, no unrated stew
    row = index._row_of_id[2]
    assert index.rating[row] == pytest.approx(4.8)  # 40x5 + 10x4; the 0-star comment is ignored
    assert index.reviews[row] == 50


def test_ingredient_search_prefers_using_more_of_what_you_have(index):
    res = index.search(ingredients=["chicken thighs", "lemon", "feta"], min_reviews=0)
    ids = [r["id"] for r in res.recipes]
    assert ids[:2] == [2, 1]
    assert 3 not in ids  # chicken noodle soup only has chicken *broth*
    assert res.recipes[0]["uses"] == ["chicken thighs", "lemon", "feta"]
    assert ids.index(4) > ids.index(1)  # lemonade uses only one of them


def test_min_reviews_default_hides_barely_rated(index):
    ids = [r["id"] for r in index.search(ingredients=["chicken thighs"]).recipes]
    assert ids == [2]


def test_rating_sort_blends_stars_with_review_count(index):
    res = index.search(sort="rating", min_reviews=0)
    # Lemonade (5.0 from 30) beats Greek chicken (4.8 from 50) beats Lemon chicken (5.0 from 2).
    assert [r["id"] for r in res.recipes] == [4, 2, 1, 3, 5]


def test_missing_skips_pantry_and_your_extras(index):
    res = index.search(ingredients=["chicken thighs", "lemon"], min_reviews=0)
    lemon_chicken = next(r for r in res.recipes if r["id"] == 1)
    assert lemon_chicken["missing"] == ["garlic cloves"]  # salt and olive oil are pantry
    res = index.search(ingredients=["chicken thighs", "lemon"], pantry=["garlic"], min_reviews=0)
    assert next(r for r in res.recipes if r["id"] == 1)["missing"] == []


def test_filters(index):
    assert [r["id"] for r in index.search(require=["feta"], min_reviews=0).recipes] == [2]
    assert 5 not in [r["id"] for r in index.search(ingredients=["chicken"], exclude=["peanut"], min_reviews=0).recipes]
    assert 2 not in [r["id"] for r in index.search(ingredients=["chicken thighs"], max_minutes=60, min_reviews=0).recipes]
    assert [r["id"] for r in index.search(max_missing=0, ingredients=["lemon"], min_reviews=0).recipes] == [4]


def test_query_matches_names_categories_and_tags(index):
    assert [r["id"] for r in index.search(query="soup", min_reviews=0).recipes] == [3]
    assert [r["id"] for r in index.search(query="greek", min_reviews=0).recipes] == [2]
    res = index.search(query="tacos", min_reviews=0)
    assert res.total_matches == 0 and res.notes


def test_unknown_ingredient_is_reported(index):
    res = index.search(ingredients=["unobtainium"])
    assert res.total_matches == 0
    assert "unobtainium" in res.notes[0]


def test_get_returns_details_and_reviews(index):
    recipe = index.get(2)
    assert recipe["url"] == "https://www.food.com/recipe/greek-chicken-with-feta-2"
    assert recipe["ingredients"][0] == "chicken thighs"
    assert recipe["amounts_without_units"] == ["1"] * 5
    assert recipe["description"] is None  # Food.com boilerplate is dropped
    snippets = recipe["review_snippets"]
    assert snippets and all(s["stars"] > 0 for s in snippets)
    assert snippets[0]["text"].startswith("I added extra garlic")  # tweak reviews first
    assert index.get(999) is None


def test_bundle_reads_across_blocks_and_shards(tmp_path, monkeypatch):
    import pandas as pd

    from conftest import RAW, REVIEWS
    from recipe_finder import bundle, data
    from recipe_finder.search import RecipeIndex

    monkeypatch.setattr(bundle, "BLOCK_SIZE", 2)
    monkeypatch.setattr(bundle, "SHARD_BYTES", 1)  # every block in its own file
    reviews = pd.DataFrame(
        {"RecipeId": [r[0] for r in REVIEWS], "Rating": [r[1] for r in REVIEWS],
         "Review": [r[2] for r in REVIEWS], "DateSubmitted": pd.Timestamp("2015-06-01", tz="UTC")}
    )
    data.build_bundle(pd.DataFrame(RAW), reviews, tmp_path, min_ratings=1)
    assert len(list(tmp_path.glob("details-*.bin"))) == 3
    idx = RecipeIndex(tmp_path)
    assert [idx.get(i)["name"] for i in (1, 2, 3, 4, 5)] == [
        "Lemon Garlic Chicken Thighs", "Greek Chicken With Feta", "Chicken Noodle Soup", "Lemonade", "Peanut Chicken",
    ]
