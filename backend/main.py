from fastapi import FastAPI
from pydantic import BaseModel

from backend.route_generator import generate_routes
from backend.route_evaluator import evaluate_routes
from backend.route_optimizer import optimize_routes
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(
    title="DataRoute AI",
    description="Multi-Cloud Egress Cost Minimizer & Dynamic Proxy Router",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class RouteRequest(BaseModel):
    source_region: str
    destination_region: str
    volume_gb: float
    weights: dict


@app.get("/")
def root():
    return {
        "message": "DataRoute AI API is running"
    }


@app.post("/optimize-route")
def optimize_route(request: RouteRequest):

    # 1. Generate candidate routes
    routes = generate_routes(
        request.source_region,
        request.destination_region
    )

    # 2. Evaluate every candidate route
    results = evaluate_routes(
        routes,
        request.volume_gb
    )

    # 3. Select best route according to user priorities
    result = optimize_routes(
        results,
        request.weights
    )

    return result