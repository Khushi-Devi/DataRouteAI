# DataRoute AI

### Multi-Cloud Egress Cost Minimizer & Dynamic Proxy Router

DataRoute AI is a multi-cloud routing optimization system designed to evaluate
and select efficient routes between cloud regions based on **data-transfer
cost, network latency, reliability, and predicted traffic demand**.

The project focuses on AWS, Microsoft Azure, and Google Cloud Platform and
uses publicly available pricing/network information wherever possible,
combined with clearly identified synthetic data for prototype experimentation.

---

## Problem

Organizations increasingly use multiple cloud providers for flexibility,
availability, performance, and workload requirements. However, transferring
large amounts of data between cloud environments can introduce significant
egress costs and performance overhead.

A routing decision based only on the shortest network path may therefore not
be the most cost-efficient or reliable choice.

DataRoute AI addresses this problem by comparing possible cloud routes using
multiple factors instead of considering network distance alone.

---

## Objective

The primary objective of DataRoute AI is to:

- Calculate estimated data-transfer costs between cloud regions.
- Compare direct and intermediary routes.
- Evaluate latency and network reliability.
- Forecast future traffic using an LSTM-based model.
- Incorporate predicted traffic into routing decisions.
- Identify inefficient routing conditions.
- Select a route according to user-defined cost, latency, and reliability
  preferences.
- Provide an explainable comparison of available routes.

---

## Supported Cloud Providers

| Provider | Example Regions |
|---|---|
| AWS | Mumbai, Hyderabad, Singapore |
| Microsoft Azure | Central India, South India, Southeast Asia |
| Google Cloud | Mumbai, Delhi, Singapore |

---

## System Architecture

```text
User
  │
  ▼
Frontend
HTML / CSS / JavaScript
  │
  ▼
FastAPI Backend
  │
  ├── Pricing Engine
  │
  ├── Network Metrics
  │
  ├── Route Generator
  │
  ├── Traffic Prediction
  │       │
  │       └── LSTM
  │
  ├── Route Optimizer
  │
  └── Anomaly Detection
  │
  ▼
PostgreSQL