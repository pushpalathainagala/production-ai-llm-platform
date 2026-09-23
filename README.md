# AI/LLM Platform & DevOps Architecture

[![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://python.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://docker.com)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D?logo=redis&logoColor=white)](https://redis.io)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)](https://postgresql.org)
[![Prometheus](https://img.shields.io/badge/Prometheus-Monitoring-E6522C?logo=prometheus&logoColor=white)](https://prometheus.io)

A production-grade, highly resilient **AI Question-Answering & LLM Platform** engineered with **FastAPI**, **PostgreSQL**, **Redis**, **Docker**, and **Prometheus**. This project is built following cloud-native DevOps best practices: stateless application tiers, multi-layered caching with graceful degradation, automated LLM fallback & retry logic, structured token/latency observability, and enterprise-ready scaling blueprints.

---

## Table of Contents
1. [Core Architecture & System Flow](#1-core-architecture--system-flow)
2. [Technology Stack](#2-technology-stack)
3. [API Endpoints & Implementation](#3-api-endpoints--implementation)
4. [Enterprise Authentication & RBAC](#4-enterprise-authentication--rbac)
5. [Resilience: Fallback, Retries & Caching](#5-resilience-fallback-retries--caching)
6. [Containerization & Local Setup](#6-containerization--local-setup)
7. [Observability & Monitoring](#7-observability--monitoring)
8. [Automated Testing](#8-automated-testing)
9. [High-Throughput Scaling (100–500 RPS)](#9-high-throughput-scaling-100500-rps)
10. [Production Migration Guide (10 to 10,000 Users)](#10-production-migration-guide-10-to-10000-users)
11. [Summary of My Work & Implementation Highlights](#11-summary-of-my-work--implementation-highlights)

---

## 1. Core Architecture & System Flow

The platform separates transient API traffic, caching, database persistence, and asynchronous LLM orchestration:

```text
                                 [ Users / Clients ]
                                          │
                                          ▼
                               ┌─────────────────────┐
                               │  Load Balancer/ALB  │
                               └──────────┬──────────┘
                                          │
                    ┌─────────────────────┴─────────────────────┐
                    ▼                                           ▼
         ┌─────────────────────┐                     ┌─────────────────────┐
         │  FastAPI Replica 1  │                     │  FastAPI Replica N  │
         │  - JWT Auth & RBAC  │                     │  - JWT Auth & RBAC  │
         │  - Token Counter    │                     │  - Token Counter    │
         │  - Latency Tracker  │                     │  - Latency Tracker  │
         └──────────┬──────────┘                     └──────────┬──────────┘
                    │                                           │
         ┌──────────┴─────────────────┬─────────────────────────┴─────────┐
         ▼                            ▼                                   ▼
┌──────────────────┐        ┌──────────────────┐                ┌──────────────────┐
│    PostgreSQL    │        │  Redis Sentinel  │                │   LLM Gateway    │
│  - User data     │        │  - Cache Layer   │                │  - Timeout (30s) │
│  - Passwords     │        │  - 300s TTL      │                │  - Retries (x2)  │
│  - Role schemas  │        │  - Graceful Miss │                │  - Fallback Model│
└──────────────────┘        └──────────────────┘                └────────┬─────────┘
                                                                         │
                                                                         ▼
                                                               ┌───────────────────┐
                                                               │ Google Gemini API │
                                                               │ (Primary/Fallback)│
                                                               └───────────────────┘

[ Monitoring Pipeline ]
   FastAPI (/metrics) ──▶ Prometheus Scraper ──▶ Grafana Dashboards
```

---

## 2. Technology Stack

| Layer | Component | Selection Rationale |
|---|---|---|
| **API Framework** | FastAPI (Python 3.12) | High-concurrency async ASGI performance, automatic OpenAPI generation, type safety with Pydantic v2. |
| **Authentication** | Python-Jose & Passlib | Standards-compliant JWT authentication with BCrypt password hashing and role claim enforcement. |
| **Persistence** | PostgreSQL 16 | ACID-compliant relational storage for identity and user metadata with connection pre-pinging. |
| **Caching Layer** | Redis 7 | In-memory key-value caching with 5-minute TTL and automated fallback on connectivity degradation. |
| **AI/LLM Gateway** | Google Gemini (`gemini-2.5-flash` / `1.5-flash`) | Fast inference, built-in usage metadata for token accounting, and multi-tier model fallback. |
| **Observability** | Prometheus Client | Exposes real-time request counts, latency histograms, and total LLM token usage counters. |
| **Containerization** | Docker & Docker Compose | Multi-stage, reproducible microservice runtime isolated via internal network bridges. |

---

## 3. API Endpoints & Implementation

### 1. `POST /auth/login`
Authenticates a registered user and issues a signed JWT access token.
- **Request Body:**
  ```json
  {
    "username": "alice",
    "password": "secretpassword"
  }
  ```
- **Response (200 OK):**
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsIn...",
    "token_type": "bearer"
  }
  ```

### 2. `POST /chat`
Protected endpoint requiring `Authorization: Bearer <token>`.
- Evaluates Redis cache using normalized query key `chat:<query>`.
- If cache hit: returns cached answer immediately (`cached: true`, `tokens_used: 0`).
- If cache miss: queries the primary LLM model (`gemini-2.5-flash`) with retries, falling back to secondary model if unavailable.
- Records token consumption and tracks request latency.
- **Request Body:**
  ```json
  {
    "question": "What is container orchestration?"
  }
  ```
- **Response (200 OK):**
  ```json
  {
    "username": "alice",
    "role": "user",
    "question": "What is container orchestration?",
    "answer": "Container orchestration automates the deployment, management, scaling, and networking of containers...",
    "cached": false,
    "tokens_used": 78,
    "model": "gemini-2.5-flash"
  }
  ```

### 3. `GET /health`
Deep health inspection endpoint returning service health and downstream dependencies:
```json
{
  "status": "healthy",
  "database": "connected",
  "redis": "connected",
  "service": "ai-llm-platform"
}
```
*(If Redis or PostgreSQL is temporarily unreachable, returns `"status": "degraded"` while continuing to serve non-dependent traffic).*

### 4. `GET /metrics`
Exposes Prometheus-formatted metrics:
- `api_request_count`: Total API requests partitioned by `method`, `endpoint`, and `status`.
- `api_request_latency_seconds`: Request latency histogram.
- `llm_token_usage_total`: Total tokens consumed across all LLM inference operations.

### 5. `GET /admin/system-status`
Demonstrates **Role-Based Access Control (RBAC)**:
- Returns `200 OK` only for users with `"role": "admin"`.
- Returns `403 Forbidden` for standard users or invalid roles.

---

## 4. Enterprise Authentication & RBAC

### SSO / OAuth2 / OIDC Production Architecture

In enterprise deployments, local credentials should be replaced with an OpenID Connect (OIDC) identity federation flow:

```text
[ Client / Browser ] ──1. Redirect to Login──▶ [ Identity Provider (Okta/Keycloak/Auth0) ]
       ▲                                                              │
       │                                                              │ 2. Authenticates &
       │                                                              │    issues ID/Access Token
       │                                                              ▼
       └───────────────── 3. Receives JWT Bearer Token ───────────────┘
                                       │
                                       │ 4. Request with Bearer Token
                                       ▼
                             ┌───────────────────┐
                             │    API Gateway    │ (e.g. Kong / Envoy / AWS API GW)
                             │  - Validates JWKS │
                             │  - Rate limits    │
                             └─────────┬─────────┘
                                       │ 5. Validated Claims passed downstream
                                       ▼
                             ┌───────────────────┐
                             │  FastAPI Backend  │
                             │  - Enforces RBAC  │
                             └───────────────────┘
```

1. **Authentication Delegation**: Clients authenticate directly against an OIDC Identity Provider (IdP) such as Okta, Azure AD, or Keycloak via Authorization Code Flow + PKCE.
2. **Token Minting**: The IdP issues a cryptographically signed JWT containing identity claims, expiry, and group/role memberships.
3. **Gateway Verification**: The API Gateway validates token integrity via the IdP's JWKS (JSON Web Key Set) endpoint without placing crypto load on backend pods.
4. **Context Injection**: Verified claims (`sub`, `roles`, `tenant_id`) are injected into downstream headers for application consumption.

### Role-Based Access Control (RBAC) Matrix

| Role | Access Permissions | Endpoints Allowed |
|---|---|---|
| **Admin** | Full system administration, metric inspection, configuration updates, and tenant management. | `POST /chat`, `GET /metrics`, `GET /health`, `GET /admin/*` |
| **User** | Interactive AI inference, personal chat queries, and account profile view. | `POST /chat`, `GET /health` |
| **Read-Only / Auditor** | Read-only inspection of system telemetry, audit logs, and reports without query generation. | `GET /health`, `GET /metrics` |

In our codebase, RBAC is enforced via FastAPI dependency injection:
```python
def require_roles(allowed_roles: list[str]):
    def role_checker(current_user: dict = Depends(get_current_user)):
        if current_user.get("role") not in allowed_roles:
            raise HTTPException(status_code=403, detail="Forbidden")
        return current_user
    return role_checker
```

---

## 5. Resilience: Fallback, Retries & Caching

### 1. Resilient LLM Gateway
- **Configurable Timeout**: All LLM requests enforce an explicit timeout via `LLM_TIMEOUT` (default: 30 seconds). Slow requests abort early, triggering HTTP 504.
- **Exponential Backoff Retries**: Upstream transient network drops or provider HTTP 429/503 errors trigger automatic retries (`time.sleep(1.0 ** attempt)`).
- **Secondary Model Fallback**: If the primary model (`gemini-2.5-flash`) fails across retries, the gateway falls back seamlessly to `gemini-1.5-flash` before raising an error.
- **Appropriate HTTP Status Codes**:
  - `504 Gateway Timeout`: Upstream provider exceeded deadline.
  - `502 Bad Gateway`: LLM provider outage or empty response.
  - `401 Unauthorized`: Missing or expired JWT.
  - `403 Forbidden`: Insufficient role privileges.

### 2. Redis Graceful Degradation
If Redis crashes or becomes unreachable:
- The system catches connection errors silently.
- `/chat` logs a warning and proceeds straight to the LLM.
- The request completes successfully (`cached: false`), preventing a total platform outage.

---

## 6. Containerization & Local Setup

### Prerequisites
- Docker Engine 24+ & Docker Compose v2+
- Git

### Quick Start with Docker Compose

1. **Clone the repository**:
   ```bash
   git clone https://github.com/pushpalathainagala/production-ai-llm-platform.git
   cd production-ai-llm-platform
   ```

2. **Configure environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env and supply your GEMINI LLM_API_KEY
   ```

3. **Build and launch services**:
   ```bash
   docker compose up -d --build
   ```

4. **Verify container health**:
   ```bash
   docker compose ps
   ```

5. **Access Application & Tools**:
   - **FastAPI Interactive Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
   - **Service Health Check**: [http://localhost:8000/health](http://localhost:8000/health)
   - **Application Metrics**: [http://localhost:8000/metrics](http://localhost:8000/metrics)
   - **Prometheus Dashboard**: [http://localhost:9090](http://localhost:9090)

6. **Shutdown**:
   ```bash
   docker compose down -v
   ```

---

## 7. Observability & Monitoring

The platform provides Prometheus metrics scraped every 15 seconds:

```text
# HELP api_request_count Total number of API requests
# TYPE api_request_count counter
api_request_count{endpoint="/chat",method="POST",status="200"} 42.0

# HELP api_request_latency_seconds API request latency in seconds
# TYPE api_request_latency_seconds histogram
api_request_latency_seconds_bucket{endpoint="/chat",le="0.5"} 12.0
api_request_latency_seconds_bucket{endpoint="/chat",le="2.0"} 38.0

# HELP llm_token_usage_total Total LLM token usage
# TYPE llm_token_usage_total counter
llm_token_usage_total 3150.0
```

---

## 8. Automated Testing

The automated test suite verifies authentication security, RBAC enforcement, health checks, and token accounting:

```bash
# Run pytest locally
pytest -v
```

**Test Coverage Highlights**:
- `test_health`: Validates health report and dependency status.
- `test_metrics`: Validates Prometheus metric exposition.
- `test_chat_without_authentication`: Asserts `401 Unauthorized`.
- `test_chat_with_invalid_token`: Asserts rejection of tampered tokens.
- `test_create_access_token`: Validates JWT token generation and role encoding.
- `test_chat_with_valid_token`: Confirms payload schema, token accounting, and model output.
- `test_rbac_admin_endpoint`: Confirms `403 Forbidden` for standard users and `200 OK` for administrators.

---

## 9. High-Throughput Scaling (100–500 RPS)

### Traffic Scenario
- **Baseline**: 100 requests/second.
- **Peak Burst**: Up to 500 requests/second.

### Architectural Strategy

```text
                                 [ 500 RPS Ingress ]
                                          │
                                          ▼
                               ┌─────────────────────┐
                               │ AWS ALB / NGINX Plus│
                               │ - SSL Termination   │
                               │ - Least Conn / Round│
                               └──────────┬──────────┘
                                          │
                                          ▼
                       ┌─────────────────────────────────────┐
                       │  Kubernetes Cluster (EKS / GKE)     │
                       │                                     │
                       │   ┌─────────────────────────────┐   │
                       │   │ Horizontal Pod Autoscaler   │   │
                       │   │ Target: 70% CPU / Custom RPS│   │
                       │   └──────────────┬──────────────┘   │
                       │                  │                  │
                       │  ┌───────────────┴───────────────┐  │
                       │  ▼               ▼               ▼  │
                       │ [Pod 1]        [Pod 2]        [Pod 15]
                       └──────────────────┬──────────────────┘
                                          │
                    ┌─────────────────────┴─────────────────────┐
                    ▼                                           ▼
         ┌─────────────────────┐                     ┌─────────────────────┐
         │ Redis Cluster / ElastiCache               │ RabbitMQ / SQS / Redis Stream
         │ - Cache hits bypass LLM (40-60%)          │ - Buffers async batch queries
         │ - Sliding-window rate limiter             │ - Prevents LLM concurrency blast
         └─────────────────────┘                     └──────────┬──────────┘
                                                                │
                                                                ▼
                                                     ┌─────────────────────┐
                                                     │ Background Workers  │
                                                     │ (Celery / ARQ)      │
                                                     └──────────┬──────────┘
                                                                │
                                                                ▼
                                                     ┌─────────────────────┐
                                                     │ LLM Gateway & Pool  │
                                                     │ - Max Concurrency=50│
                                                     │ - Token Bucket RPM  │
                                                     └─────────────────────┘
```

1. **Horizontal Pod Autoscaling (HPA)**:
   - FastAPI pods scale dynamically from 3 replicas (100 RPS) to 15–20 replicas (500 RPS) using Kubernetes HPA driven by CPU utilization (>70%) and Prometheus custom metrics (RPS per pod).
2. **Distributed Redis Caching**:
   - At 500 RPS, duplicate or popular queries are served in sub-5ms from Redis, deflecting an estimated 40–60% of requests away from the LLM provider.
3. **Distributed Rate Limiting**:
   - Enforce user-tier rate limiting using Redis Sliding Window / Token Bucket algorithms to protect against noisy-neighbor attacks.
4. **LLM Provider Concurrency & Rate Limit Management**:
   - LLMs have strict Requests-Per-Minute (RPM) and Tokens-Per-Minute (TPM) caps.
   - We introduce an **asynchronous queue decoupling pattern**: long-running or batch questions are pushed to an SQS/Redis queue and processed by worker pools constrained by an upstream concurrency semaphore (e.g. 50 simultaneous LLM connections).
5. **Circuit Breakers & Graceful Degradation**:
   - When the LLM provider latency spikes above threshold or throws 429s, circuit breakers (e.g., PyBreaker / Envoy circuit breaking) trip, immediately routing traffic to cached responses, secondary models, or fallback answers rather than exhausting worker threads.

---

## 10. Production Migration Guide (10 to 10,000 Users)

### Current vs. Target Production State

| Dimension | Legacy Single-EC2 Architecture (10 Users) | Modern Production Architecture (10,000 Users) |
|---|---|---|
| **Compute** | Single EC2 instance running API & DB | Amazon EKS / ECS multi-AZ container cluster with auto-scaling |
| **Database** | Local SQLite / monolithic PostgreSQL on same disk | AWS Aurora PostgreSQL Multi-AZ with Read Replicas & RDS Proxy |
| **Cache** | Local in-process dictionary or standalone Redis | Multi-AZ Amazon ElastiCache for Redis Cluster with Sentinel |
| **LLM Gateway** | Direct synchronous unmonitored SDK calls | Queued, circuit-broken gateway with retries, fallback & token metrics |
| **Secrets** | Plaintext `.env` on disk | AWS Secrets Manager / Vault injected via Kubernetes CSI |
| **Deployment** | Manual SSH / git pull (downtime on restart) | Zero-downtime Blue/Green or Canary via ArgoCD / AWS ALB |

### 5-Phase Zero-Downtime Migration Plan

```text
Phase 1: Foundation      Phase 2: DB Replication    Phase 3: Dual Write     Phase 4: Canary Cutover   Phase 5: Decommission
┌─────────────────┐      ┌────────────────────┐    ┌──────────────────┐    ┌───────────────────┐    ┌─────────────────────┐
│ Provision EKS,  │ ───▶ │ Snapshot & Replicate│───▶│ Route 5% traffic │───▶│ Scale traffic to  │───▶│ Retire legacy EC2   │
│ ElastiCache &   │      │ EC2 DB to Aurora   │    │ to EKS via ALB   │    │ 100% on EKS;      │    │ server safely       │
│ Aurora Postgres │      │ with CDC sync      │    │ Validate latency │    │ verify all metrics│    │                     │
└─────────────────┘      └────────────────────┘    └──────────────────┘    └───────────────────┘    └─────────────────────┘
```

#### 1. Compute & Scalability
Migrate from single EC2 to managed Kubernetes (EKS) or AWS ECS. Containerized FastAPI pods run behind an Application Load Balancer (ALB) across at least 3 Availability Zones. Auto-scaling policies adjust pod count and node groups in response to real-time traffic.

#### 2. Database Migration with Zero Data Loss
1. Provision **AWS Aurora PostgreSQL** Multi-AZ with read replicas.
2. Establish continuous replication from the EC2 database using **AWS Database Migration Service (DMS)** with Change Data Capture (CDC).
3. Introduce **RDS Proxy / PgBouncer** for high-performance connection pooling, ensuring 10,000 concurrent users do not exhaust database connection limits.

#### 3. Handling LLM Provider Limits (RPM / TPM)
- Implement a tiered token-bucket rate limiter in Redis.
- Maintain multi-region / multi-account API keys with round-robin dispatch.
- Enable automatic failover from `gemini-2.5-flash` to secondary LLM endpoints or cache-only modes when quotas are reached.

#### 4. Asynchronous Queue Architecture
- Separate synchronous interactive chats from heavier analytical tasks.
- Heavy requests return a `202 Accepted` with a job ID, routing the execution through **Celery / Redis Streams** workers. Clients poll or listen via WebSockets/SSE.

#### 5. Secrets Management
- Remove all `.env` files from compute nodes.
- Synchronize credentials from **AWS Secrets Manager** or **HashiCorp Vault** using the Kubernetes External Secrets Operator (ESO), injecting them securely into pod memory as environment variables.

#### 6. Zero-Downtime Cutover Strategy
- Use **Weighted DNS (Route 53)** or **ALB Canary Routing**:
  - Direct 95% of traffic to legacy EC2, 5% to the new Kubernetes cluster.
  - Monitor error rates, response latencies, and database locks in Prometheus/Grafana.
  - Incrementally ramp to 25%, 50%, and 100% over several hours.
  - Decommission the legacy EC2 instance once traffic is cleanly transitioned.

---

## 11. Summary of My Work & Implementation Highlights

Throughout this project, I worked on and implemented several critical architectural enhancements to ensure this AI Question-Answering platform meets real-world production standards:

### 1. Resilient LLM Gateway & Fallback Engineering
- **What I worked on**: I developed a resilient LLM integration layer for Google Gemini that protects the API against external provider downtime and latency spikes.
- **What I implemented**:
  - Implemented configurable request timeouts (`LLM_TIMEOUT`) so stalled upstream queries do not block client connections.
  - Implemented exponential backoff retries to absorb transient network blips and rate limits.
  - Implemented an automated **secondary model fallback system**: if the primary model (`gemini-2.5-flash`) fails across retry attempts, the gateway automatically falls back to `gemini-1.5-flash`.
  - Implemented structured HTTP exception handling, returning `504 Gateway Timeout` or `502 Bad Gateway` with clear error details instead of generic 500 crashes.

### 2. Live Token Tracking & Prometheus Observability
- **What I worked on**: I integrated observability directly into the inference lifecycle rather than treating it as an afterthought.
- **What I implemented**:
  - Implemented an `llm_token_usage_total` counter in Prometheus that extracts token usage metadata directly from LLM responses and tracks consumption over time.
  - Added latency observation histograms (`api_request_latency_seconds`) and total request counters (`api_request_count`) partitioned by HTTP method, endpoint, and status code.
  - Added Prometheus container orchestration into `docker-compose.yml` mapped to scrape configuration.

### 3. High-Performance Caching with Graceful Degradation
- **What I worked on**: I built an intelligent Redis caching layer to eliminate redundant LLM calls and reduce response latency.
- **What I implemented**:
  - Implemented normalized query hashing (`chat:<question>`) with a 5-minute TTL to serve frequent queries in sub-5ms.
  - Implemented **graceful degradation**: if Redis is unreachable or crashes, the application catches connection errors, logs an alert, bypasses the cache, and serves the response directly from the LLM without failing the user request.

### 4. Enterprise Authentication & Role-Based Access Control (RBAC)
- **What I worked on**: I secured the API with JWT tokens and enforced granular role separation.
- **What I implemented**:
  - Implemented JWT token generation with expiration and role claims, secured by BCrypt password hashing.
  - Implemented reusable FastAPI dependency injection guards (`require_roles`) to enforce RBAC.
  - Added the `GET /admin/system-status` endpoint to demonstrate strict permission gating between Admin and User roles (returning `403 Forbidden` for non-admin accounts).

### 5. Deep Health Check & Fault-Tolerant Local Setup
- **What I worked on**: I improved operational reliability for orchestrated environments (Kubernetes/Docker).
- **What I implemented**:
  - Upgraded `GET /health` into a deep health inspection endpoint that verifies active connections to PostgreSQL and Redis.
  - Built an automatic database fallback mechanism: when running locally without a live PostgreSQL instance, the engine gracefully defaults to SQLite (`sqlite:///./ai_platform.db`) for immediate offline developer testing.

### 6. Cloud-Native Scalability & Production Migration Design
- **What I worked on**: I authored the system design and operational strategy for scaling the platform.
- **What I implemented**:
  - Designed the **100–500 RPS scaling blueprint**, detailing horizontal pod autoscaling (HPA), token-bucket rate limiting, and asynchronous queue decoupling (Celery/SQS).
  - Formulated the comprehensive **5-phase migration strategy** to transition a single EC2 server with 10 users to an AWS EKS and Aurora PostgreSQL Multi-AZ architecture serving 10,000 users with zero downtime.

---

## 12. License & Author
- **Author**: Pushpalatha Inagala
- **Repository**: [production-ai-llm-platform](https://github.com/pushpalathainagala/production-ai-llm-platform)
- **License**: MIT