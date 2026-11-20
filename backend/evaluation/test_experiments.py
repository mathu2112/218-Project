
import pytest

from backend.evaluation.experiments import (
    run_experiment,
    run_current_backend_evaluation,
    compare_strategies
)


# Sample allocation records
def sample_allocations():

    return [
        {
            "request_id": "R001",
            "medicine_required_kits": 100,
            "medicine_allocated": 100,
            "shelter_required_kits": 50,
            "shelter_allocated": 50,
            "nutrition_required_parcels": 200,
            "nutrition_allocated": 200,
            "urgency_level": 5,
            "severity_level": 5,
            "beneficiaries_served": 500,
            "delivery_delay_hours": 2,
            "status": "fulfilled"
        },
        {
            "request_id": "R002",
            "medicine_required_kits": 100,
            "medicine_allocated": 50,
            "shelter_required_kits": 50,
            "shelter_allocated": 0,
            "nutrition_required_parcels": 100,
            "nutrition_allocated": 50,
            "urgency_level": 4,
            "severity_level": 3,
            "beneficiaries_served": 200,
            "delivery_delay_hours": 4,
            "status": "partial"
        },
        {
            "request_id": "R003",
            "medicine_required_kits": 50,
            "medicine_allocated": 0,
            "shelter_required_kits": 20,
            "shelter_allocated": 0,
            "nutrition_required_parcels": 100,
            "nutrition_allocated": 0,
            "urgency_level": 1,
            "severity_level": 1,
            "beneficiaries_served": None,
            "delivery_delay_hours": None,
            "status": "unfulfilled"
        }
    ]


# Sample available stock
def sample_stock():

    return {
        "medicine": 300,
        "shelter": 200,
        "nutrition": 500
    }


# TEST 1: Run a single experiment
def test_run_experiment():

    allocations = sample_allocations()

    results = run_experiment(
        "AI Recommended Allocation",
        allocations,
        sample_stock()
    )

    assert results["strategy"] == "AI Recommended Allocation"
    assert results["scenario"] == "Normal Conditions"
    assert "metrics" in results


# TEST 2: Custom scenario name
def test_run_experiment_custom_scenario():

    results = run_experiment(
        "FIFO Baseline",
        sample_allocations(),
        sample_stock(),
        scenario_name="Limited Resources"
    )

    assert results["scenario"] == "Limited Resources"


# TEST 3: Run comparison of all three strategies
def test_run_current_backend_evaluation():

    allocations = sample_allocations()

    results = run_current_backend_evaluation(
        ai_allocations=allocations,
        human_allocations=allocations,
        available_stock=sample_stock(),
        baseline_allocations=allocations
    )

    assert len(results) == 3

    strategies = [result["strategy"] for result in results]

    assert "AI Recommended Allocation" in strategies
    assert "Manual + AI" in strategies
    assert "Greedy Baseline" in strategies


# TEST 4: Run evaluation without baseline
def test_evaluation_without_baseline():

    allocations = sample_allocations()

    results = run_current_backend_evaluation(
        ai_allocations=allocations,
        human_allocations=allocations,
        available_stock=sample_stock()
    )

    assert len(results) == 2


# TEST 5: Compare strategy results
def test_compare_strategies():

    allocations = sample_allocations()

    results = run_current_backend_evaluation(
        ai_allocations=allocations,
        human_allocations=allocations,
        available_stock=sample_stock(),
        baseline_allocations=allocations
    )

    comparison = compare_strategies(results)

    assert len(comparison) == 3

    for strategy in comparison:

        assert "strategy" in strategy
        assert "scenario" in strategy
        assert "fulfilment_rate" in strategy
        assert "partial_fulfilment_rate" in strategy
        assert "unfulfilled_rate" in strategy
        assert "critical_fulfilment_rate" in strategy
        assert "medicine_unmet" in strategy
        assert "shelter_unmet" in strategy
        assert "nutrition_unmet" in strategy


# TEST 6: Check comparison values
def test_comparison_metric_values():

    allocations = sample_allocations()

    results = run_current_backend_evaluation(
        ai_allocations=allocations,
        human_allocations=allocations,
        available_stock=sample_stock(),
        baseline_allocations=allocations
    )

    comparison = compare_strategies(results)

    for strategy in comparison:

        assert strategy["fulfilment_rate"] == 33.33
        assert strategy["partial_fulfilment_rate"] == 33.33
        assert strategy["unfulfilled_rate"] == 33.33


# TEST 7: Empty experiment results
def test_compare_empty_results():

    comparison = compare_strategies([])

    assert comparison == []
