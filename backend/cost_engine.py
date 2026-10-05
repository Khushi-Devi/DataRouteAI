import pandas as pd


PRICING_FILE = "data/pricing_rules.csv"


def load_pricing_rules():
    return pd.read_csv(PRICING_FILE)


def calculate_tiered_cost(volume_gb, rules):
    """
    Calculate progressive tiered pricing.
    """

    total_cost = 0.0

    for _, rule in rules.sort_values("min_volume_gb").iterrows():

        price = rule["price_per_unit"]

        if pd.isna(price):
            continue

        min_volume = rule["min_volume_gb"]
        max_volume = rule["max_volume_gb"]

        if volume_gb <= min_volume:
            continue

        tier_volume = min(volume_gb, max_volume) - min_volume

        if tier_volume > 0:
            total_cost += tier_volume * price

    return total_cost


def calculate_cost(
    provider_id,
    source_region,
    destination_region,
    transfer_type,
    volume_gb
):
    rules = load_pricing_rules()

    matching_rules = rules[
        (rules["provider_id"] == provider_id) &
        (
            (rules["source_region"] == source_region) |
            (rules["source_region"] == "ANY")
        ) &
        (
            (rules["destination_region"] == destination_region) |
            (rules["destination_region"] == "ANY")
        ) &
        (rules["transfer_type"] == transfer_type)
    ]

    if matching_rules.empty:
        return {
            "available": False,
            "cost": None,
            "reason": "No pricing rule found"
        }

    if matching_rules["price_per_unit"].notna().sum() == 0:
        return {
            "available": False,
            "cost": None,
            "reason": "Pricing exists but price is unavailable"
        }

    cost = calculate_tiered_cost(volume_gb, matching_rules)

    return {
        "available": True,
        "cost": round(cost, 4),
        "currency": matching_rules.iloc[0]["currency"],
        "billing_unit": matching_rules.iloc[0]["billing_unit"]
    }