
# This baseline is used to compare a simple allocation
# strategy against the Fuzzy Logic AI approach.

# It allocates resources based on:
# 1. Expert priority
# 2. Available hub stock
# 3. Aircraft transport capacity
# 4. Available flight slots


import copy

from backend.game_rule import calculate_weight



PRIORITY_ORDER = {
    "Critical": 1,
    "High": 2,
    "Medium": 3,
    "Low": 4
}



#RESOURCE WEIGHTS


# These weights must match game_rule.py

RESOURCE_WEIGHTS = [0.01, 0.05, 0.02]



#SAFE NUMBER CONVERSION

def safe_int(value):
    """Convert values safely into non-negative integers."""

    try:
        if value is None:
            return 0

        return max(0, int(float(value)))

    except (ValueError, TypeError):
        return 0


#SORT EMERGENCY REQUESTS


def sort_requests(daily_requests):
    """
    Sort requests according to expert priority.

    Critical requests are processed first,
    followed by High, Medium and Low requests.

    Requests with equal priority are sorted
    by their request time.
    """

    sorted_requests = daily_requests.copy()

    sorted_requests["_priority_order"] = (
        sorted_requests["expert_priority_label"]
        .map(PRIORITY_ORDER)
        .fillna(5)
    )

    sorted_requests = sorted_requests.sort_values(
        by=["_priority_order", "request_datetime"],
        ascending=True,
        na_position="last"
    )

    return sorted_requests.drop(columns=["_priority_order"])


# --------------------------------------------------
# 5. CHECK REQUEST FULFILMENT
# --------------------------------------------------

def check_request_status(required, allocated):
    """
    Determine whether an emergency request
    is fulfilled, partially fulfilled or unfulfilled.
    """

    if all(allocated[i] >= required[i] for i in range(3)):
        return "Fulfilled"

    if all(amount == 0 for amount in allocated):
        return "Unfulfilled"

    return "Partially Fulfilled"



#GREEDY RESOURCE ALLOCATION

def allocate_greedily(required, available, capacity):
    """
    Allocate the maximum possible quantity of resources.

    The allocation follows a fixed order:
    Medicine -> Shelter -> Nutrition.

    Allocation is restricted by:
    - Required quantities
    - Available hub stock
    - Remaining aircraft capacity
    """

    allocated = [0, 0, 0]

    remaining_capacity = max(0, float(capacity))

    for i in range(3):

        # Maximum quantity allowed by request and stock
        maximum = min(required[i], available[i])

        # Maximum quantity that fits remaining capacity
        capacity_limit = int(
            remaining_capacity / RESOURCE_WEIGHTS[i]
        )

        # Allocate the maximum quantity possible
        amount = min(maximum, capacity_limit)

        allocated[i] = amount

        # Update remaining aircraft capacity
        remaining_capacity -= (
            amount * RESOURCE_WEIGHTS[i]
        )

    return allocated



# BASELINE SIMULATION


def simulate_baseline(daily_requests, initial_hub_resources):
    """
    Run the priority-based greedy allocation simulation.

    Parameters:
        daily_requests:
            Emergency requests for the selected date.

        initial_hub_resources:
            Initial stock, aircraft capacity and flight
            slots for each supply hub.

    Returns:
        baseline_history:
            List of allocation results for each request.
    """

    # Create independent resources.
    # This prevents changes to the original game resources.
    baseline_resources = copy.deepcopy(initial_hub_resources)

    # Sort requests by priority
    sorted_requests = sort_requests(daily_requests)

    # Store allocation results
    baseline_history = []

    # Process each emergency request
    for _, request in sorted_requests.iterrows():

        hub_id = request["supply_hub"]

        # Read required quantities
        required = [
            safe_int(request["medicine_required_kits"]),
            safe_int(request["shelter_required_kits"]),
            safe_int(request["nutrition_required_parcels"])
        ]

        # Prepare the result record
        record = {
            "request_id": request["request_id"],
            "supply_hub": hub_id,
            "expert_priority_label": request["expert_priority_label"],
            "urgency_level": safe_int(request.get("urgency_level")),
            "severity_level": safe_int(request.get("severity_level")),

            "medicine_required_kits": required[0],
            "shelter_required_kits": required[1],
            "nutrition_required_parcels": required[2],

            "medicine_allocated": 0,
            "shelter_allocated": 0,
            "nutrition_allocated": 0,

            "status": "Unfulfilled"
        }

        # Check whether the assigned hub exists
        if hub_id not in baseline_resources:
            baseline_history.append(record)
            continue

        resources = baseline_resources[hub_id]

        # Check transport availability
        if resources["slots"] <= 0 or resources["capacity"] <= 0:
            baseline_history.append(record)
            continue

        # Perform greedy allocation
        allocated = allocate_greedily(
            required,
            resources["stock"],
            resources["capacity"]
        )

        # Update resources only if something is allocated
        if any(amount > 0 for amount in allocated):

            # Calculate allocated transport weight
            total_weight = calculate_weight(allocated)

            # Reduce available hub stock
            for i in range(3):
                resources["stock"][i] -= allocated[i]

            # Reduce remaining aircraft capacity
            resources["capacity"] -= total_weight

            # Use one flight slot
            resources["slots"] -= 1

        # Determine fulfilment status
        status = check_request_status(
            required,
            allocated
        )

        # Update result record
        record["medicine_allocated"] = allocated[0]
        record["shelter_allocated"] = allocated[1]
        record["nutrition_allocated"] = allocated[2]
        record["status"] = status

        # Save the result
        baseline_history.append(record)

    return baseline_history
