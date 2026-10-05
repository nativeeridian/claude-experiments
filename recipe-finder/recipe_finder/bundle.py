"""The compact on-disk format the app searches, readable with numpy and the stdlib.

A bundle directory holds:
  index.npz         numeric columns plus flattened ingredient and keyword indexes
  strings.json.gz   recipe names, categories, ingredient vocabulary, keyword tokens, metadata
  details-NN.bin    full recipes as JSON, LZMA-compressed in blocks of BLOCK_SIZE recipes,
                    split into shards that stay well under GitHub's file size limits

Rows are recipes sorted by id; row i is the same recipe in every file.
"""

from __future__ import annotations

import gzip
import json
import lzma
import math
import re
from functools import lru_cache
from pathlib import Path

import numpy as np

from . import ingredients as ing

DEFAULT_BUNDLE_DIR = Path(__file__).resolve().parent.parent / "bundle"
FORMAT_VERSION = 1
BLOCK_SIZE = 64
SHARD_BYTES = 24_000_000

_WORD = re.compile(r"[a-z0-9]+")


def text_tokens(text: str) -> list[str]:
    """Searchable words of a recipe name, category or tag (also used on queries)."""
    return [ing.singularize(w) for w in _WORD.findall(text.lower())]


def _jsonable(value):
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, np.generic):
        return _jsonable(value.item())
    if isinstance(value, np.ndarray):
        return [_jsonable(v) for v in value.tolist()]
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    return value


def write(recipes, snippets: dict[int, list[dict]], out_dir: Path, meta: dict) -> None:
    """Write a bundle from a DataFrame of processed recipes (see data.process).

    `snippets` maps recipe id -> review snippets; `meta` is stored as-is.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("details-*.bin"):
        old.unlink()
    recipes = recipes.sort_values("id").reset_index(drop=True)

    # Ingredient index: each recipe's ingredients as ids into a shared vocabulary.
    vocab: dict[str, int] = {}
    flat_vocab: list[int] = []
    row_bounds = [0]
    for names in recipes["ingredients"]:
        for name in names:
            flat_vocab.append(vocab.setdefault(ing.clean_name(name), len(vocab)))
        row_bounds.append(len(flat_vocab))

    # Keyword index: token -> rows whose name, category or Food.com tags contain it.
    postings: dict[str, list[int]] = {}
    for row, (name, cat, tags) in enumerate(zip(recipes["name"], recipes["category"], recipes["keywords"])):
        words = " ".join([name or "", cat if isinstance(cat, str) else "", *list(tags)])
        for tok in set(text_tokens(words)):
            postings.setdefault(tok, []).append(row)
    tokens = sorted(postings)
    tok_rows = [r for t in tokens for r in postings[t]]
    tok_bounds = np.cumsum([0] + [len(postings[t]) for t in tokens])

    categories = sorted({c for c in recipes["category"] if isinstance(c, str)})
    cat_index = {c: i for i, c in enumerate(categories)}

    # Full recipes, compressed in blocks so one lookup decompresses ~64 recipes.
    records = recipes.to_dict("records")
    blocks = []  # (shard, start, length)
    shard, shard_file, offset = -1, None, SHARD_BYTES
    for start in range(0, len(records), BLOCK_SIZE):
        chunk = []
        for rec in records[start : start + BLOCK_SIZE]:
            rec = {k: _jsonable(v) for k, v in rec.items()}
            rec["review_snippets"] = snippets.get(rec["id"], [])
            chunk.append(rec)
        data = lzma.compress(json.dumps(chunk, ensure_ascii=False).encode())
        if offset + len(data) > SHARD_BYTES:
            if shard_file:
                shard_file.close()
            shard, offset = shard + 1, 0
            shard_file = open(out_dir / f"details-{shard:02d}.bin", "wb")
        shard_file.write(data)
        blocks.append((shard, offset, len(data)))
        offset += len(data)
    if shard_file:
        shard_file.close()

    np.savez_compressed(
        out_dir / "index.npz",
        ids=recipes["id"].to_numpy(np.int64),
        rating=recipes["rating"].to_numpy(np.float32),
        reviews=recipes["reviews"].to_numpy(np.int32),
        minutes=recipes["total_minutes"].to_numpy(np.float32),
        calories=recipes["calories"].to_numpy(np.float32),
        servings=recipes["servings"].to_numpy(np.float32),
        category=np.array([cat_index.get(c, -1) for c in recipes["category"]], np.int16),
        flat_vocab=np.array(flat_vocab, np.int32),
        row_bounds=np.array(row_bounds, np.int64),
        tok_rows=np.array(tok_rows, np.int32),
        tok_bounds=tok_bounds.astype(np.int64),
        blocks=np.array(blocks, np.int64).reshape(-1, 3),
    )
    strings = {
        "meta": {**meta, "format": FORMAT_VERSION, "block_size": BLOCK_SIZE, "recipes": len(records)},
        "names": recipes["name"].tolist(),
        "categories": categories,
        "vocab": list(vocab),
        "tokens": tokens,
    }
    with gzip.open(out_dir / "strings.json.gz", "wt", encoding="utf-8") as f:
        json.dump(strings, f, ensure_ascii=False)


class Bundle:
    """Read-only view of a bundle directory."""

    def __init__(self, path: Path | str | None = None):
        self.path = Path(path) if path else DEFAULT_BUNDLE_DIR
        if not (self.path / "index.npz").exists():
            raise FileNotFoundError(
                f"No recipe bundle in {self.path}. Run `python -m recipe_finder build` first."
            )
        with np.load(self.path / "index.npz") as npz:
            self.arrays = {k: npz[k] for k in npz.files}
        with gzip.open(self.path / "strings.json.gz", "rt", encoding="utf-8") as f:
            strings = json.load(f)
        self.meta = strings["meta"]
        self.names = strings["names"]
        self.categories = strings["categories"]
        self.vocab = strings["vocab"]
        self.tokens = strings["tokens"]
        self._block = lru_cache(maxsize=64)(self._read_block)

    def _read_block(self, block: int) -> list[dict]:
        shard, start, length = (int(x) for x in self.arrays["blocks"][block])
        with open(self.path / f"details-{shard:02d}.bin", "rb") as f:
            f.seek(start)
            return json.loads(lzma.decompress(f.read(length)))

    def details(self, row: int) -> dict:
        """The full stored recipe at `row` (a fresh copy, safe to modify)."""
        size = self.meta["block_size"]
        return dict(self._block(row // size)[row % size])
