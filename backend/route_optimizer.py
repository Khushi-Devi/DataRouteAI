def normalize(value, min_value, max_value):
    """
    Normalize a value between 0 and 1.

    0 = best
    1 = worst
    """

    if max_value == min_value:
        return 0.0

    return (value - min_value) / (max_value - min_value)


def optimize_routes(route_results, weights):
    """
    Select the best route using user-defined weights.

    weights:
        cost       -> importance of low cost
        latency    -> importance of low latency
        reliability -> importance of high reliability

    Example:
        {
            "cost": 0.2,
            "latency": 0.6,
            "reliability": 0.2
        }
    """

    # ---------------------------------------------------------
    # 1. Keep only routes that can actually be evaluated
    # ---------------------------------------------------------

    available_routes = [
        route
        for route in route_results
        if route.get("available") is True
    ]

    if not available_routes:
        return {
            "available": False,
            "reason": "No available routes to optimize"
        }

    # ---------------------------------------------------------
    # 2. Validate weights
    # ---------------------------------------------------------

    required_weights = {
        "cost",
        "latency",
        "reliability"
    }

    if set(weights.keys()) != required_weights:
        return {
            "available": False,
            "reason": (
                "Weights must contain exactly: "
                "cost, latency, reliability"
            )
        }

    total_weight = sum(weights.values())

    if total_weight <= 0:
        return {
            "available": False,
            "reason": "Sum of weights must be greater than zero"
        }

    # Normalize weights so they sum to 1.
    normalized_weights = {
        key: value / total_weight
        for key, value in weights.items()
    }

    # ---------------------------------------------------------
    # 3. Find metric ranges
    # ---------------------------------------------------------

    costs = [
        route["total_cost"]
        for route in available_routes
    ]

    latencies = [
        route["total_latency_ms"]
        for route in available_routes
    ]

    reliabilities = [
        route["total_reliability"]
        for route in available_routes
    ]

    min_cost = min(costs)
    max_cost = max(costs)

    min_latency = min(latencies)
    max_latency = max(latencies)

    min_reliability = min(reliabilities)
    max_reliability = max(reliabilities)

    # ---------------------------------------------------------
    # 4. Calculate normalized metrics + weighted score
    # ---------------------------------------------------------

    scored_routes = []

    for route in available_routes:

        # Cost:
        # lower is better
        cost_score = normalize(
            route["total_cost"],
            min_cost,
            max_cost
        )

        # Latency:
        # lower is better
        latency_score = normalize(
            route["total_latency_ms"],
            min_latency,
            max_latency
        )

        # Reliability:
        # higher is better
        reliability_score = normalize(
            route["total_reliability"],
            min_reliability,
            max_reliability
        )

        reliability_score = 1 - reliability_score

        # -----------------------------------------------------
        # Weighted multi-objective score
        # Lower score = better route
        # -----------------------------------------------------

        final_score = (
            normalized_weights["cost"] * cost_score
            + normalized_weights["latency"] * latency_score
            + normalized_weights["reliability"] * reliability_score
        )

        scored_routes.append({
            "route_id": route["route_id"],
            "route_type": route["route_type"],
            "route": route["route"],

            "total_cost": route["total_cost"],
            "total_latency_ms": route["total_latency_ms"],
            "total_packet_loss_pct": route["total_packet_loss_pct"],
            "total_reliability": route["total_reliability"],

            "normalized_cost": round(cost_score, 6),
            "normalized_latency": round(latency_score, 6),
            "normalized_reliability": round(
                reliability_score,
                6
            ),

            "score": round(final_score, 6)
        })

    # ---------------------------------------------------------
    # 5. Sort by final score
    # ---------------------------------------------------------

    scored_routes.sort(
        key=lambda route: route["score"]
    )

    best_route = scored_routes[0]

    # ---------------------------------------------------------
    # 6. Explanation
    # ---------------------------------------------------------

    explanation = (
        f"{best_route['route_id']} selected because it achieved "
        f"the lowest weighted score of "
        f"{best_route['score']:.6f} based on the user's priorities."
    )

    return {
        "available": True,

        "weights": normalized_weights,

        "best_route": best_route,

        "ranked_routes": scored_routes,

        "explanation": explanation
    }