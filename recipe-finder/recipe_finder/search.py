"""In-memory recipe index: ingredient matching, filters, and rating-aware ranking."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from . import ingredients as ing
from .bundle import Bundle, text_tokens

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

def weighted_rating(rating: np.ndarray, reviews: np.ndarray, mean: float, m: float = PRIOR_REVIEWS):
    return (reviews * rating + m * mean) / (reviews + m)


def recipe_url(recipe_id: int, name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return f"https://www.food.com/recipe/{slug}-{recipe_id}"


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
        self.bundle = Bundle(path)
        a = self.bundle.arrays
        self.n = len(a["ids"])
        self.ids = a["ids"]
        self.names = self.bundle.names
        self.category = [self.bundle.categories[c] if c >= 0 else None for c in a["category"]]
        self.rating = a["rating"].astype(float)
        self.reviews = a["reviews"].astype(float)
        self.minutes = a["minutes"].astype(float)
        self.calories = a["calories"].astype(float)
        self.servings = a["servings"].astype(float)
        self.mean_rating = float(self.bundle.meta["mean_rating"])
        self.wr = weighted_rating(self.rating, self.reviews, self.mean_rating)
        self._row_of_id = {int(rid): i for i, rid in enumerate(self.ids)}

        # Ingredients: recipe row r uses vocab ids flat_vocab[row_bounds[r]:row_bounds[r+1]].
        self.vocab = self.bundle.vocab
        self.flat_vocab = a["flat_vocab"]
        self._row_bounds = a["row_bounds"]
        self.flat_rows = np.repeat(np.arange(self.n), np.diff(self._row_bounds))
        order = np.argsort(self.flat_vocab, kind="stable")
        counts = np.bincount(self.flat_vocab, minlength=len(self.vocab))
        self.postings = np.split(self.flat_rows[order], np.cumsum(counts)[:-1])
        self.pantry_mask = self._vocab_mask_pantry(ing.DEFAULT_PANTRY)

        # Keywords: token -> rows whose name, category or tags contain it.
        rows, bounds = a["tok_rows"], a["tok_bounds"]
        self.text_postings = {
            tok: rows[bounds[i] : bounds[i + 1]] for i, tok in enumerate(self.bundle.tokens)
        }

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
            for tok in dict.fromkeys(text_tokens(query)):
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

    def card(self, recipe_id: int) -> dict | None:
        """The few fields a recipe card in the web UI shows."""
        row = self._row_of_id.get(int(recipe_id))
        if row is None:
            return None
        return {
            "id": int(recipe_id),
            "name": self.names[row],
            "rating": round(float(self.rating[row]), 2),
            "reviews": int(self.reviews[row]),
            "total_minutes": _num(self.minutes[row]),
            "image": self.bundle.details(row).get("image"),
            "url": recipe_url(int(recipe_id), self.names[row]),
        }

    def get(self, recipe_id: int) -> dict | None:
        """Full recipe details and review snippets."""
        row = self._row_of_id.get(int(recipe_id))
        if row is None:
            return None
        rec = self.bundle.details(row)
        # Food.com amounts were scraped without units ("1/4" feta might be cups or
        # ounces) and only line up with the names for ~25% of recipes.
        rec["amounts_without_units"] = rec.pop("quantities")
        rec["rating"] = round(rec["rating"], 2)
        rec["weighted_rating"] = round(float(self.wr[row]), 3)
        rec["url"] = recipe_url(rec["id"], rec["name"])
        return rec
