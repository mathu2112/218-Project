
import pandas as pd


def load_data():
    requests = pd.read_csv("data/emergency_requests.csv")
    locations = pd.read_csv("data/locations.csv")
    hubs = pd.read_csv("data/supply_hubs.csv")
    stock = pd.read_csv("data/daily_hub_stock.csv")
    flights = pd.read_csv("data/daily_flight_slots.csv")

    return requests, locations, hubs, stock, flights


def get_requests(requests):
    columns = [
        "request_id",
        "request_datetime",
        "request_type",
        "location_id",
        "location",
        "population_affected",
        "vulnerable_population",
        "medicine_required_kits",
        "shelter_required_kits",
        "nutrition_required_parcels",
        "expert_priority_label",
        "urgency_level",
        "severity_level",
        "medical_emergency",
        "time_sensitivity_hours",
        "delivery_accessibility"
    ]

    return requests[columns].copy()


def get_stock(stock, selected_date):
    daily_stock = stock[stock["date"] == selected_date].copy()

    return daily_stock


def get_flights(flights, selected_date):
    daily_flights = flights[flights["date"] == selected_date].copy()

    return daily_flights

# Get emergency requests for a selected date
def get_requests_by_date(requests, selected_date):
    daily_requests = requests[
        requests["request_datetime"].str[:10] == selected_date
    ].copy()

    return daily_requests