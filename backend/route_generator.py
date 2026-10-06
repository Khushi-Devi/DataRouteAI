import pandas as pd


NETWORK_FILE = "data/network_metrics.csv"


# Available regions in the current prototype.
REGIONS = [
    {"provider_id": "AWS", "region_id": "AWS_MUM"},
    {"provider_id": "AWS", "region_id": "AWS_HYD"},
    {"provider_id": "AWS", "region_id": "AWS_SIN"},

    {"provider_id": "GCP", "region_id": "GCP_MUM"},
    {"provider_id": "GCP", "region_id": "GCP_DEL"},
    {"provider_id": "GCP", "region_id": "GCP_SIN"},

    {"provider_id": "AZURE", "region_id": "AZURE_CIN"},
    {"provider_id": "AZURE", "region_id": "AZURE_SIN"},
    {"provider_id": "AZURE", "region_id": "AZURE_SEA"},
]


def load_network_metrics():
    return pd.read_csv(NETWORK_FILE)


def network_path_exists(source_region, destination_region):
    """
    Check whether network metrics exist for a hop.
    """

    if source_region == destination_region:
        return True

    df = load_network_metrics()

    match = df[
        (df["source_region"] == source_region)
        & (df["destination_region"] == destination_region)
    ]

    return not match.empty


def get_region_info(region_id):
    """
    Return provider information for a region.
    """

    for region in REGIONS:
        if region["region_id"] == region_id:
            return region

    return None


def generate_routes(
    source_region,
    destination_region,
    predicted_traffic=None,
    anomaly_score=None,
):
    """
    Generate candidate routes between source and destination.

    V1:
    - Always includes the direct route if available.
    - Generates one-hop proxy routes.
    - LSTM and Isolation Forest values are accepted but not
      actively used yet.

    Later:
    - predicted_traffic will come from LSTM.
    - anomaly_score will come from Isolation Forest.
    - These values can influence how aggressively proxy
      routes are generated.
    """

    source_info = get_region_info(source_region)
    destination_info = get_region_info(destination_region)

    if source_info is None:
        raise ValueError(f"Unknown source region: {source_region}")

    if destination_info is None:
        raise ValueError(
            f"Unknown destination region: {destination_region}"
        )

    routes = []

    # ---------------------------------------------------------
    # 1. DIRECT ROUTE
    # ---------------------------------------------------------

    if network_path_exists(source_region, destination_region):

        routes.append({
            "route_id": f"ROUTE_001",
            "type": "direct",
            "hops": [
                source_region,
                destination_region
            ]
        })

        # ---------------------------------------------------------
        # 2. ONE-HOP PROXY ROUTES
        # ---------------------------------------------------------
        route_number = len(routes) + 1

        for region in REGIONS:

            proxy_region = region["region_id"]

            # Do not use source or destination as proxy.
            if proxy_region in {
                source_region,
                destination_region
            }:
                continue

            first_hop_exists = network_path_exists(
                source_region,
                proxy_region
            )

            second_hop_exists = network_path_exists(
                proxy_region,
                destination_region
            )

            # Both hops must exist.
            if not first_hop_exists or not second_hop_exists:
                continue

            routes.append({
                "route_id": f"ROUTE_{route_number:03d}",
                "type": "one_hop_proxy",
                "hops": [
                    source_region,
                    proxy_region,
                    destination_region
                ]
            })

            route_number += 1

    return routes