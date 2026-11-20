
import pandas as pd

from backend.evaluation.baseline import (
    sort_requests,
    simulate_baseline,
    check_request_status,
    allocate_greedily
)


# Sample emergency requests
def sample_requests():

    return pd.DataFrame([
        {
            "request_id": "R002",
            "request_datetime": "2025-10-01 10:00:00",
            "supply_hub": "HUB-AMM",
            "expert_priority_label": "Critical",
            "urgency_level": 5,
            "severity_level": 5,
            "medicine_required_kits": 100,
            "shelter_required_kits": 50,
            "nutrition_required_parcels": 200
        },
        {
            "request_id": "R001",
            "request_datetime": "2025-10-01 09:00:00",
            "supply_hub": "HUB-AMM",
            "expert_priority_label": "Low",
            "urgency_level": 1,
            "severity_level": 1,
            "medicine_required_kits": 100,
            "shelter_required_kits": 50,
            "nutrition_required_parcels": 200
        }
    ])


# Sample hub resources
def sample_resources():

    return {
        "HUB-AMM": {
            "stock": [500, 500, 500],
            "capacity": 100,
            "slots": 2
        }
    }


# TEST 1: FIFO request ordering
def test_fifo_order():

    requests = sample_requests()

    sorted_requests = sort_requests(requests)

    assert list(sorted_requests["request_id"]) == [
        "R001", "R002"
    ]


# TEST 2: FIFO allocation order
def test_fifo_allocation():

    requests = sample_requests()
    resources = sample_resources()

    results = simulate_baseline(requests, resources)

    assert results[0]["request_id"] == "R001"
    assert results[1]["request_id"] == "R002"


# TEST 3: Allocation does not exceed stock
def test_allocation_does_not_exceed_stock():

    requests = sample_requests()
    resources = sample_resources()

    results = simulate_baseline(requests, resources)

    assert sum(r["medicine_allocated"] for r in results) <= 500
    assert sum(r["shelter_allocated"] for r in results) <= 500
    assert sum(r["nutrition_allocated"] for r in results) <= 500


# TEST 4: Allocation does not exceed requirements
def test_allocation_does_not_exceed_requirements():

    requests = sample_requests()
    resources = sample_resources()

    results = simulate_baseline(requests, resources)

    for result in results:

        assert result["medicine_allocated"] <= result["medicine_required_kits"]

        assert result["shelter_allocated"] <= result["shelter_required_kits"]

        assert result["nutrition_allocated"] <= result["nutrition_required_parcels"]


# TEST 5: Original hub resources are not modified
def test_original_resources_are_not_modified():

    requests = sample_requests()
    resources = sample_resources()

    original_resources = sample_resources()

    simulate_baseline(requests, resources)

    assert resources == original_resources


# TEST 6: No flight slots means no allocation
def test_no_flight_slots_means_no_allocation():

    requests = sample_requests()

    resources = {
        "HUB-AMM": {
            "stock": [500, 500, 500],
            "capacity": 100,
            "slots": 0
        }
    }

    results = simulate_baseline(requests, resources)

    for result in results:

        assert result["medicine_allocated"] == 0
        assert result["shelter_allocated"] == 0
        assert result["nutrition_allocated"] == 0


# TEST 7: Missing hub means no allocation
def test_missing_hub_is_unfulfilled():

    requests = sample_requests()
    requests["supply_hub"] = "UNKNOWN-HUB"

    resources = sample_resources()

    results = simulate_baseline(requests, resources)

    for result in results:

        assert result["status"] == "unfulfilled"

        assert result["medicine_allocated"] == 0
        assert result["shelter_allocated"] == 0
        assert result["nutrition_allocated"] == 0


# TEST 8: Allocation respects transport capacity
def test_allocation_respects_transport_capacity():

    required = [100, 50, 200]
    available = [500, 500, 500]
    capacity = 0.5

    allocated = allocate_greedily(
        required,
        available,
        capacity
    )

    used_capacity = (
        allocated[0] * 0.01
        + allocated[1] * 0.05
        + allocated[2] * 0.02
    )

    assert used_capacity <= capacity + 1e-9


# TEST 9: Request status is calculated correctly
def test_request_status():

    assert check_request_status(
        [100, 50, 200],
        [100, 50, 200]
    ) == "fulfilled"

    assert check_request_status(
        [100, 50, 200],
        [50, 0, 100]
    ) == "partial"

    assert check_request_status(
        [100, 50, 200],
        [0, 0, 0]
    ) == "unfulfilled"
