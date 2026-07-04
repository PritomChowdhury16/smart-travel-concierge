#!/usr/bin/env python3
# mcp_server.py — Smart Travel Concierge MCP Server (stdio transport)
# Exposes travel-domain tools to the ADK agents via the MCP Python SDK.

import json
import random

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("smart-travel-concierge")


# ─────────────────────────────────────────────────────────────────────────────
# Tool 1: get_destination_info
# Returns highlights and travel tips for a destination.
# Used by: destination_researcher, itinerary_builder
# ─────────────────────────────────────────────────────────────────────────────
@mcp.tool()
def get_destination_info(destination: str) -> str:
    """Return highlights and travel tips for a travel destination.

    Args:
        destination: The city or country to look up (e.g. "Paris", "Japan").

    Returns:
        JSON string with destination highlights, top attractions, and tips.
    """
    # Simulated knowledge base
    db = {
        "paris": {
            "highlights": ["Eiffel Tower", "Louvre Museum", "Montmartre", "Seine River cruise"],
            "cuisine": ["Croissants", "Crêpes", "Coq au Vin", "Macarons"],
            "tips": "Book museum tickets in advance. Metro is the best way to get around.",
            "language": "French",
            "currency": "EUR",
        },
        "tokyo": {
            "highlights": ["Shibuya Crossing", "Senso-ji Temple", "Mt. Fuji day trip", "Akihabara"],
            "cuisine": ["Sushi", "Ramen", "Tempura", "Yakitori"],
            "tips": "Get a Suica card for transport. Cash is still widely used.",
            "language": "Japanese",
            "currency": "JPY",
        },
        "new york": {
            "highlights": ["Central Park", "Times Square", "Statue of Liberty", "Brooklyn Bridge"],
            "cuisine": ["NY Pizza", "Bagels", "Pastrami sandwich", "Cheesecake"],
            "tips": "Use the subway for most travel. Book popular restaurants early.",
            "language": "English",
            "currency": "USD",
        },
        "bali": {
            "highlights": ["Ubud Rice Terraces", "Tanah Lot Temple", "Seminyak Beach", "Mount Batur"],
            "cuisine": ["Nasi Goreng", "Satay", "Babi Guling", "Fresh fruit"],
            "tips": "Rent a scooter for easy travel. Respect temple dress codes.",
            "language": "Balinese/Indonesian",
            "currency": "IDR",
        },
    }
    key = destination.lower().strip()
    info = db.get(key, {
        "highlights": [f"Explore the city center of {destination}", "Visit local markets", "Try local cuisine"],
        "cuisine": ["Local specialties"],
        "tips": f"Research {destination} visa requirements and local customs before traveling.",
        "language": "Local language",
        "currency": "Local currency",
    })
    return json.dumps({"destination": destination, **info})


# ─────────────────────────────────────────────────────────────────────────────
# Tool 2: check_visa_requirements
# Returns visa requirements based on traveler nationality and destination.
# Used by: destination_researcher
# ─────────────────────────────────────────────────────────────────────────────
@mcp.tool()
def check_visa_requirements(nationality: str, destination: str) -> str:
    """Check visa requirements for a given nationality traveling to a destination.

    Args:
        nationality: The traveler's nationality (e.g. "American", "British", "Indian").
        destination: The destination country or city (e.g. "Japan", "France").

    Returns:
        JSON string with visa requirement details.
    """
    # Simplified visa logic
    visa_free = {
        "american": ["france", "germany", "japan", "italy", "spain", "mexico", "canada"],
        "british": ["france", "germany", "japan", "italy", "spain", "usa", "canada"],
        "indian": ["maldives", "bhutan", "nepal", "mauritius", "indonesia"],
        "australian": ["japan", "france", "germany", "usa", "canada", "new zealand"],
    }

    nat_key = nationality.lower().strip()
    dest_key = destination.lower().strip()

    free_list = visa_free.get(nat_key, [])
    requires_visa = dest_key not in free_list

    result = {
        "nationality": nationality,
        "destination": destination,
        "visa_required": requires_visa,
        "visa_type": "Tourist Visa" if requires_visa else "Visa-Free Entry",
        "max_stay_days": 30 if requires_visa else 90,
        "processing_time": "5–10 business days" if requires_visa else "N/A",
        "note": (
            f"{nationality} citizens require a tourist visa for {destination}. "
            "Apply at least 2 weeks before travel."
        ) if requires_visa else (
            f"{nationality} citizens can enter {destination} visa-free for up to 90 days."
        ),
    }
    return json.dumps(result)


# ─────────────────────────────────────────────────────────────────────────────
# Tool 3: estimate_flight_cost
# Estimates a flight cost for a given route and travel class.
# Used by: itinerary_builder
# ─────────────────────────────────────────────────────────────────────────────
@mcp.tool()
def estimate_flight_cost(origin: str, destination: str, travel_class: str = "economy") -> str:
    """Estimate round-trip flight cost between two cities.

    Args:
        origin: Departure city (e.g. "London").
        destination: Arrival city (e.g. "Tokyo").
        travel_class: Seat class — "economy", "business", or "first". Defaults to "economy".

    Returns:
        JSON string with estimated cost range and booking tips.
    """
    # Base cost ranges by distance (simplified)
    base_ranges = {
        "economy":  (300, 1200),
        "business": (1500, 5000),
        "first":    (4000, 12000),
    }
    cls = travel_class.lower()
    low, high = base_ranges.get(cls, base_ranges["economy"])
    estimate = random.randint(low, high)

    return json.dumps({
        "origin": origin,
        "destination": destination,
        "travel_class": cls,
        "estimated_cost_usd": estimate,
        "cost_range_usd": f"${low}–${high}",
        "tips": [
            "Book 6–8 weeks in advance for best economy prices.",
            "Use flexible date search to find cheaper fares.",
            "Check airline loyalty programs for upgrades.",
        ],
    })


# ─────────────────────────────────────────────────────────────────────────────
# Tool 4: get_best_travel_season
# Returns the recommended travel months for a destination.
# Used by: destination_researcher
# ─────────────────────────────────────────────────────────────────────────────
@mcp.tool()
def get_best_travel_season(destination: str) -> str:
    """Return the best months to travel to a destination and months to avoid.

    Args:
        destination: The city or country (e.g. "Bali", "Paris").

    Returns:
        JSON string with best months, months to avoid, and weather summary.
    """
    seasons_db = {
        "paris": {
            "best_months": ["April", "May", "June", "September", "October"],
            "avoid_months": ["July", "August"],
            "weather_summary": "Spring and early autumn are mild and less crowded.",
            "peak_season": "Summer (Jul–Aug) — crowded and expensive.",
        },
        "tokyo": {
            "best_months": ["March", "April", "October", "November"],
            "avoid_months": ["July", "August", "June"],
            "weather_summary": "Cherry blossom (Mar–Apr) and autumn foliage (Oct–Nov) are spectacular.",
            "peak_season": "Golden Week (late Apr–early May) — very busy.",
        },
        "bali": {
            "best_months": ["April", "May", "June", "July", "August", "September"],
            "avoid_months": ["January", "February", "December"],
            "weather_summary": "Dry season (Apr–Oct) is ideal. Wet season has heavy rains.",
            "peak_season": "July–August — peak tourist season.",
        },
        "new york": {
            "best_months": ["April", "May", "September", "October"],
            "avoid_months": ["January", "February"],
            "weather_summary": "Spring and fall are comfortable. Winters are cold; summers are hot and humid.",
            "peak_season": "December (holiday season) — very busy.",
        },
    }
    key = destination.lower().strip()
    info = seasons_db.get(key, {
        "best_months": ["March", "April", "May", "October"],
        "avoid_months": ["Peak summer or monsoon months — research locally"],
        "weather_summary": f"Research {destination}'s climate before booking.",
        "peak_season": "Varies by destination.",
    })
    return json.dumps({"destination": destination, **info})


# ─────────────────────────────────────────────────────────────────────────────
# Tool 5: estimate_trip_budget
# Provides a full budget breakdown for a trip.
# Used by: itinerary_builder
# ─────────────────────────────────────────────────────────────────────────────
@mcp.tool()
def estimate_trip_budget(
    destination: str,
    duration_days: int,
    budget_level: str = "mid-range",
) -> str:
    """Estimate a complete trip budget breakdown for a destination.

    Args:
        destination: The travel destination (e.g. "Paris").
        duration_days: Number of days for the trip.
        budget_level: Spending level — "budget", "mid-range", or "luxury".

    Returns:
        JSON string with per-day and total cost estimates by category.
    """
    daily_rates = {
        "budget":    {"accommodation": 40,  "food": 25,  "transport": 10, "activities": 15},
        "mid-range": {"accommodation": 120, "food": 60,  "transport": 25, "activities": 40},
        "luxury":    {"accommodation": 350, "food": 150, "transport": 80, "activities": 120},
    }
    lvl = budget_level.lower().strip()
    rates = daily_rates.get(lvl, daily_rates["mid-range"])

    breakdown = {cat: rate * duration_days for cat, rate in rates.items()}
    total = sum(breakdown.values())

    return json.dumps({
        "destination": destination,
        "duration_days": duration_days,
        "budget_level": lvl,
        "daily_rates_usd": rates,
        "total_breakdown_usd": breakdown,
        "total_estimated_usd": total,
        "note": "Estimates exclude international flights. Add 15% buffer for unexpected costs.",
    })


if __name__ == "__main__":
    mcp.run(transport="stdio")
