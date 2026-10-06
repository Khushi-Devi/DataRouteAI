
# import pandas as pd


# PRICING_FILE = "data/pricing_rules.csv"

# # Default Azure network path for the current prototype.
# # We can add TRANSIT_ISP later when the optimizer is ready.
# DEFAULT_AZURE_NETWORK_PATH = "PREMIUM_GLOBAL_NETWORK"


# def load_pricing_rules():
#     return pd.read_csv(PRICING_FILE)


# def convert_volume(volume, from_unit, to_unit):
#     if from_unit == to_unit:
#         return volume

#     if from_unit == "GB" and to_unit == "GiB":
#         return volume * (1_000_000_000 / 1_073_741_824)

#     if from_unit == "GiB" and to_unit == "GB":
#         return volume * (1_073_741_824 / 1_000_000_000)

#     raise ValueError(f"Unsupported conversion: {from_unit} -> {to_unit}")


# def calculate_tiered_cost(volume_gb, rules):
#     """
#     Calculate progressive tiered pricing.
#     """

#     total_cost = 0.0

#     for _, rule in rules.sort_values("min_volume_gb").iterrows():

#         price = rule["price_per_unit"]

#         if pd.isna(price):
#             continue

#         min_volume = rule["min_volume_gb"]
#         max_volume = rule["max_volume_gb"]

#         if volume_gb <= min_volume:
#             continue

#         tier_volume = min(volume_gb, max_volume) - min_volume

#         if tier_volume > 0:
#             total_cost += tier_volume * price

#     return total_cost


# def calculate_cost(
#     provider_id,
#     source_region,
#     destination_region,
#     transfer_type,
#     volume_gb,
#     network_path=None
# ):
#     """
#     Calculate data transfer cost for a provider route.

#     For Azure, Premium Global Network is used by default.
#     Transit ISP can be added later when route optimization is implemented.
#     """

#     rules = load_pricing_rules()

#     # Use default Azure path when no path is provided.
#     if provider_id == "AZURE" and network_path is None:
#         network_path = DEFAULT_AZURE_NETWORK_PATH

#     # Filter basic pricing rules.
#     matching_rules = rules[
#         (rules["provider_id"] == provider_id) &
#         (
#             (rules["source_region"] == source_region) |
#             (rules["source_region"] == "ANY")
#         ) &
#         (
#             (rules["destination_region"] == destination_region) |
#             (rules["destination_region"] == "ANY")
#         ) &
#         (rules["transfer_type"] == transfer_type)
#     ]

#     # Handle Azure network path.
#     if provider_id == "AZURE":
#         if "network_path" not in rules.columns:
#             raise ValueError(
#                 "pricing_rules.csv must contain a 'network_path' column "
#                 "for Azure pricing."
#             )

#         matching_rules = matching_rules[
#             matching_rules["network_path"] == network_path
#         ]

#     if matching_rules.empty:
#         return {
#             "available": False,
#             "cost": None,
#             "reason": "No pricing rule found"
#         }

#     if matching_rules["price_per_unit"].notna().sum() == 0:
#         return {
#             "available": False,
#             "cost": None,
#             "reason": "Pricing exists but price is unavailable"
#         }

#     billing_unit = matching_rules.iloc[0]["billing_unit"]

#     volume_for_pricing = convert_volume(
#         volume_gb,
#         "GB",
#         billing_unit
#     )

#     cost = calculate_tiered_cost(
#         volume_for_pricing,
#         matching_rules
#     )

#     return {
#         "available": True,
#         "cost": round(cost, 4),
#         "currency": matching_rules.iloc[0]["currency"],
#         "billing_unit": billing_unit,
#         "network_path": network_path
#     }
import pandas as pd


PRICING_FILE = "data/pricing_rules.csv"

# Temporary default Azure path.
# Later this can be replaced with proper network-path selection.
DEFAULT_AZURE_NETWORK_PATH = "PREMIUM_GLOBAL_NETWORK"


def load_pricing_rules():
    return pd.read_csv(PRICING_FILE)


def convert_volume(volume, from_unit, to_unit):
    if from_unit == to_unit:
        return volume

    if from_unit == "GB" and to_unit == "GiB":
        return volume * (1_000_000_000 / 1_073_741_824)

    if from_unit == "GiB" and to_unit == "GB":
        return volume * (1_073_741_824 / 1_000_000_000)

    raise ValueError(f"Unsupported conversion: {from_unit} -> {to_unit}")


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
    volume_gb,
    network_path=None
):
    """
    Calculate data transfer cost.

    Azure currently uses Premium Global Network by default.
    Transit ISP will be handled later by the optimizer.
    """

    rules = load_pricing_rules()

    # Default Azure path for now.
    if provider_id == "AZURE" and network_path is None:
        network_path = DEFAULT_AZURE_NETWORK_PATH

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

    # Temporary Azure path selection using existing rule IDs.
    if provider_id == "AZURE":
        if network_path == "PREMIUM_GLOBAL_NETWORK":
            matching_rules = matching_rules[
                matching_rules["rule_id"].str.contains("_PGN_")
            ]

        elif network_path == "TRANSIT_ISP":
            matching_rules = matching_rules[
                matching_rules["rule_id"].str.contains("_ISP_")
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

    billing_unit = matching_rules.iloc[0]["billing_unit"]

    volume_for_pricing = convert_volume(
        volume_gb,
        "GB",
        billing_unit
    )

    cost = calculate_tiered_cost(
        volume_for_pricing,
        matching_rules
    )

    return {
        "available": True,
        "cost": round(cost, 4),
        "currency": matching_rules.iloc[0]["currency"],
        "billing_unit": billing_unit,
        "network_path": network_path
    }