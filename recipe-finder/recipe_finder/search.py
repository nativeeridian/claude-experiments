"""In-memory recipe index: ingredient matching, filters, and rating-aware ranking."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from . import ingredients as ing
from .data import CORE_COLUMNS, DEFAULT_DATA_DIR, PROCESSED_FILE, REVIEWS_FILE

# Bayesian prior: every recipe is treated as if it also had this many reviews at
# the dataset-wide average rating. A 5.0 from 2 reviews no longer beats a 4.8
# from 300, but a 4.9 from 150 still beats a 4.7 from 2,000.
PRIOR_REVIEWS = 10

# Ranking for sort="best". Using one more of your ingredients (out of 4) is worth 0.5,
# about the gap between a 4.9 and a 4.4 recipe. Each item to buy costs 0.02, so a much
# better-loved recipe still wins over one that needs a few fewer groceries.
COVERAGE_WEIGHT = 2.0
MISSING_PENALTY = 0.02

SORTS = ("best", "rating", "fewest_missing", "quickest")
MAX_LIMIT = 25

_WORD = re.compile(r"[a-z0-9]+")


def weighted_rating(rating: np.ndarray, reviews: np.ndarray, mean: float, m: float = PRIOR_REVIEWS):
    return (reviews * rating + m * mean) / (reviews + m)


def recipe_url(recipe_id: int, name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return f"https://www.food.com/recipe/{slug}-{recipe_id}"


def _text_tokens(text: str) -> list[str]:
    return [ing.singularize(w) for w in _WORD.findall(text.lower())]


def _num(value, digits: int = 0):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    return round(float(value), digits) if digits else int(round(float(value)))


@dataclass
class SearchResult:
    total_matches: int
    recipes: list[dict]
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        out = {"total_matches": self.total_matches, "recipes": self.recipes}
        if self.notes:
            out["notes"] = self.notes
        return out


class RecipeIndex:
    def __init__(self, path: Path | str | None = None):
        self.path = Path(path) if path else DEFAULT_DATA_DIR / PROCESSED_FILE
        if not self.path.exists():
            raise FileNotFoundError(
                f"{self.path} not found. Run `python -m recipe_finder build` first."
            )
        self.reviews_path = self.path.with_name(REVIEWS_FILE)
        core = pq.read_table(self.path, columns=CORE_COLUMNS)
        self.n = core.num_rows

        def floats(col: str) -> np.ndarray:
            return core[col].to_numpy().astype(float)

        self.ids = core["id"].to_numpy()
        self.names = np.array(core["name"].to_pylist(), dtype=object)
        self.category = np.array(core["category"].to_pylist(), dtype=object)
        self.rating = floats("rating")
        self.reviews = floats("reviews")
        self.minutes = floats("total_minutes")
        self.calories = floats("calories")
        self.servings = floats("servings")
        self.mean_rating = float(self.rating.mean())
        self.wr = weighted_rating(self.rating, self.reviews, self.mean_rating)
        self._row_of_id = {int(rid): i for i, rid in enumerate(self.ids)}
        self._build_ingredient_index(core["ingredients"])
        self._build_text_index(core)

    # -- index construction -------------------------------------------------

    def _build_ingredient_index(self, lists: pa.ChunkedArray) -> None:
        lists = lists.combine_chunks()
        # Recipes are stored in row order, so each recipe's ingredients are a slice.
        self.flat_rows = pc.list_parent_indices(lists).to_numpy()
        self._row_bounds = np.searchsorted(self.flat_rows, np.arange(self.n + 1))
        raw = pc.list_flatten(lists).dictionary_encode()
        # Collapse spelling variants ("Garlic Cloves", "garlic cloves") into one vocab entry.
        cleaned = [ing.clean_name(u) for u in raw.dictionary.to_pylist()]
        vocab_codes, vocab = pd.factorize(pd.Series(cleaned, dtype=object), sort=False)
        self.vocab = list(vocab)
        self.flat_vocab = vocab_codes[raw.indices.to_numpy()]
        counts = np.bincount(self.flat_vocab, minlength=len(self.vocab))
        order = np.argsort(self.flat_vocab, kind="stable")
        self.postings = np.split(self.flat_rows[order], np.cumsum(counts)[:-1])
        self.pantry_mask = self._vocab_mask_pantry(ing.DEFAULT_PANTRY)

    def _build_text_index(self, core: pa.Table) -> None:
        """Token -> recipe rows, over name, category and Food.com keyword tags."""
        tags = pc.binary_join(core["keywords"], " ")
        text = pc.binary_join_element_wise(
            *(pc.fill_null(col.cast(pa.large_string()), "") for col in (core["name"], core["category"], tags)),
            pa.scalar(" ", pa.large_string()),
        )
        words = pc.split_pattern_regex(pc.utf8_lower(text), r"[^a-z0-9]+").combine_chunks()
        rows = pc.list_parent_indices(words).to_numpy()
        encoded = pc.list_flatten(words).dictionary_encode()
        tok_codes, toks = pd.factorize(
            pd.Series([ing.singularize(w) for w in encoded.dictionary.to_pylist()], dtype=object)
        )
        # One sorted key per distinct (token, row) pair, then split per token.
        keys = np.sort(tok_codes[encoded.indices.to_numpy()].astype(np.int64) * self.n + rows)
        keys = keys[np.r_[True, keys[1:] != keys[:-1]]]
        tok_of, rows = np.divmod(keys, self.n)
        starts = np.flatnonzero(np.r_[True, tok_of[1:] != tok_of[:-1]])
        self.text_postings = dict(zip(toks[tok_of[starts]], np.split(rows, starts[1:])))
        self.text_postings.pop("", None)

    # -- matching helpers -----------------------------------------------------

    def _vocab_mask_pantry(self, items) -> np.ndarray:
        keys = ing.pantry_keys(items)
        return np.fromiter((ing.is_pantry(v, keys) for v in self.vocab), bool, len(self.vocab))

    def vocab_matches(self, term: str, broad: bool = False) -> np.ndarray:
        """Vocab ids of every recipe ingredient that `term` covers."""
        return np.fromiter(
            (i for i, v in enumerate(self.vocab) if ing.matches(term, v, broad)), dtype=np.int64
        )

    def _rows_with(self, vocab_ids: np.ndarray) -> np.ndarray:
        mask = np.zeros(self.n, dtype=bool)
        for v in vocab_ids:
            mask[self.postings[v]] = True
        return mask

    # -- public API ----------------------------------------------------------

    def search(
        self,
        ingredients: list[str] | None = None,
        require: list[str] | None = None,
        exclude: list[str] | None = None,
        pantry: list[str] | None = None,
        use_default_pantry: bool = True,
        query: str | None = None,
        max_minutes: float | None = None,
        max_calories: float | None = None,
        max_missing: int | None = None,
        min_reviews: int = 5,
        min_rating: float | None = None,
        sort: str = "best",
        limit: int = 10,
    ) -> SearchResult:
        """Find rated recipes.

        ingredients: what you have / want to use; a recipe must use at least one.
        require: every one of these must be in the recipe.
        exclude: none of these may be in the recipe.
        pantry: extra things you have on hand (not counted as "missing").
        query: words that must appear in the recipe's name, category or tags.
        """
        ingredients = [t.strip() for t in ingredients or [] if t.strip()]
        require = [t.strip() for t in require or [] if t.strip()]
        exclude = [t.strip() for t in exclude or [] if t.strip()]
        pantry = [t.strip() for t in pantry or [] if t.strip()]
        if sort not in SORTS:
            raise ValueError(f"sort must be one of {SORTS}")
        limit = max(1, min(int(limit), MAX_LIMIT))
        notes: list[str] = []

        mask = self.reviews >= (min_reviews or 0)
        if min_rating is not None:
            mask &= self.rating >= min_rating
        if max_minutes is not None:
            mask &= self.minutes <= max_minutes
        if max_calories is not None:
            mask &= self.calories <= max_calories

        if query:
            for tok in dict.fromkeys(_text_tokens(query)):
                rows = self.text_postings.get(tok)
                if rows is None:
                    notes.append(f"No recipe names or tags contain '{tok}'.")
                    mask[:] = False
                    break
                hit = np.zeros(self.n, dtype=bool)
                hit[rows] = True
                mask &= hit

        covered = self.pantry_mask.copy() if use_default_pantry else np.zeros(len(self.vocab), bool)
        for term in pantry:
            covered[self.vocab_matches(term)] = True

        for term in require:
            ids = self.vocab_matches(term)
            if len(ids) == 0:
                notes.append(f"No Food.com ingredient matches '{term}'.")
            covered[ids] = True
            mask &= self._rows_with(ids)

        for term in exclude:
            ids = self.vocab_matches(term, broad=True)
            if len(ids) == 0:
                notes.append(f"No Food.com ingredient matches excluded '{term}'; name specific items.")
            mask &= ~self._rows_with(ids)

        uses = np.zeros(self.n, dtype=np.int32)
        use_hits: list[np.ndarray] = []
        for term in ingredients:
            ids = self.vocab_matches(term)
            if len(ids) == 0:
                notes.append(f"No Food.com ingredient matches '{term}'; try a more common name.")
            covered[ids] = True
            hit = self._rows_with(ids)
            use_hits.append(hit)
            uses += hit
        if ingredients:
            mask &= uses > 0

        missing_flat = ~covered[self.flat_vocab]
        missing = np.bincount(self.flat_rows, weights=missing_flat, minlength=self.n).astype(int)
        if max_missing is not None:
            mask &= missing <= max_missing

        rows = np.flatnonzero(mask)
        best = self.wr[rows] - MISSING_PENALTY * missing[rows]
        if ingredients:
            best = best + COVERAGE_WEIGHT * uses[rows] / len(ingredients)
        if sort == "best":
            order = np.lexsort((-self.reviews[rows], -best))
        elif sort == "rating":
            order = np.lexsort((-self.reviews[rows], -self.wr[rows]))
        elif sort == "fewest_missing":
            order = np.lexsort((-self.wr[rows], missing[rows]))
        else:  # quickest
            order = np.lexsort((-self.wr[rows], np.nan_to_num(self.minutes[rows], nan=1e9)))
        top = rows[order[:limit]]

        recipes = [self._summary(r, ingredients, use_hits, covered) for r in top]
        return SearchResult(total_matches=len(rows), recipes=recipes, notes=notes)

    def _recipe_vocab(self, row: int) -> np.ndarray:
        lo, hi = self._row_bounds[row], self._row_bounds[row + 1]
        return self.flat_vocab[lo:hi]

    def _summary(self, r: int, terms: list[str], use_hits: list[np.ndarray], covered) -> dict:
        vocab_ids = self._recipe_vocab(r)
        out = {
            "id": int(self.ids[r]),
            "name": self.names[r],
            "rating": round(float(self.rating[r]), 2),
            "reviews": int(self.reviews[r]),
            "weighted_rating": round(float(self.wr[r]), 3),
            "total_minutes": _num(self.minutes[r]),
            "category": self.category[r],
            "calories_per_serving": _num(self.calories[r]),
            "servings": _num(self.servings[r]),
            "n_ingredients": int(len(vocab_ids)),
        }
        if terms:
            out["uses"] = [t for t, hit in zip(terms, use_hits) if hit[r]]
        out["missing"] = list(dict.fromkeys(self.vocab[v] for v in vocab_ids if not covered[v]))
        out["url"] = recipe_url(out["id"], out["name"])
        return out

    def get(self, recipe_id: int) -> dict | None:
        """Full recipe details, read from disk on demand."""
        if int(recipe_id) not in self._row_of_id:
            return None
        table = pq.read_table(self.path, filters=[("id", "=", int(recipe_id))])
        if table.num_rows == 0:
            return None
        rec = table.to_pylist()[0]
        # Food.com amounts were scraped without units ("1/4" feta might be cups or
        # ounces) and only line up with the names for ~25% of recipes.
        rec["amounts_without_units"] = rec.pop("quantities")
        for key, value in list(rec.items()):
            if isinstance(value, float) and math.isnan(value):
                rec[key] = None
        rec["rating"] = round(rec["rating"], 2)
        rec["weighted_rating"] = round(float(self.wr[self._row_of_id[int(recipe_id)]]), 3)
        rec["url"] = recipe_url(rec["id"], rec["name"])
        rec["review_snippets"] = self.review_snippets(int(recipe_id))
        return rec

    def review_snippets(self, recipe_id: int) -> list[dict]:
        """A few reviews for the recipe: tweak-heavy positive ones plus one critical one."""
        if not self.reviews_path.exists():
            return []
        table = pq.read_table(self.reviews_path, filters=[("recipe_id", "=", recipe_id)])
        return [
            {"stars": r["stars"], "date": r["date"], "text": r["text"]}
            for r in table.drop(["recipe_id"]).to_pylist()
        ]
