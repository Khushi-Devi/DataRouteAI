from backend.route_cost import calculate_route_cost


def get_provider(region_id):
    """
    Get provider from a region ID.

    Example:
    AWS_HYD -> AWS
    GCP_DEL -> GCP
    AZURE_CIN -> AZURE
    """

    return region_id.split("_")[0]


def get_transfer_type(source_region, destination_region):
    """
    Determine transfer type for a hop.

    Same provider:
        INTER_REGION

    Different providers:
        INTERNET_EGRESS
    """

    source_provider = get_provider(source_region)
    destination_provider = get_provider(destination_region)

    if source_provider == destination_provider:
        return "INTER_REGION_EGRESS"

    return "INTERNET_EGRESS"


def evaluate_route(route, volume_gb):
    """
    Evaluate a complete route.

    A route can be:

    Direct:
        AWS_HYD -> AWS_MUM

    One-hop:
        AWS_HYD -> GCP_DEL -> AWS_MUM
    """

    hops = route["hops"]

    hop_results = []

    total_cost = 0.0
    total_latency = 0.0

    # Start with 100% successful transmission.
    total_success_probability = 1.0

    for i in range(len(hops) - 1):

        source_region = hops[i]
        destination_region = hops[i + 1]

        transfer_type = get_transfer_type(
            source_region,
            destination_region
        )

        result = calculate_route_cost(
            provider_id=get_provider(source_region),
            source_region=source_region,
            destination_region=destination_region,
            transfer_type=transfer_type,
            volume_gb=volume_gb
        )

        # If either cost or network data is unavailable,
        # this route cannot currently be evaluated.
        if not result["cost"]["available"]:
            return {
                "available": False,
                "route_id": route["route_id"],
                "route": hops,
                "reason": (
                    f"Cost unavailable for hop: "
                    f"{source_region} -> {destination_region}"
                )
            }

        if not result["network"]["available"]:
            return {
                "available": False,
                "route_id": route["route_id"],
                "route": hops,
                "reason": (
                    f"Network metrics unavailable for hop: "
                    f"{source_region} -> {destination_region}"
                )
            }

        cost = result["cost"]["cost"]
        latency = result["network"]["latency_ms"]
        packet_loss = result["network"]["packet_loss_pct"]
        reliability = result["network"]["reliability"]

        total_cost += cost
        total_latency += latency

        # Combine reliability across hops.
        total_success_probability *= reliability

        hop_results.append({
            "hop_number": i + 1,
            "source_region": source_region,
            "destination_region": destination_region,
            "transfer_type": transfer_type,
            "cost": cost,
            "latency_ms": latency,
            "packet_loss_pct": packet_loss,
            "reliability": reliability
        })

    # Convert combined success probability back into
    # an overall packet-loss percentage.
    total_packet_loss = (
        1 - total_success_probability
    ) * 100

    return {
        "available": True,

        "route_id": route["route_id"],
        "route_type": route["type"],
        "route": hops,

        "volume_gb": volume_gb,

        "total_cost": round(total_cost, 4),
        "total_latency_ms": round(total_latency, 4),
        "total_packet_loss_pct": round(total_packet_loss, 6),
        "total_reliability": round(
            total_success_probability,
            6
        ),

        "hops": hop_results
    }


def evaluate_routes(routes, volume_gb):
    """
    Evaluate all generated candidate routes.
    """

    results = []

    for route in routes:

        result = evaluate_route(
            route,
            volume_gb
        )

        results.append(result)

    return results