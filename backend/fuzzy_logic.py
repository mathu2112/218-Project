from backend.game_rule import calculate_weight
# FUZZY LOGIC AI ASSISTANT


# Low membership
def low_membership(value):
    if value <= 1:
        return 1

    if value >= 4:
        return 0

    return (4 - value) / 3


# Medium membership
def medium_membership(value):
    if value <= 1 or value >= 5:
        return 0

    if value <= 3:
        return (value - 1) / 2

    return (5 - value) / 2


# High membership
def high_membership(value):
    if value <= 2:
        return 0

    if value >= 5:
        return 1

    return (value - 2) / 3


# Convert affected population to a 1-5 scale
def population_level(population):
    if population <= 5000:
        return 1

    if population <= 10000:
        return 2

    if population <= 15000:
        return 3

    if population <= 20000:
        return 4

    return 5


# Calculate priority using fuzzy IF-THEN rules
def calculate_priority(urgency, severity, population):

    # Convert population to a 1-5 scale
    population = population_level(population)

    # Rule 1: High urgency OR high severity OR high population
    high = max(
        high_membership(urgency),
        high_membership(severity),
        high_membership(population)
    )

    # Rule 2: Medium urgency OR medium severity OR medium population
    medium = max(
        medium_membership(urgency),
        medium_membership(severity),
        medium_membership(population)
    )

    # Rule 3: Low urgency AND low severity AND low population
    low = min(
        low_membership(urgency),
        low_membership(severity),
        low_membership(population)
    )

    # Calculate final priority score
    total = high + medium + low

    if total == 0:
        return 0

    score = (high * 90 + medium * 50 + low * 10) / total

    return round(score, 2)

# Suggest resource allocations based on priority and stock
def suggest_allocation(required, available, priority):

    if priority >= 70:
        percentage = 1.0

    elif priority >= 40:
        percentage = 0.6

    else:
        percentage = 0.3

    suggested = []

    for i in range(3):
        amount = int(required[i] * percentage)

        # Do not suggest more than available stock
        amount = min(amount, available[i])

        suggested.append(amount)

    return suggested

# Explain the AI recommendation
def explain_recommendation(priority):

    if priority >= 70:
        return "High priority: This request needs urgent attention. The AI recommends allocating as many required resources as available."

    elif priority >= 40:
        return "Medium priority: This request has moderate needs. The AI recommends allocating 60% of the required resources."

    else:
        return "Low priority: This request has lower relative priority. The AI recommends allocating 30% of the required resources."

# Check whether the suggested allocation can be transported
def check_suggestion_transport(suggested, capacity, slots):

    if slots <= 0:
        return False

    if calculate_weight(suggested) > capacity:
        return False

    return True

