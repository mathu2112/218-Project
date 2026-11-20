
import copy
import pandas as pd

from backend.game_rule import calculate_weight


# Resource weights in tonnes
RESOURCE_WEIGHTS = [0.01, 0.05, 0.02]


def safe_int(value):
    """Convert a value to an integer safely."""
    try:
        if pd.isna(value):
            return 0
        return max(0, int(float(value)))
    except (ValueError, TypeError):
        return 0


def sort_requests(daily_requests):
    """
    Sort requests using FIFO.

    The earliest request_datetime is processed first.
    Priority does not affect the order.
    """
    return daily_requests.sort_values(
        by=["request_datetime", "request_id"],
        ascending=[True, True],
        na_position="last"
    ).copy()


def check_request_status(required, allocated):
    """Determine whether a request is fulfilled, partially fulfilled or unfulfilled."""

    total_required = sum(required)
    total_allocated = sum(allocated)

    if total_required == 0:
        return "fulfilled"

    if total_allocated >= total_required:
        return "fulfilled"

    if total_allocated > 0:
        return "partial"

    return "unfulfilled"


def allocate_greedily(required, available, capacity):
    """
    Allocate resources in a fixed order:
    Medicine -> Shelter -> Nutrition.

    Allocation cannot exceed the required quantity,
    available stock or remaining transport capacity.
    """

    allocated = [0, 0, 0]

    remaining_capacity = max(0, float(capacity))

    for i in range(3):

        required_amount = safe_int(required[i])
        available_amount = safe_int(available[i])

        # Maximum possible allocation based on demand and stock
        maximum = min(required_amount, available_amount)

        # Weight per unit of the resource
        weight = RESOURCE_WEIGHTS[i]

        # Calculate how many units can fit within remaining capacity
        if weight > 0:
            capacity_limit = int(remaining_capacity // weight)
        else:
            capacity_limit = maximum

        # Final allocation
        quantity = min(maximum, capacity_limit)

        allocated[i] = quantity

        # Reduce remaining transport capacity
        remaining_capacity -= quantity * weight

    return allocated


def simulate_baseline(daily_requests, initial_hub_resources):
    """
    Run the FIFO baseline allocation simulation.

    Requests are processed from earliest to latest arrival time.
    Each request is allocated resources subject to:
    - Available hub stock
    - Remaining transport capacity
    - Available flight slots

    The original hub resources are not modified.
    """

    # Make an independent copy of the hub resources
    hub_resources = copy.deepcopy(initial_hub_resources)

    # Sort requests using FIFO
    sorted_requests = sort_requests(daily_requests)

    baseline_history = []

    for _, request in sorted_requests.iterrows():

        request_id = request["request_id"]
        supply_hub = request["supply_hub"]

        priority = request.get("expert_priority_label", "Unknown")
        urgency = request.get("urgency_level", 0)
        severity = request.get("severity_level", 0)

        # Read required resources
        required = [
            safe_int(request["medicine_required_kits"]),
            safe_int(request["shelter_required_kits"]),
            safe_int(request["nutrition_required_parcels"])
        ]

        # Default allocation is zero
        allocated = [0, 0, 0]

        # Check whether the assigned hub exists
        if supply_hub in hub_resources:

            hub = hub_resources[supply_hub]

            available_stock = hub["stock"]
            remaining_capacity = hub["capacity"]
            available_slots = hub["slots"]

            # Allocate only if a flight slot is available
            if available_slots > 0 and remaining_capacity > 0:

                allocated = allocate_greedily(
                    required,
                    available_stock,
                    remaining_capacity
                )

                # Check whether any resources were allocated
                if sum(allocated) > 0:

                    # Reduce hub stock
                    for i in range(3):
                        hub["stock"][i] -= allocated[i]

                    # Calculate used transport capacity
                    used_capacity = calculate_weight(allocated)

                    hub["capacity"] -= used_capacity

                    # One flight slot is used for this request
                    hub["slots"] -= 1

        # Determine request status
        status = check_request_status(required, allocated)

        # Save allocation results
        record = {
            "request_id": request_id,
            "request_datetime": request.get("request_datetime"),
            "supply_hub": supply_hub,
            "expert_priority_label": priority,
            "urgency_level": urgency,
            "severity_level": severity,

            "medicine_required_kits": required[0],
            "shelter_required_kits": required[1],
            "nutrition_required_parcels": required[2],

            "medicine_allocated": allocated[0],
            "shelter_allocated": allocated[1],
            "nutrition_allocated": allocated[2],

            "status": status
        }

        baseline_history.append(record)

    return baseline_history
