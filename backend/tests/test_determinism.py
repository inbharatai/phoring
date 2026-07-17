import random

import pytest

from app.utils.determinism import (
    deterministic_choice,
    deterministic_int,
    deterministic_rng,
    stable_int_seed,
)


def test_stable_seed_is_repeatable_and_namespace_sensitive():
    assert stable_int_seed("run-1", "profiles", 4) == stable_int_seed(
        "run-1", "profiles", 4
    )
    assert stable_int_seed("run-1", "profiles", 4) != stable_int_seed(
        "run-1", "profiles", 5
    )


def test_dict_order_does_not_change_seed():
    left = {"model": "gemini", "temperature": 0.2}
    right = {"temperature": 0.2, "model": "gemini"}
    assert stable_int_seed(left) == stable_int_seed(right)


def test_rng_does_not_mutate_global_random_state():
    random.seed(12345)
    expected = random.random()

    random.seed(12345)
    deterministic_rng(99, "agent", 7).random()
    observed = random.random()

    assert observed == expected


def test_deterministic_helpers_return_repeatable_values():
    assert deterministic_int(100, 500, 42, "followers", "entity-a") == deterministic_int(
        100, 500, 42, "followers", "entity-a"
    )
    assert deterministic_choice(["a", "b", "c"], 42, "stance") == deterministic_choice(
        ["a", "b", "c"], 42, "stance"
    )


def test_invalid_arguments_raise_clear_errors():
    with pytest.raises(ValueError):
        stable_int_seed("x", bits=7)
    with pytest.raises(ValueError):
        deterministic_int(5, 4, 1)
    with pytest.raises(ValueError):
        deterministic_choice([], 1)
