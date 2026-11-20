"""Unit tests for the project's fuzzy-logic allocation assistant."""

import pytest

from backend.fuzzy_logic import (
    low_membership,
    medium_membership,
    high_membership,
    priority_level,
    availability_level,
    demand_level,
    fuzzy_allocation_percentage,
    suggest_allocation,
    check_suggestion_transport,
    adjust_for_transport,
    explain_recommendation,
)
from backend.game_rule import calculate_weight


@pytest.mark.parametrize("value, expected", [(0, 1), (1, 1), (2.5, 0.5), (4, 0), (5, 0)])
def test_low_membership(value, expected):
    assert low_membership(value) == pytest.approx(expected)


@pytest.mark.parametrize("value, expected", [(1, 0), (2, 0.5), (3, 1), (4, 0.5), (5, 0)])
def test_medium_membership(value, expected):
    assert medium_membership(value) == pytest.approx(expected)


@pytest.mark.parametrize("value, expected", [(1, 0), (2, 0), (3.5, 0.5), (5, 1), (6, 1)])
def test_high_membership(value, expected):
    assert high_membership(value) == pytest.approx(expected)


@pytest.mark.parametrize("label, expected", [("Critical", 5), ("High", 4), ("Medium", 3), ("Low", 1), ("Unknown", None)])
def test_priority_level(label, expected):
    assert priority_level(label) == expected


@pytest.mark.parametrize("required, available, expected", [
    (0, 0, 5), (100, 0, 1), (100, 24, 1), (100, 25, 2),
    (100, 50, 3), (100, 75, 4), (100, 100, 5),
])
def test_availability_level(required, available, expected):
    assert availability_level(required, available) == expected


@pytest.mark.parametrize("required, available, expected", [
    (10, 0, 5), (49, 100, 1), (50, 100, 2),
    (100, 100, 3), (150, 100, 4), (200, 100, 5),
])
def test_demand_level(required, available, expected):
    assert demand_level(required, available) == expected


def test_unknown_priority_gets_zero_allocation_percentage():
    assert fuzzy_allocation_percentage("Unknown", 5, 1) == 0


def test_critical_priority_with_high_availability_gets_full_percentage():
    assert fuzzy_allocation_percentage("Critical", 5, 1) == 1.0


def test_low_priority_gets_low_percentage():
    assert fuzzy_allocation_percentage("Low", 5, 5) == 0.2


def test_fuzzy_percentage_is_within_valid_range():
    for priority in ("Critical", "High", "Medium", "Low"):
        for availability in range(1, 6):
            for demand in range(1, 6):
                result = fuzzy_allocation_percentage(priority, availability, demand)
                assert 0 <= result <= 1


def test_suggest_allocation_for_critical_request():
    assert suggest_allocation([10, 20, 30], [100, 100, 100], "Critical", [10, 20, 30]) == [10, 20, 30]


def test_suggestion_never_exceeds_available_stock_or_request():
    required = [100, 50, 80]
    available = [10, 20, 0]
    result = suggest_allocation(required, available, "Critical", [200, 100, 160])
    assert len(result) == 3
    assert all(isinstance(amount, int) for amount in result)
    assert all(0 <= amount <= min(need, stock) for amount, need, stock in zip(result, required, available))


def test_suggest_allocation_with_no_stock():
    assert suggest_allocation([10, 20, 30], [0, 0, 0], "Critical", [10, 20, 30]) == [0, 0, 0]


def test_suggest_allocation_with_unknown_priority():
    assert suggest_allocation([10, 20, 30], [100, 100, 100], "Unknown", [10, 20, 30]) == [0, 0, 0]


@pytest.mark.parametrize("capacity, slots, expected", [
    (1.0, 1, True), (0.01, 1, False), (1.0, 0, False), (1.0, -1, False),
])
def test_check_suggestion_transport(capacity, slots, expected):
    assert check_suggestion_transport([10, 10, 10], capacity, slots) is expected


def test_adjust_for_transport_without_slot():
    assert adjust_for_transport([10, 10, 10], 100, 0) == [0, 0, 0]


def test_adjust_for_transport_without_capacity():
    assert adjust_for_transport([10, 10, 10], 0, 1) == [0, 0, 0]


def test_adjust_for_transport_preserves_valid_allocation():
    allocation = [10, 10, 10]
    assert adjust_for_transport(allocation, 10, 1) == allocation


def test_adjust_for_transport_reduces_weight_and_does_not_mutate_input():
    original = [10, 10, 10]
    adjusted = adjust_for_transport(original, 0.3, 1)
    assert original == [10, 10, 10]
    assert calculate_weight(adjusted) <= 0.3
    assert all(0 <= amount <= 10 for amount in adjusted)


@pytest.mark.parametrize("priority, phrase", [
    ("Critical", "critical emergency"), ("High", "high-priority"),
    ("Medium", "medium-priority"), ("Low", "low-priority"),
])
def test_explanation_mentions_priority(priority, phrase):
    assert phrase in explain_recommendation(priority, [10, 10, 10], [5, 5, 5])


@pytest.mark.parametrize("suggested, phrase", [
    ([10, 10, 10], "fulfilling all"),
    ([5, 5, 5], "partial allocation"),
    ([0, 0, 0], "cannot recommend any"),
])
def test_explanation_describes_fulfilment(suggested, phrase):
    assert phrase in explain_recommendation("High", [10, 10, 10], suggested)
