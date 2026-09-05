# AI/LLM Platform — DevOps Engineer Assessment

A production-style AI Question Answering API built with **FastAPI**, **PostgreSQL**, **Redis**, **Docker**, **Prometheus**, and **Grafana**.

The application provides JWT-based authentication, an authenticated LLM-powered `/chat` endpoint, Redis response caching, database integration, monitoring, and automated tests — designed to reflect the operational concerns of a real production deployment rather than a minimal demo.

---

## 1. Overview

This project implements a stateless, horizontally scalable API service that answers user questions using an LLM provider, while caching responses, authenticating requests, and exposing metrics for observability. Every architectural decision below is made with production readiness in mind: statelessness, graceful degradation, and clear scaling paths.

---

## 2. Architecture

```text
                         ┌─────────────────────┐
                         │       Client        │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │     FastAPI API     │
                         │                     │
                         │  /auth/login        │
                         │  /chat              │
                         │  /health            │
                         │  /metrics           │
                         └──────┬──────┬───────┘
                                │      │
                  ┌─────────────┘      └──────────────┐
                  ▼                                   ▼
        ┌─────────────────┐                  ┌─────────────────┐
        │   PostgreSQL    │                 │      Redis      │
        │                 │                 │                 │
        │ User data       │                 │ Response cache  │
        │ Authentication  │                 │ TTL: 5 minutes  │
        └─────────────────┘                 └────────┬────────┘
                                                        │
                                                        ▼
                                             ┌─────────────────┐
                                             │   LLM Provider  │
                                             │                 │
                                             │   Gemini API    │
                                             └─────────────────┘

        ┌─────────────────┐           ┌─────────────────┐
        │   Prometheus     │─────────▶│     Grafana     │
        │                  │          │                  │
        │ Metrics          │          │ Dashboards       │
        └─────────────────┘            └─────────────────┘
```

---

## 3. Technology Stack

| Component               | Technology         |
| ----------------------  | ------------------ |
| Backend                 | FastAPI / Python   |
| Authentication          | JWT                |
| Database                | PostgreSQL         |
| Cache                   | Redis              |
| LLM                     | Gemini API         |
| Containerization        | Docker             |
| Orchestration design    | Kubernetes         |
| Monitoring              | Prometheus         |
| Visualization           | Grafana            |
| Testing                 | Pytest             |
| API Documentation       | OpenAPI / Swagger  |

---

## 4. Features

### Authentication

```text
POST /auth/login
```

JWT-based authentication. A successful login returns an access token required for all protected endpoints.

### Chat

```text
POST /chat
```

The endpoint:

1. Validates the JWT.
2. Checks Redis for a cached response.
3. Calls the LLM provider only when no cached response exists.
4. Stores the new response in Redis.
5. Returns the answer to the client.

### Health Check

```text
GET /health
```

Returns the current health status of the API — can be used as a basic health endpoint for readiness/liveness checks in orchestrated environments. It currently returns a simple status response and does not verify downstream dependencies (PostgreSQL, Redis, LLM provider).

### Metrics

```text
GET /metrics
```

Exposes Prometheus-compatible metrics, currently including request count and request latency.

---

## 5. Redis Caching

Redis reduces repeated LLM requests and improves response latency.

The cache key is derived from the normalized question:

```text
chat:<question>
```

Responses are cached for **5 minutes**, which:

* Reduces unnecessary LLM API calls and associated cost.
* Improves response time for repeated or common questions.

The current setup runs a single API instance and a single Redis instance. If horizontally scaled, all API instances would share this same Redis, giving them a single consistent cache rather than duplicating work per instance — this is a property of the design, not something currently exercised with multiple instances.

---

## 6. PostgreSQL

PostgreSQL stores application user data:

* User ID
* Username
* Password hash
* Role

Passwords are always stored as salted hashes — never as plain text.

---

## 7. Environment Configuration

All configuration is supplied through environment variables, keeping secrets out of source code.

```env
DATABASE_URL=...
JWT_SECRET=...
JWT_ALGORITHM=HS256
REDIS_URL=...
LLM_TIMEOUT=30
LLM_API_KEY=...
```

* `.env` is excluded from version control via `.gitignore`.
* `.env.example` is provided as a configuration template for new environments.

---

## 8. Running with Docker Compose

### Prerequisites

* Docker
* Docker Compose

### Start the application

```bash
docker compose build
docker compose up -d
```

### Check running services

```bash
docker compose ps
```

The stack includes:

* FastAPI application
* PostgreSQL
* Redis

### Stop the application

```bash
docker compose down
```

PostgreSQL data persists across restarts via a Docker volume.

---

## 9. API Documentation

Once the application is running:

http://localhost:8000/docs
```

OpenAPI specification:

http://localhost:8000/openapi.json
```

---

## 10. Testing

Automated tests are implemented with Pytest.

pytest -q

**Current result:**

 5 passed

Test coverage includes:

* Health endpoint
* Metrics endpoint
* Authentication requirement enforcement
* Invalid JWT handling
* JWT token creation

---

## 11. Monitoring

Prometheus scrapes application metrics from `/metrics`; Grafana visualizes them.

**Current dashboard panels:**

* API Request Count
* API Request Latency

Prometheus scrape configuration: `monitoring/prometheus.yml`

---

## 12. Scaling Strategy — 100 RPS Normal / 500 RPS Burst

*(Design — not implemented in the current single-instance Docker Compose setup.)*

The API's stateless design (implemented) means it is *capable* of scaling horizontally rather than depending on a single instance. The load balancer, multi-instance deployment, and autoscaling described below are the intended production path.

### Normal traffic (~100 RPS)

Multiple FastAPI instances run behind a load balancer, sharing Redis and PostgreSQL:

                  Load Balancer
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
       API-1        API-2        API-3
          │            │            │
          └────────────┼────────────┘
                       │
              ┌────────┴────────┐
              ▼                 ▼
            Redis           PostgreSQL
```

### Burst traffic (~500 RPS)

Kubernetes Horizontal Pod Autoscaler (HPA) increases API replica count in response to load:

 100 RPS
   │
   ▼
3 API replicas
   │
   │ traffic increases
   ▼
HPA
   │
   ▼
5–10 API replicas
 
Exact replica counts should be determined through load testing and real resource measurements — not assumed in advance.

---

## 13. Kubernetes HPA

*(Design — no Kubernetes manifests exist in this project yet; see Section 25, Future Improvements.)*

A production deployment would use HPA driven by CPU/memory utilization and, ideally, application-level metrics such as request rate or latency:

                     ┌───────────────┐
                    │ Load Balancer  │
                    └───────┬────────┘
                            │
                    ┌───────▼────────┐
                    │ Kubernetes      │
                    │ Service         │
                    └───────┬────────┘
                            │
                ┌───────────┼───────────┐
                ▼           ▼           ▼
              Pod 1       Pod 2       Pod 3
                │           │           │
                └───────────┼───────────┘
                            │
                           HPA
                            │
                    Scale replicas up/down

Pods remain stateless so new instances can be created or removed safely at any time.

---

## 14. LLM Rate Limits and Concurrent Requests

LLM providers impose rate and quota limits, so a production deployment should avoid sending unbounded concurrent requests directly to the provider.

Production architecture would use:

* Request rate limiting
* Concurrency limits
* Redis-based throttling
* Queue-based processing for asynchronous workloads
* Request timeouts
* Retry policies
* Provider fallback where appropriate

None of the above are implemented in the current codebase — they are documented here as the intended production design.

Redis caching, which **is** implemented, already reduces redundant identical requests that would otherwise consume LLM quota unnecessarily.

---

## 15. Queue-Based Architecture

*(Design — not implemented; the current `/chat` endpoint responds synchronously.)*

Workloads that don't require an immediate synchronous response could be routed through a message queue:

Client
  │
  ▼
API
  │
  ▼
Redis / Message Queue
  │
  ├──── Worker 1 ────▶ LLM
  ├──── Worker 2 ────▶ LLM
  └──── Worker 3 ────▶ LLM

Workers scale independently based on queue depth, preventing traffic spikes from overwhelming the LLM provider.

---

## 16. Handling Slow or Failing LLM Requests

LLM calls enforce a configurable timeout via the `LLM_TIMEOUT` environment variable — this **is** implemented. The remaining strategies below (retry, fallback, circuit breaker) are documented as the intended production design and are not yet implemented in the current codebase.

**Timeout** *(implemented)* — terminate requests exceeding the configured maximum duration.

**Retry** *(design)* — retry transient failures with exponential backoff:

```text
Attempt 1 → temporary failure → wait
Attempt 2 → temporary failure → wait longer
Attempt 3
```

Retries would be capped to avoid compounding load during provider outages.

**Fallback** *(design)* — a secondary LLM provider could be configured where business requirements permit.

**Circuit Breaker** *(design)* — repeated provider failures would temporarily halt new calls, allowing recovery without continuously generating failed requests.

---

## 17. Failure Recovery

| Failure                | Recovery strategy | Status |
| ------------------------ | ------------------ | -------- |
| API instance failure     | Application is stateless by design; Kubernetes would restart failed pods automatically. | Design (stateless app implemented; Kubernetes deployment not yet configured) |
| Redis failure             | Application should degrade gracefully rather than fail the whole request. | Design — current code calls Redis directly with no fallback path if it's unavailable |
| PostgreSQL failure        | Persistent storage, automated backups, health checks, and HA in production. | Design (Docker volume persistence implemented; backups/HA not yet configured) |
| LLM provider failure      | Timeout, limited retries, circuit breaker, optional fallback, and clear error responses. | Timeout implemented; retries/circuit breaker/fallback are design only |

---

## 18. Production Architecture for 10,000 Users

```text
                         Internet
                            │
                            ▼
                    ┌───────────────┐
                    │ Load Balancer  │
                    └───────┬────────┘
                            │
                     Kubernetes
                            │
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
            API Pod       API Pod       API Pod
              │             │             │
              └─────────────┼─────────────┘
                            │
             ┌──────────────┼──────────────┐
             ▼              ▼              ▼
          Redis         PostgreSQL       Queue
                                           │
                                  ┌────────┼────────┐
                                  ▼        ▼        ▼
                               Worker   Worker   Worker
                                  │        │        │
                                  └────────┼────────┘
                                           ▼
                                      LLM Provider

             Monitoring:
             Prometheus → Grafana
```

Infrastructure sizing should be finalized after load testing, informed by:

* CPU utilization
* Memory usage
* Request latency
* Requests per second
* Database connections
* Redis performance
* LLM latency
* Provider quotas

---

## 19. Database Scaling

As traffic increases, PostgreSQL scaling would rely on:

* Connection pooling
* Proper indexing
* Query optimization
* Read replicas for read-heavy workloads
* Database monitoring
* Automated backups

None of these are implemented in the current codebase — they represent the intended scaling path. Production deployment should use appropriate connection pooling and database connection limits to efficiently manage concurrent requests.

---

## 20. Redis Scaling

Redis is currently used for response caching *(implemented)*. In a larger production deployment, Redis could also support:

* Rate limiting *(design)*
* Distributed locks where required *(design)*
* Temporary session/context data *(design)*
* Queue-related coordination *(design)*

Larger production workloads would use a highly available Redis configuration; the current setup runs a single Redis instance.

---

## 21. Secrets Management

| Environment  | Approach |
| ------------- | -------- |
| Local development | `.env` file |
| Production          | Kubernetes Secrets, AWS Secrets Manager, HashiCorp Vault, or a cloud-native equivalent |

Secrets are never committed to Git.

---

## 22. Minimal-Downtime Migration

```text
Current Version
      │
      ▼
Deploy New Version
      │
      ▼
Health Checks
      │
      ▼
Small Percentage of Traffic
      │
      ▼
Monitor Metrics
      │
      ▼
Gradually Increase Traffic
      │
      ▼
100% New Version
```

A rolling deployment, or blue-green/canary strategy, would be used in production. This migration process is not implemented in the current project (no Kubernetes deployment or CI/CD pipeline exists yet) — it is documented here as the intended approach. Database schema changes would follow a backward-compatible migration path so old and new application versions can temporarily coexist during rollout.

---

## 23. Security

**Implemented:**

* JWT authentication
* Password hashing
* Environment-based secrets
* Protected `/chat` endpoint
* No API keys committed to source control

**Additional production hardening:**

* HTTPS/TLS
* Network policies
* Secret management
* Container image scanning
* Least-privilege IAM
* API rate limiting
* Security headers
* Regular dependency updates

---

## 24. Project Structure

```text
AI-LLM-Platform-DevOps/
│
├── app/
│   ├── auth.py
│   ├── config.py
│   ├── database.py
│   ├── llm.py
│   ├── main.py
│   ├── metrics.py
│   ├── models.py
│   ├── redis_client.py
│   └── schemas.py
│
├── monitoring/
│   └── prometheus.yml
│
├── tests/
│   └── test_api.py
│
├── .env
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## 25. Future Improvements

* Kubernetes deployment manifests
* Kubernetes HPA
* Background worker implementation
* Message queue integration
* Distributed rate limiting
* LLM provider fallback
* Circuit breaker
* PostgreSQL connection pooling
* Centralized logging
* Distributed tracing
* Alerting through Grafana/Prometheus
* CI/CD pipeline

---

## 26. Conclusion

This project implements a working AI/LLM API — FastAPI, JWT authentication, PostgreSQL persistence, Redis caching, LLM integration, Docker Compose deployment, Prometheus/Grafana monitoring, and automated tests — with clear separation of concerns between application logic, caching, persistence, monitoring, and LLM integration.

Beyond the implementation, this README documents the production scaling and reliability design that would extend the system to handle real-world load: horizontal scaling, Kubernetes orchestration, rate limiting, queue-based processing, retries/circuit breakers, and database/Redis scaling. These are deliberately presented as design rather than code, since implementing full production infrastructure is outside the scope of this assessment — the goal here is to demonstrate that the architecture supports that growth path, not to pre-build it.

Key principles applied to what **is** implemented:

* **Stateless application layer** — enables safe horizontal scaling and fast recovery from failure, once multi-instance deployment is added.
* **Environment-based secrets** — no credentials are hard-coded or committed to source control.
* **Observability by default** — Prometheus and Grafana are wired in from the start, not bolted on later.

The result is a system that runs correctly and is well-tested locally, with an architecture and documented roadmap that reflect the operational realities of running an LLM-backed API in production.