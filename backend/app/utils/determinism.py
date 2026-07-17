"""Deterministic randomness helpers for reproducible Phoring runs.

Python's built-in ``hash`` is intentionally process-randomized, so it must not
be used to derive simulation seeds. These helpers derive stable integer seeds
from explicit run inputs using SHA-256 and return isolated ``random.Random``
instances instead of mutating global random state.
"""

from __future__ import annotations

import hashlib
import json
import random
from typing import Any, Sequence, TypeVar


T = TypeVar("T")


def _canonical_part(value: Any) -> str:
    """Return a stable textual representation for seed derivation."""
    if isinstance(value, (dict, list, tuple, set)):
        normalized = sorted(value) if isinstance(value, set) else value
        return json.dumps(
            normalized,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
    return str(value)


def stable_int_seed(*parts: Any, bits: int = 64) -> int:
    """Derive a stable non-negative integer seed from arbitrary values.

    Args:
        *parts: Values that uniquely identify the deterministic operation.
        bits: Number of digest bits to retain. Must be between 8 and 256 and a
            multiple of 8.
    """
    if bits < 8 or bits > 256 or bits % 8 != 0:
        raise ValueError("bits must be a multiple of 8 between 8 and 256")

    payload = "\x1f".join(_canonical_part(part) for part in parts).encode("utf-8")
    digest = hashlib.sha256(payload).digest()
    return int.from_bytes(digest[: bits // 8], byteorder="big", signed=False)


def deterministic_rng(base_seed: int | str, *namespace: Any) -> random.Random:
    """Create an isolated reproducible random generator for a namespace."""
    return random.Random(stable_int_seed(base_seed, *namespace))


def deterministic_int(
    minimum: int,
    maximum: int,
    base_seed: int | str,
    *namespace: Any,
) -> int:
    """Return a reproducible integer in the inclusive range."""
    if minimum > maximum:
        raise ValueError("minimum cannot be greater than maximum")
    return deterministic_rng(base_seed, *namespace).randint(minimum, maximum)


def deterministic_choice(
    values: Sequence[T],
    base_seed: int | str,
    *namespace: Any,
) -> T:
    """Return a reproducible selection without changing global random state."""
    if not values:
        raise ValueError("values cannot be empty")
    return values[deterministic_rng(base_seed, *namespace).randrange(len(values))]
