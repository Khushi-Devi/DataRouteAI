import pandas as pd

from backend.cost_engine import calculate_cost


NETWORK_FILE = "data/network_metrics.csv"


def load_network_metrics():
    return pd.read_csv(NETWORK_FILE)


def get_network_metrics(source_region, destination_region):
    # Same-region transfer
    if source_region == destination_region:
        return {
            "available": True,
            "latency_ms": 0.0,
            "packet_loss_pct": 0.0,
            "reliability": 1.0
        }

    df = load_network_metrics()

    match = df[
        (df["source_region"] == source_region)
        & (df["destination_region"] == destination_region)
    ]

    if match.empty:
        return {
            "available": False,
            "reason": "Network metrics not found"
        }

    row = match.iloc[0]

    return {
        "available": True,
        "latency_ms": float(row["latency_ms"]),
        "packet_loss_pct": float(row["packet_loss_pct"]),
        "reliability": float(row["reliability"])
    }


def calculate_route_cost(
    provider_id,
    source_region,
    destination_region,
    transfer_type,
    volume_gb
):
    cost = calculate_cost(
        provider_id,
        source_region,
        destination_region,
        transfer_type,
        volume_gb
    )

    network = get_network_metrics(
        source_region,
        destination_region
    )

    return {
        "source_region": source_region,
        "destination_region": destination_region,
        "volume_gb": volume_gb,
        "cost": cost,
        "network": network
    }