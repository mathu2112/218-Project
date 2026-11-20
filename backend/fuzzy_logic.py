"""Fuzzy resource recommendations and transport checks."""

from backend.game_rule import check_transport_capacity


# FUZZY LOGIC AI ASSISTANT
# Recommends resource allocations based on expert priority,
# available supplies, and competing demand.


# --------------------------------------------------
# 1. FUZZY MEMBERSHIP FUNCTIONS
# --------------------------------------------------

# Calculate how strongly a value belongs to the low category
def low_membership(value):
    if value <= 1:
        return 1

    if value >= 4:
        return 0

    return (4 - value) / 3


# Calculate how strongly a value belongs to the medium category
def medium_membership(value):
    if value <= 1 or value >= 5:
        return 0

    if value <= 3:
        return (value - 1) / 2

    return (5 - value) / 2


# Calculate how strongly a value belongs to the high category
def high_membership(value):
    if value <= 2:
        return 0

    if value >= 5:
        return 1

    return (value - 2) / 3


# --------------------------------------------------
# 2. CONVERT INPUTS INTO LEVELS
# --------------------------------------------------

# Convert the instructor's expert priority label to a 1-5 level
def priority_level(label):

    if label == "Critical":
        return 5

    if label == "High":
        return 4

    if label == "Medium":
        return 3

    if label == "Low":
        return 1

    return None


# Measure how much stock is available compared to the request
def availability_level(required, available):

    if required <= 0:
        return 5

    # Compare available stock with required quantity
    ratio = available / required

    if ratio < 0.25:
        return 1

    if ratio < 0.50:
        return 2

    if ratio < 0.75:
        return 3

    if ratio < 1:
        return 4

    return 5


# Measure total resource demand compared to available stock
def demand_level(total_required, available):

    if available <= 0:
        return 5

    # Compare total demand with available stock
    ratio = total_required / available

    if ratio < 0.5:
        return 1

    if ratio < 1:
        return 2

    if ratio < 1.5:
        return 3

    if ratio < 2:
        return 4

    return 5


# --------------------------------------------------
# 3. FUZZY ALLOCATION RULES
# --------------------------------------------------

# Calculate the recommended allocation percentage using fuzzy logic
def fuzzy_allocation_percentage(priority, availability, demand):

    # Convert the expert priority label into a numerical level
    priority = priority_level(priority)

    if priority is None:
        return 0

    # Calculate fuzzy membership values for priority
    priority_high = high_membership(priority)
    priority_medium = medium_membership(priority)
    priority_low = low_membership(priority)

    # Calculate fuzzy membership values for availability
    availability_high = high_membership(availability)
    availability_low = low_membership(availability)

    # Calculate fuzzy membership values for demand
    demand_high = high_membership(demand)
    demand_low = low_membership(demand)

    # Apply fuzzy rules using priority, availability, and demand
    rule1 = min(priority_high, availability_high)
    rule2 = min(priority_high, availability_low)
    rule3 = min(priority_medium, demand_low)
    rule4 = min(priority_medium, demand_high)
    rule5 = min(priority_low, demand_high)
    rule6 = min(priority_low, demand_low)

    # Combine rules that recommend the same allocation level
    high_allocation = max(rule1, rule3)
    medium_allocation = max(rule2, rule4)
    low_allocation = max(rule5, rule6)

    # Calculate the total strength of the activated rules
    total = high_allocation + medium_allocation + low_allocation

    # Use a default percentage if no rules are activated
    if total == 0:
        return 0.5

    # Calculate the final percentage using a weighted average
    percentage = (
        high_allocation * 1.0 +
        medium_allocation * 0.6 +
        low_allocation * 0.2
    ) / total

    return round(percentage, 2)


# --------------------------------------------------
# 4. RESOURCE ALLOCATION RECOMMENDATION
# --------------------------------------------------

# Suggest medicine, shelter, and nutrition allocations
def suggest_allocation(required, available, priority, total_demand):

    suggested = []

    # Calculate recommendations separately for each resource
    for i in range(3):

        # Measure availability and demand for this resource
        availability = availability_level(required[i], available[i])
        demand = demand_level(total_demand[i], available[i])

        # Get the fuzzy allocation percentage
        percentage = fuzzy_allocation_percentage(
            priority, availability, demand
        )

        # Calculate the recommended resource quantity
        amount = int(required[i] * percentage)

        # Do not allocate more than the available stock
        amount = min(amount, available[i])

        suggested.append(amount)

    return suggested


# --------------------------------------------------
# 5. TRANSPORT CAPACITY CHECKS
# --------------------------------------------------

def check_suggestion_transport(suggested, capacity, slots):
    """Check the slot and cargo limits used by the player and the AI."""
    return slots > 0 and check_transport_capacity(suggested, capacity)


def adjust_for_transport(suggested, capacity, slots):
    """Trim a copy of the recommendation to fit the available transport."""
    if slots <= 0 or capacity <= 0:
        return [0, 0, 0]

    adjusted = suggested.copy()
    while not check_transport_capacity(adjusted, capacity):
        # Reduce each nonzero supply by one unit to preserve the existing policy.
        adjusted = [max(0, amount - 1) for amount in adjusted]

    return adjusted


# --------------------------------------------------
# 6. AI RECOMMENDATION EXPLANATION
# --------------------------------------------------

# Generate a simple explanation of the AI recommendation
def explain_recommendation(priority, required, suggested):

    # Explain the request's expert priority
    if priority == "Critical":
        explanation = "This is a critical emergency request. "

    elif priority == "High":
        explanation = "This is a high-priority emergency request. "

    elif priority == "Medium":
        explanation = "This is a medium-priority emergency request. "

    else:
        explanation = "This is a low-priority emergency request. "

    # Explain whether the AI recommends full or partial fulfilment
    if suggested == required:
        explanation += "The AI recommends fulfilling all requested resources."

    elif all(amount == 0 for amount in suggested):
        explanation += "The AI cannot recommend any resources under the current conditions."

    else:
        explanation += (
            "The AI recommends a partial allocation based on "
            "resource availability and competing demand."
        )

    return explanation
