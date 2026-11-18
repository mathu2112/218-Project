RESOURCE_FIELDS = {
    "medicine": (
        "medicine_required_kits",
        "medicine_allocated"
    ),
    "shelter": (
        "shelter_required_kits",
        "shelter_allocated"
    ),
    "nutrition": (
        "nutrition_required_parcels",
        "nutrition_allocated"
    )
}


def safe_number(value):
    """Convert a value to a number safely."""
    try:
        if value is None:
            return 0.0

        number = float(value)

        if number != number:  # Check for NaN
            return 0.0

        return number

    except (ValueError, TypeError):
        return 0.0


def get_request_status(request):
    """
    Determine fulfilment status using all three resource types.
    """

    required = []
    allocated = []

    for resource, fields in RESOURCE_FIELDS.items():
        required_field, allocated_field = fields

        required_amount = safe_number(request.get(required_field))
        allocated_amount = safe_number(request.get(allocated_field))

        required.append(required_amount)
        allocated.append(allocated_amount)

    if all(allocated[i] >= required[i] for i in range(3)):
        return "Fulfilled"

    if all(amount == 0 for amount in allocated):
        return "Unfulfilled"

    return "Partially Fulfilled"


def calculate_fulfilment_metrics(allocations):
    """Calculate fully, partially and unfulfilled request rates."""

    eligible = [
        request for request in allocations
        if str(request.get("status", "")).lower() != "cancelled"
    ]

    total = len(eligible)

    fulfilled = 0
    partially_fulfilled = 0
    unfulfilled = 0

    for request in eligible:
        status = get_request_status(request)

        if status == "Fulfilled":
            fulfilled += 1

        elif status == "Partially Fulfilled":
            partially_fulfilled += 1

        else:
            unfulfilled += 1

    if total == 0:
        return {
            "total_requests": 0,
            "fulfilled_requests": 0,
            "partially_fulfilled_requests": 0,
            "unfulfilled_requests": 0,
            "fulfilment_rate": 0,
            "partial_fulfilment_rate": 0,
            "unfulfilled_rate": 0
        }

    return {
        "total_requests": total,
        "fulfilled_requests": fulfilled,
        "partially_fulfilled_requests": partially_fulfilled,
        "unfulfilled_requests": unfulfilled,
        "fulfilment_rate": round((fulfilled / total) * 100, 2),
        "partial_fulfilment_rate": round(
            (partially_fulfilled / total) * 100, 2
        ),
        "unfulfilled_rate": round((unfulfilled / total) * 100, 2)
    }


def calculate_unmet_demand(allocations):
    """Calculate the remaining demand for each resource."""

    unmet = {}

    for resource, fields in RESOURCE_FIELDS.items():
        required_field, allocated_field = fields

        total_required = 0
        total_allocated = 0

        for request in allocations:
            if str(request.get("status", "")).lower() == "cancelled":
                continue

            required = safe_number(request.get(required_field))
            allocated = safe_number(request.get(allocated_field))

            total_required += required
            total_allocated += min(allocated, required)

        unmet[resource] = {
            "required": round(total_required, 2),
            "allocated": round(total_allocated, 2),
            "unmet": round(max(0, total_required - total_allocated), 2)
        }

    return unmet


def calculate_resource_utilisation(allocations, available_stock):
    """
    Calculate how much of the initial available stock was allocated.
    """

    results = {}

    for resource, fields in RESOURCE_FIELDS.items():
        _, allocated_field = fields

        total_allocated = sum(
            min(
                safe_number(request.get(allocated_field)),
                safe_number(request.get(fields[0]))
            )
            for request in allocations
            if str(request.get("status", "")).lower() != "cancelled"
        )

        available = safe_number(available_stock.get(resource, 0))

        if available > 0:
            utilisation = (total_allocated / available) * 100
        else:
            utilisation = 0

        results[resource] = {
            "available": round(available, 2),
            "allocated": round(total_allocated, 2),
            "utilisation_rate": round(utilisation, 2)
        }

    return results


def calculate_critical_fulfilment(allocations, critical_threshold=4):
    """
    Calculate fulfilment of critical requests.
    """

    critical_requests = []

    for request in allocations:
        if str(request.get("status", "")).lower() == "cancelled":
            continue

        urgency = safe_number(request.get("urgency_level"))
        severity = safe_number(request.get("severity_level"))

        if urgency >= critical_threshold or severity >= critical_threshold:
            critical_requests.append(request)

    total = len(critical_requests)

    fulfilled = sum(
        1 for request in critical_requests
        if get_request_status(request) == "Fulfilled"
    )

    rate = (fulfilled / total * 100) if total > 0 else 0

    return {
        "total_critical_requests": total,
        "fulfilled_critical_requests": fulfilled,
        "critical_fulfilment_rate": round(rate, 2)
    }


def calculate_beneficiaries_served(allocations):
    """
    Calculate beneficiaries served only when an explicit beneficiaries_served value is supplied in the results.
    """

    values = [
        safe_number(request.get("beneficiaries_served"))
        for request in allocations
        if request.get("beneficiaries_served") is not None
    ]

    if not values:
        return None

    return round(sum(values), 2)


def calculate_delivery_delays(allocations):
    """Calculate average delivery delay when delay data is available."""

    delays = []

    for request in allocations:
        if str(request.get("status", "")).lower() == "cancelled":
            continue

        delay = request.get("delivery_delay_hours")

        if delay is not None:
            delays.append(safe_number(delay))

    if not delays:
        return None

    return {
        "average_delay_hours": round(sum(delays) / len(delays), 2),
        "maximum_delay_hours": round(max(delays), 2),
        "requests_with_delay_data": len(delays)
    }


def calculate_metrics(allocations, available_stock=None):
    """
    Calculate all evaluation metrics for one allocation strategy.
    """

    if available_stock is None:
        available_stock = {}

    return {
        "fulfilment": calculate_fulfilment_metrics(allocations),

        "beneficiaries_served":
            calculate_beneficiaries_served(allocations),

        "unmet_demand":
            calculate_unmet_demand(allocations),

        "resource_utilisation":
            calculate_resource_utilisation(
                allocations,
                available_stock
            ),

        "critical_fulfilment":
            calculate_critical_fulfilment(allocations),

        "delivery_delays":
            calculate_delivery_delays(allocations)
    }
