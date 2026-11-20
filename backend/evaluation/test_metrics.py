
import pytest

from backend.evaluation.metrics import (
    safe_number,
    get_request_status,
    calculate_fulfilment_metrics,
    calculate_unmet_demand,
    calculate_resource_utilisation,
    calculate_critical_fulfilment,
    calculate_beneficiaries_served,
    calculate_delivery_delays,
    calculate_metrics
)


# Sample allocation records for testing
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


# TEST 1: Safe number conversion
def test_safe_number():

    assert safe_number(100) == 100.0
    assert safe_number("50") == 50.0
    assert safe_number(None) == 0.0
    assert safe_number("invalid") == 0.0


# TEST 2: Request status
def test_get_request_status():

    allocations = sample_allocations()

    assert get_request_status(allocations[0]) == "Fulfilled"

    assert get_request_status(allocations[1]) == "Partially Fulfilled"

    assert get_request_status(allocations[2]) == "Unfulfilled"


# TEST 3: Fulfilment metrics
def test_calculate_fulfilment_metrics():

    results = calculate_fulfilment_metrics(sample_allocations())

    assert results["total_requests"] == 3
    assert results["fulfilled_requests"] == 1
    assert results["partially_fulfilled_requests"] == 1
    assert results["unfulfilled_requests"] == 1

    assert results["fulfilment_rate"] == 33.33
    assert results["partial_fulfilment_rate"] == 33.33
    assert results["unfulfilled_rate"] == 33.33


# TEST 4: Unmet demand
def test_calculate_unmet_demand():

    results = calculate_unmet_demand(sample_allocations())

    assert results["medicine"]["required"] == 250
    assert results["medicine"]["allocated"] == 150
    assert results["medicine"]["unmet"] == 100

    assert results["shelter"]["required"] == 120
    assert results["shelter"]["allocated"] == 50
    assert results["shelter"]["unmet"] == 70

    assert results["nutrition"]["required"] == 400
    assert results["nutrition"]["allocated"] == 250
    assert results["nutrition"]["unmet"] == 150


# TEST 5: Resource utilisation
def test_calculate_resource_utilisation():

    available_stock = {
        "medicine": 300,
        "shelter": 200,
        "nutrition": 500
    }

    results = calculate_resource_utilisation(
        sample_allocations(),
        available_stock
    )

    assert results["medicine"]["utilisation_rate"] == 50.0
    assert results["shelter"]["utilisation_rate"] == 25.0
    assert results["nutrition"]["utilisation_rate"] == 50.0


# TEST 6: Critical request fulfilment
def test_calculate_critical_fulfilment():

    results = calculate_critical_fulfilment(sample_allocations())

    assert results["total_critical_requests"] == 2
    assert results["fulfilled_critical_requests"] == 1
    assert results["critical_fulfilment_rate"] == 50.0


# TEST 7: Beneficiaries served
def test_calculate_beneficiaries_served():

    results = calculate_beneficiaries_served(sample_allocations())

    assert results == 700.0


# TEST 8: Delivery delays
def test_calculate_delivery_delays():

    results = calculate_delivery_delays(sample_allocations())

    assert results["average_delay_hours"] == 3.0
    assert results["maximum_delay_hours"] == 4.0
    assert results["requests_with_delay_data"] == 2


# TEST 9: Cancelled requests should be excluded
def test_cancelled_requests_are_excluded():

    allocations = sample_allocations()

    allocations.append({
        "request_id": "R004",
        "medicine_required_kits": 100,
        "medicine_allocated": 0,
        "shelter_required_kits": 50,
        "shelter_allocated": 0,
        "nutrition_required_parcels": 100,
        "nutrition_allocated": 0,
        "urgency_level": 5,
        "severity_level": 5,
        "status": "cancelled"
    })

    results = calculate_fulfilment_metrics(allocations)

    assert results["total_requests"] == 3


# TEST 10: Empty allocation list
def test_empty_allocations():

    results = calculate_fulfilment_metrics([])

    assert results["total_requests"] == 0
    assert results["fulfilled_requests"] == 0
    assert results["fulfilment_rate"] == 0


# TEST 11: Combined evaluation metrics
def test_calculate_metrics():

    available_stock = {
        "medicine": 300,
        "shelter": 200,
        "nutrition": 500
    }

    results = calculate_metrics(
        sample_allocations(),
        available_stock
    )

    assert "fulfilment" in results
    assert "beneficiaries_served" in results
    assert "unmet_demand" in results
    assert "resource_utilisation" in results
    assert "critical_fulfilment" in results
    assert "delivery_delays" in results

    assert results["fulfilment"]["total_requests"] == 3
    assert results["beneficiaries_served"] == 700.0
