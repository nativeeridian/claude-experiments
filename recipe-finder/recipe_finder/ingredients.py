"""Ingredient-name normalization and matching.

Food.com ingredient names are short phrases ("boneless skinless chicken thighs",
"fresh lemon juice"). We compare them as sets of normalized tokens: a user's
ingredient matches a recipe ingredient when every token the user typed appears in
the recipe ingredient. So "chicken thighs" matches "boneless skinless chicken thighs",
and "lemon" matches "fresh lemon juice".

That rule alone over-matches on processed products (having chicken does not mean
you have chicken broth), so a recipe ingredient that contains a "derived product"
token the user did not type is not a match.
"""

from __future__ import annotations

import re
from functools import lru_cache

_NON_WORD = re.compile(r"[^a-z0-9]+")

# Words that turn a raw ingredient into a different product. "lemon" should not
# match "lemon cake mix", but "lemon cake mix" should still match "lemon cake mix".
DERIVED_TOKENS = frozenset(
    {
        "broth", "stock", "bouillon", "soup", "gravy", "mix", "base", "seasoning",
        "cube", "granule", "pudding", "gelatin", "jell", "curd", "yogurt", "liqueur",
        "schnapps", "vodka", "rum", "soda", "drink", "candy", "cake", "cookie",
        "cracker", "chip", "noodle", "wrapper", "substitute", "beater", "juice", "nectar",
        "jam", "jelly", "preserve", "marmalade", "pie", "filling", "concentrate",
        "flavoring", "extract", "salt",
    }
)

# Derived tokens that are still fine for these base ingredients:
# a lemon gives you lemon juice; a vanilla bean is close enough to vanilla extract.
_DERIVED_OK = {
    "juice": {"lemon", "lime", "orange", "grapefruit"},
    "extract": {"vanilla", "almond"},
}

# Words that describe an ingredient's form rather than what it is. They are dropped
# from both sides so "fresh spinach" == "spinach" and "lemon, zest of" == "lemon".
STOP_TOKENS = frozenset(
    {
        "fresh", "freshly", "of", "and", "or", "a", "the", "to", "taste", "large",
        "small", "medium", "chopped", "diced", "minced", "sliced", "whole", "dried",
        "frozen", "canned", "raw", "cooked", "boneless", "skinless", "lean", "extra",
        "organic", "plain", "rind", "zest", "leaf", "sprig", "stalk", "head", "piece",
        "bunch", "cup", "can", "package",
    }
)

# A conservative default pantry: things almost every kitchen has, so they are not
# counted as "missing" when ranking. Matched by equal token sets (see is_pantry).
DEFAULT_PANTRY = (
    "water", "salt", "kosher salt", "sea salt", "table salt", "pepper", "black pepper",
    "fresh ground black pepper", "ground black pepper", "fresh ground pepper",
    "black peppercorns", "salt and pepper", "salt & pepper", "olive oil",
    "extra virgin olive oil", "vegetable oil", "canola oil", "oil", "cooking spray",
    "nonstick cooking spray",
    "sugar", "granulated sugar", "white sugar", "flour", "all-purpose flour",
    "butter", "unsalted butter", "ice", "ice cubes", "cold water", "warm water",
    "hot water", "boiling water",
)

_IRREGULAR = {
    "leaves": "leaf",
    "halves": "half",
    "loaves": "loaf",
    "knives": "knife",
}
_KEEP_S = ("ss", "us", "is", "ous")


@lru_cache(maxsize=None)
def singularize(word: str) -> str:
    if word in _IRREGULAR:
        return _IRREGULAR[word]
    if len(word) <= 3 or word.endswith(_KEEP_S):
        return word
    if word.endswith("ies"):
        return word[:-3] + "y"
    if word.endswith("oes"):
        return word[:-2]
    if word.endswith(("ches", "shes", "sses", "xes")):
        return word[:-2]
    if word.endswith("s"):
        return word[:-1]
    return word


def clean_name(name: str) -> str:
    """Lowercase and collapse punctuation; used as the canonical display/vocab key."""
    return " ".join(_NON_WORD.sub(" ", name.lower()).split())


@lru_cache(maxsize=65536)
def tokens(name: str) -> frozenset[str]:
    """Normalized content tokens of an ingredient phrase."""
    words = [singularize(w) for w in _NON_WORD.sub(" ", name.lower()).split()]
    content = frozenset(w for w in words if w not in STOP_TOKENS)
    if "garlic" in content:
        content -= {"clove"}  # "garlic cloves" is garlic; "ground cloves" is the spice
    # Don't let a phrase made only of descriptors vanish entirely.
    return content or frozenset(words)


def matches(query: str, ingredient: str, broad: bool = False) -> bool:
    """True if the user's ingredient `query` covers the recipe's `ingredient`.

    broad=True skips the derived-product rule, for exclusions: excluding "peanut"
    must also exclude "peanut butter chips".
    """
    q = tokens(query)
    ing = tokens(ingredient)
    if not q or not q <= ing:
        return False
    if broad:
        return True
    for extra in ing - q:
        if extra in DERIVED_TOKENS and not (_DERIVED_OK.get(extra, set()) & q):
            return False
    return True


def pantry_keys(items) -> frozenset[frozenset[str]]:
    return frozenset(tokens(i) for i in items)


def is_pantry(ingredient: str, keys: frozenset[frozenset[str]]) -> bool:
    return tokens(ingredient) in keys
