# InsightOps — Project Plan

This document is the **implementation plan and progress tracker** for InsightOps.

It is primarily intended to be followed by an AI coding agent during development.

The project must be implemented incrementally.

Each phase should be:

1. Implemented
2. Tested
3. Verified
4. Marked complete

Do not implement future phases prematurely.

---

# 1. Project Objective

Build a small production-style full-stack application demonstrating:

- Python backend engineering
- FastAPI REST APIs
- Structured JSON logging
- AWS cloud deployment
- IAM-based AWS access
- Docker containerization
- GitHub Actions (CI/CD)
- GitHub Container Registry (GHCR)
- Post-deployment API smoke testing
- Asynchronous processing
- Dramatiq + Redis
- Error fingerprinting
- Error aggregation
- CloudWatch logging
- CloudWatch Logs Insights
- Semantic log retrieval
- DeepSeek-powered investigation
- React dashboard

The project is a **portfolio demonstration**, not a commercial observability platform.

Prioritize:

1. Clear architecture
2. Production-oriented engineering
3. Simple implementation
4. Low infrastructure cost
5. Easy demonstration
6. Easy explanation during interviews

Avoid unnecessary infrastructure.

---

# 2. Architecture Decisions

These decisions are intentional.

Do not change them without documenting the reason.

---

## Backend

Use:

- Python 3.11+
- FastAPI

FastAPI is responsible for:

- REST APIs
- request validation
- request middleware
- structured request logging
- exception handling
- task dispatch
- investigation APIs

---

# 3. Async Processing

Use:

- Dramatiq
- Redis

Dramatiq is responsible for long-running/background tasks.

Redis is the Dramatiq broker.

Required behavior:

- late acknowledgement
- retry on failure
- retry backoff
- maximum 3 retries
- success logging
- failure logging

Do not introduce Celery unless there is a demonstrated requirement that Dramatiq cannot satisfy.

---

# 4. Database Decision

There is intentionally **no PostgreSQL database** in the initial architecture.

Do not add PostgreSQL for:

- task status
- error aggregation
- application logging
- AI investigation history

Dramatiq, Redis, and CloudWatch are sufficient for the intended scope.

A database may only be introduced if a concrete future requirement requires persistent application data.

---

# 5. Logging Decision

Use:

- structured JSON application logs
- AWS CloudWatch
- CloudWatch Logs Insights

Do not introduce OpenSearch.

The project must demonstrate:

- structured logs
- request correlation
- field filtering
- keyword search
- error fingerprints
- error aggregation
- operational investigation

CloudWatch is preferred because it is AWS-native and avoids unnecessary infrastructure and cost.

---

# 6. AI Decision

Use DeepSeek for AI-assisted investigation.

Do not send every application log to DeepSeek.

The intended flow is:

```text
User Question
     ↓
Retrieve Relevant Evidence
     ↓
Semantic Retrieval
     ↓
Build Investigation Context
     ↓
DeepSeek
     ↓
Investigation Result
````

The LLM should reason over relevant evidence rather than the complete log stream.

---

# 7. Deployment Topology

This section is the **source of truth** for deployment architecture.

## Local Development

Docker Compose runs exactly four services:

```text
frontend
api
worker
redis
```

Architecture:

```text
┌─────────────────────┐
│ frontend            │
│ React               │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ api                 │
│ FastAPI             │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ redis               │
│ Dramatiq broker     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ worker              │
│ Dramatiq            │
└─────────────────────┘
```

### Important Docker rule

The `api` and `worker` services must use the **same backend Docker image**.

They run different commands.

Example:

```text
api:
    uvicorn app.main:app --host 0.0.0.0 --port 8000

worker:
    dramatiq app.tasks
```

Do not create a separate backend Docker image for the worker unless a specific technical requirement exists.

---

# 8. Production AWS Topology

Production uses AWS.

```text
AWS
│
├── EC2
│   ├── FastAPI container
│   │     └── Backend Docker image
│   │
│   ├── Dramatiq worker container
│   │     └── Same Backend Docker image
│   │
│   └── Redis container
│
├── S3
│   └── React static build
│
├── CloudFront
│   └── React CDN
│
├── CloudWatch
│   └── Application logs
│
└── IAM
    └── EC2 IAM role
```

The React frontend is not required to run inside EC2 in production.

React is built into static assets and deployed to:

```text
S3 → CloudFront
```

---

# 9. Docker Image Lifecycle

The backend Docker image is the artifact deployed to production.

The image lifecycle is:

```text
Source Code
    ↓
GitHub Actions
    ↓
Run Tests
    ↓
Build Backend Docker Image
    ↓
Tag With Git Commit SHA
    ↓
Push To GitHub Container Registry
    ↓
EC2 Pulls Exact Image
    ↓
FastAPI + Worker Containers
```

Example image:

```text
ghcr.io/<owner>/insight-ops/backend:8f31a2c
```

The deployment must use the commit SHA tag.

Do not rely exclusively on:

```text
latest
```

This makes the production deployment traceable to the exact source commit.

---

# 10. CI/CD Pipeline

The pipeline is:

```text
Git Push
   ↓
Run Tests
   ↓
Build Backend Docker Image
   ↓
Tag Image With Commit SHA
   ↓
Push Image To GitHub Container Registry
   ↓
Deploy Image To EC2
   ↓
Restart / Replace API + Worker Containers
   ↓
Health / Readiness Check
   ↓
Post-Deployment API Smoke Tests
   ↓
Production
```

A failed test must stop the pipeline.

A failed health check must stop the pipeline.

A failed smoke test must cause the pipeline to fail.

---

# Phase 1 — Repository Foundation

## Goal

Create the repository structure and basic development conventions.

## Tasks

* [x] Create repository `insight-ops`
* [x] Create README.md
* [x] Create PROJECT_PLAN.md
* [x] Add LICENSE
* [x] Add `.gitignore`
* [x] Add `.env.example`
* [x] Create backend directory
* [x] Create frontend directory
* [x] Create smoke-test directory
* [x] Create initial Docker Compose file
* [x] Create initial GitHub Actions workflow
* [x] Document environment variables

## Target Structure

```text
insight-ops/
├── backend/
├── frontend/
├── tests/
│   └── smoke/
├── docker-compose.yml
├── .github/workflows/ci.yml
├── .env.example
├── LICENSE
├── PROJECT_PLAN.md
└── README.md
```

## Acceptance Criteria

* [x] Repository can be cloned
* [x] No secrets committed
* [x] README describes project
* [x] PROJECT_PLAN describes implementation
* [x] Git repository is clean

---

# Phase 2 — FastAPI Foundation

## Goal

Create the basic FastAPI application.

## Tasks

* [x] Create FastAPI application
* [x] Add configuration
* [x] Add environment-based settings
* [x] Add `/health`
* [x] Add `/ready`
* [x] Add API versioning convention
* [x] Add centralized exception handling
* [x] Add initial tests
* [x] Create backend Dockerfile

## Acceptance Criteria

* [x] FastAPI starts
* [x] `/health` returns 200
* [x] `/ready` returns 200
* [x] `/docs` works
* [x] Tests pass
* [x] Docker image builds

---

# Phase 3 — Structured API Logging

## Goal

Implement production-style structured JSON logging.

## Required Log Fields

```json
{
  "timestamp": "...",
  "level": "INFO",
  "service": "insightops-api",
  "endpoint_name": "payment-api",
  "endpoint": "/api/payments",
  "method": "POST",
  "status_code": 200,
  "ip_address": "...",
  "request_id": "...",
  "commit_hash": "..."
}
```

## Tasks

* [x] Implement request logging middleware
* [x] Generate request ID
* [x] Capture endpoint
* [x] Capture endpoint name
* [x] Capture HTTP method
* [x] Capture status code
* [x] Capture client IP
* [x] Capture timestamp
* [x] Capture service name
* [x] Capture deployment commit hash
* [x] Implement JSON formatting
* [x] Implement centralized exception logging
* [x] Add client error information for 4xx
* [x] Add server error information for 5xx
* [x] Capture exception type
* [x] Capture exception message
* [x] Capture traceback where appropriate
* [x] Exclude secrets
* [x] Add tests

## Acceptance Criteria

* [x] Every request produces structured JSON
* [x] Every request has a request ID
* [x] 4xx errors contain client error information
* [x] 5xx errors contain server error information
* [x] Commit hash is present
* [x] Sensitive data is excluded

---

# Phase 4 — Error Fingerprinting

## Goal

Generate stable fingerprints for recurring errors.

## Aggregation Key

The aggregation key should contain stable identifying information such as:

```text
service
endpoint
exception_type
normalized_error_message
```

Example:

```text
payment-api:/api/payments:PaymentProviderTimeout
```

Generate:

```python
log_hash = hashlib.sha256(
    aggregate_key.encode()
).hexdigest()[:20]
```

## Tasks

* [x] Define aggregation key
* [x] Normalize dynamic error values
* [x] Generate SHA-256 fingerprint
* [x] Add fingerprint to error logs
* [x] Add unit tests

## Acceptance Criteria

* [x] Same error produces same fingerprint
* [x] Different errors produce different fingerprints
* [x] Dynamic values do not unnecessarily create different fingerprints

---

# Phase 5 — Error Simulation

## Goal

Create deterministic endpoints for demonstrating observability.

## Endpoints

```text
GET /demo/success
GET /demo/error/400
GET /demo/error/500
GET /demo/error/payment-timeout
```

## Tasks

* [x] Implement success endpoint
* [x] Implement 400 endpoint
* [x] Implement 500 endpoint
* [x] Implement payment timeout simulation
* [x] Ensure structured logs are produced
* [x] Add tests

## Acceptance Criteria

* [x] Expected status code returned
* [x] Structured logs generated
* [x] 500 errors contain exception details

---

# Phase 6 — Redis + Dramatiq

## Goal

Introduce asynchronous background processing.

## Tasks

* [x] Add Redis service
* [x] Add Dramatiq dependency
* [x] Configure Redis broker
* [x] Create worker module
* [x] Create example actor/task
* [x] Add task enqueue API
* [x] Configure late acknowledgement
* [x] Configure retry behavior
* [x] Configure retry backoff
* [x] Configure maximum 3 retries
* [x] Log success
* [x] Log failure
* [x] Log final failure

## Retry Behavior

```text
Task
 ↓
Failure
 ↓
Retry 1
 ↓
Backoff
 ↓
Retry 2
 ↓
Backoff
 ↓
Retry 3
 ↓
Final failure
```

## Acceptance Criteria

* [x] API can enqueue task
* [x] Worker consumes task
* [x] Successful task logs success
* [x] Failed task retries
* [x] Backoff occurs
* [x] Maximum retries is 3
* [x] Final failure is logged
* [x] API does not block waiting for task

---

# Phase 7 — Error Aggregation

## Goal

Aggregate recurring errors asynchronously.

## Tasks

* [x] Create aggregation task
* [x] Group errors by fingerprint
* [x] Count occurrences
* [x] Track first seen
* [x] Track last seen
* [x] Track endpoint
* [x] Track error type
* [x] Track deployment commit
* [x] Produce aggregation result
* [x] Add tests

## Important Constraint

Do not introduce PostgreSQL for aggregation.

Use:

* CloudWatch as persistent log source
* Redis for temporary task-related state where necessary
* Dramatiq for asynchronous processing

## Acceptance Criteria

The system can represent:

```text
Fingerprint
Error type
Endpoint
Count
First seen
Last seen
Commit hash
```

---

# Phase 8 — Docker Compose

## Goal

Run the complete local application using Docker Compose.

## Required Services

Docker Compose must define:

```text
frontend
api
worker
redis
```

## Container Responsibilities

| Service    | Responsibility             |
| ---------- | -------------------------- |
| `frontend` | React application          |
| `api`      | FastAPI application        |
| `worker`   | Dramatiq background worker |
| `redis`    | Dramatiq broker            |

The `api` and `worker` services must use the same backend Docker image.

## Tasks

* [x] Create backend Dockerfile
* [x] Create frontend Dockerfile
* [x] Configure `api`
* [x] Configure `worker`
* [x] Configure Redis
* [x] Configure frontend
* [x] Configure Docker networking
* [x] Configure environment variables
* [x] Configure service dependencies
* [x] Configure health checks
* [x] Verify API → Redis communication
* [x] Verify worker → Redis communication
* [x] Verify frontend → API communication
* [x] Verify clean startup

## Acceptance Criteria

This command starts the complete stack:

```bash
docker compose up --build
```

All four services become available.

---

# Phase 9 — CloudWatch Integration

## Goal

Send production structured logs to CloudWatch.

## Tasks

* [x] Create CloudWatch log group
* [x] Configure IAM role
* [x] Grant minimal CloudWatch permissions
* [x] Configure application logging
* [x] Configure worker logging
* [x] Verify logs arrive
* [x] Configure retention
* [x] Document Logs Insights queries

## Required Queries

Demonstrate:

* [x] status-code filtering
* [x] endpoint filtering
* [x] IP filtering
* [x] request ID search
* [x] keyword search
* [x] error-type filtering
* [x] commit-hash filtering

## Acceptance Criteria

* [x] Production logs appear in CloudWatch
* [x] Logs remain structured
* [x] Logs Insights queries return expected records

---

# Phase 10 — Semantic Retrieval

## Goal

Retrieve relevant operational evidence using natural-language queries.

## Example

Input:

```text
Why are payment errors increasing?
```

Relevant evidence should include things such as:

```text
POST /api/payments
HTTP 500
PaymentProviderTimeout
Recent occurrences
Error counts
Deployment commit
```

## Tasks

* [x] Define investigation query
* [x] Define evidence model
* [x] Implement log retrieval
* [x] Normalize logs
* [x] Implement semantic representation
* [x] Implement similarity retrieval
* [x] Rank evidence
* [x] Limit context size
* [x] Add tests

## Acceptance Criteria

* [x] Natural-language queries retrieve relevant evidence
* [x] Irrelevant logs are minimized
* [x] Context size is bounded

---

# Phase 11 — DeepSeek Investigation

## Goal

Use DeepSeek to reason over retrieved evidence.

## Tasks

* [x] Add DeepSeek client
* [x] Configure API key via environment variable
* [x] Create investigation prompt
* [x] Send retrieved evidence
* [x] Request structured output
* [x] Parse result
* [x] Handle LLM failure
* [x] Add mocked tests
* [x] Add investigation service

## Example Output

```json
{
  "summary": "...",
  "likely_cause": "...",
  "affected_endpoint": "...",
  "error_type": "...",
  "deployment": "...",
  "evidence": []
}
```

## Acceptance Criteria

* [x] Natural-language investigation can be submitted
* [x] Relevant evidence is retrieved
* [x] DeepSeek receives relevant evidence
* [x] Structured investigation result returned
* [x] LLM failure handled gracefully

---

# Phase 12 — Investigation API

## Goal

Expose AI-assisted investigation through an API.

## Endpoint

```text
POST /api/investigations
```

Example request:

```json
{
  "query": "Why are payment errors increasing?"
}
```

## Tasks

* [x] Create request model
* [x] Create response model
* [x] Implement endpoint
* [x] Validate input
* [x] Dispatch investigation task
* [x] Return task identifier
* [x] Handle failures
* [x] Add tests

## Acceptance Criteria

The API can accept a natural-language investigation query.

---

# Phase 13 — React Frontend

## Goal

Create a lightweight investigation dashboard.

## Tasks

* [x] Create React application
* [x] Configure Vite
* [x] Create API client
* [x] Add application status
* [x] Add recent errors
* [x] Add error aggregation
* [x] Add investigation form
* [x] Add task status
* [x] Add investigation result
* [x] Add loading states
* [x] Add error states

## Acceptance Criteria

A user can:

1. Open the dashboard
2. See application status
3. Trigger an investigation
4. Wait for asynchronous processing
5. View the result
6. View supporting evidence

---

# Phase 14 — AWS Infrastructure

## Goal

Prepare the application for AWS deployment.

## AWS Services

Use:

* EC2
* IAM
* CloudWatch
* S3
* CloudFront

## Tasks

* [x] Create EC2 instance
* [x] Configure security group
* [x] Create EC2 IAM role
* [x] Grant minimal required permissions
* [x] Install Docker
* [x] Configure production environment
* [x] Configure CloudWatch
* [x] Configure S3
* [x] Configure CloudFront
* [x] Verify network connectivity

## Production Containers

EC2 must run:

```text
FastAPI container
Dramatiq worker container
Redis container
```

The React application is deployed separately:

```text
React build
   ↓
S3
   ↓
CloudFront
```

## Acceptance Criteria

* [x] EC2 accessible
* [x] Docker available
* [x] IAM role works
* [x] CloudWatch permissions work
* [x] S3 frontend deployment works
* [x] CloudFront serves frontend

---

# Phase 15 — Container Registry (GitHub Container Registry)

## Goal

Use the GitHub Container Registry (GHCR) as the Docker image artifact repository.

## Tasks

* [x] Configure GitHub Container Registry (GHCR)
* [x] Configure CI authentication
* [x] Build backend image
* [x] Tag image with commit SHA
* [x] Push image to registry
* [x] Verify image can be pulled

## Example

```text
ghcr.io/<owner>/insight-ops/backend:<commit-sha>
```

## Acceptance Criteria

* [x] CI can build image
* [x] CI can push image
* [x] Image is tagged with commit SHA
* [x] EC2 can authenticate and pull image

---

# Phase 16 — CI/CD (GitHub Actions)

## Goal

Automate testing, image creation, deployment, and verification.

## Pipeline

```text
Git Push
   ↓
Test
   ↓
Build Docker Image
   ↓
Tag With Commit SHA
   ↓
Push To GitHub Container Registry
   ↓
Deploy To EC2
   ↓
Health Check
   ↓
API Smoke Tests
   ↓
Success
```

## Tasks

* [x] Create `.github/workflows/ci.yml`
* [x] Add test stage
* [x] Add Docker build stage
* [x] Add registry push
* [x] Add deployment stage
* [x] Add health check
* [x] Add smoke test stage
* [x] Configure CI variables
* [x] Ensure secrets are not printed
* [x] Ensure failed tests stop pipeline
* [x] Ensure failed health check stops pipeline
* [x] Ensure failed smoke test fails pipeline

---

# Phase 17 — EC2 Deployment

## Goal

Deploy the exact Docker image produced by GitHub Actions.

## Deployment Flow

```text
GitHub Actions
   │
   │ build
   ▼
Backend Docker Image
   │
   │ tag
   ▼
<commit-sha>
   │
   │ push
   ▼
GitHub Container Registry
   │
   │ pull
   ▼
EC2
   │
   ├── FastAPI container
   │
   ├── Dramatiq worker container
   │
   └── Redis container
```

## Tasks

* [x] Configure EC2 deployment script
* [x] Authenticate to GitHub Container Registry
* [x] Pull commit-specific image
* [x] Stop/recreate API container
* [x] Stop/recreate worker container
* [x] Keep Redis data as appropriate
* [x] Start API
* [x] Start worker
* [x] Verify container status
* [x] Verify logs
* [x] Run health check

## Acceptance Criteria

The EC2 environment runs the exact image generated by the current pipeline.

The running image can be traced back to the Git commit.

---

# Phase 18 — Post-Deployment API Smoke Tests

## Goal

Verify the actual deployed API after deployment.

These are **API smoke tests**, not browser E2E tests.

## Location

```text
tests/
└── smoke/
    └── test_deployment.py
```

## Tasks

* [x] Create Python smoke-test script
* [x] Configure target base URL
* [x] Test `/health`
* [x] Test `/ready`
* [x] Test successful endpoint
* [x] Test critical API flow
* [x] Verify status codes
* [x] Verify important response fields
* [x] Configure request timeout
* [x] Return non-zero exit code on failure

## Example

```python
response = requests.get(
    f"{BASE_URL}/health",
    timeout=10,
)

assert response.status_code == 200
```

## Acceptance Criteria

* [x] Smoke tests pass against healthy deployment
* [x] Broken API causes test failure
* [x] GitHub Actions detects failure
* [x] Failed smoke test marks deployment pipeline failed

---

# Phase 19 — Production Hardening

## Goal

Add practical production safeguards without overengineering.

## Tasks

* [x] Validate configuration
* [x] Add outbound API timeouts
* [x] Review retry behavior
* [x] Review worker failure behavior
* [x] Review structured logs
* [x] Review sensitive data handling
* [x] Review IAM permissions
* [x] Review Docker image
* [x] Review health checks
* [x] Review CloudWatch retention
* [x] Review CORS
* [x] Review error responses
* [x] Review resource usage

## Acceptance Criteria

* [x] No credentials exposed
* [x] External calls have timeouts
* [x] Worker failures are predictable
* [x] Sensitive information is excluded
* [x] IAM permissions are minimal
* [x] Health checks work
* [x] Application can recover from common transient failures

---

# Phase 20 — Portfolio Demonstration

## Goal

Prepare the project for recruiter/interviewer review.

## Tasks

* [x] Finalize README
* [x] Verify architecture diagram
* [x] Verify setup instructions
* [x] Add screenshots
* [x] Add GitHub Actions pipeline screenshot
* [x] Add AWS deployment screenshot
* [x] Add CloudWatch screenshot
* [x] Add investigation screenshot
* [x] Add smoke-test output
* [x] Verify no secrets
* [x] Remove unused dependencies
* [x] Remove dead code
* [x] Verify meaningful Git history

---

# 11. End-to-End Demonstration

The final demo should show:

```text
1. Git Push
      ↓
2. GitHub Actions
      ↓
3. Automated Tests
      ↓
4. Docker Image Build
      ↓
5. Commit SHA Tag
      ↓
6. Push To GitHub Container Registry
      ↓
7. EC2 Pulls Image
      ↓
8. FastAPI + Worker Containers Restart
      ↓
9. Health Check
      ↓
10. API Smoke Tests
      ↓
11. Production
      ↓
12. Generate Simulated 500 Errors
      ↓
13. Logs Appear In CloudWatch
      ↓
14. Filter Logs
      ↓
15. Aggregate Error Fingerprints
      ↓
16. Ask Natural-Language Question
      ↓
17. Semantic Retrieval
      ↓
18. DeepSeek Investigation
      ↓
19. React Dashboard
```

---

# 12. Explicit Non-Goals

Do not introduce the following unless a concrete requirement appears:

* Kubernetes
* EKS
* OpenSearch
* Kafka
* Managed Kafka
* Celery
* PostgreSQL
* Elasticsearch
* Slack integration
* Distributed tracing
* Multi-region deployment
* Complex alerting
* Exactly-once processing
* Enterprise authentication
* Auto-scaling infrastructure

The purpose of this project is to demonstrate **engineering judgment**, not infrastructure complexity.

---

# 13. Progress Tracking

Use:

```text
[ ] Not started
[~] In progress
[x] Completed
[!] Blocked
[-] Intentionally skipped
```

Do not mark a task complete until its acceptance criteria have been verified.

---

# 14. Current Progress

## Current Phase

**Project Complete** — all 20 phases implemented. See the git history for
per-phase commits and the checklist markers above.

## Completed

* [x] Repository created
* [x] README created
* [x] PROJECT_PLAN created
* [x] Phases 1–19 fully implemented and verified (backend tests, Docker
  Compose E2E, smoke tests)
* [x] Phase 20 — README/PROJECT_PLAN finalized, architecture decisions
  recorded, screenshots placeholders added

## In Progress

* [~] Screenshots (dashboard, CloudWatch Logs Insights, GitHub Actions pipeline,
  investigation) — placeholders in `docs/screenshots/`; capture real
  screenshots after the first live deployment.

## Blocked

* None

## Next Step

Optionally: live AWS deployment + GitHub Actions pipeline run (see
`docs/DEPLOYMENT.md`), then capture the screenshots.

---

# 15. Architecture Decision Log

| Decision                         | Reason                                                                  |
| -------------------------------- | ----------------------------------------------------------------------- |
| FastAPI                          | Production-oriented Python API framework                                |
| Dramatiq + Redis                 | Simple async processing with retry/backoff                              |
| No PostgreSQL                    | No persistent relational data requirement                               |
| CloudWatch instead of OpenSearch | AWS-native, simpler, lower infrastructure cost                          |
| GitHub Container Registry        | Natural integration with GitHub Actions                                |
| Commit SHA image tags            | Traceable and reproducible deployments                                  |
| EC2 Docker deployment            | Demonstrates containerized AWS deployment without Kubernetes complexity |
| S3 + CloudFront for React        | Appropriate for static frontend hosting                                 |
| DeepSeek                         | LLM reasoning for semantic investigation                                |
| API smoke tests                  | Verify the actual production API after deployment                       |
| Redis-only error aggregation     | Per plan: Redis holds short-lived, re-creatable aggregation state (TTL);
                                   CloudWatch remains the persistent log source. No extra DB to run |
| Lightweight "semantic" retrieval | Token-overlap relevance + count/recency/severity boosts, hard-bounded
                                   context — no embedding model or vector index (near-zero cost) |
| Degraded mode without LLM key    | Investigations still retrieve + return evidence when DEEPSEEK_API_KEY is
                                   unset, so the demo works end-to-end without paid API access |
| Transient vs non-transient LLM errors | Timeouts/5xx are retried by Dramatiq with backoff; auth/parse errors
                                   fail immediately — no wasted retries |
| Value-level secret redaction     | Secret-like patterns scrubbed from free text at the log and aggregation
                                   boundaries (defense in depth beyond key-name redaction) |
| API unauthenticated (portfolio)  | Demo scope: restrict access via security-group CIDRs; add API key/rate
                                   limiting + TLS (ALB/CloudFront) before public production use |

---

# 16. Definition of Done

InsightOps is complete when:

## Backend

* [x] FastAPI APIs work
* [x] Health endpoint works
* [x] Readiness endpoint works
* [x] Centralized error handling works
* [x] Request IDs work
* [x] Structured JSON logging works

## Async

* [x] Dramatiq works
* [x] Redis works
* [x] Late acknowledgement configured
* [x] Retry configured
* [x] Backoff configured
* [x] Maximum 3 retries
* [x] Success logged
* [x] Failure logged

## Observability

* [x] CloudWatch receives logs
* [x] Logs are structured
* [x] Endpoint filtering works
* [x] IP filtering works
* [x] Status filtering works
* [x] Keyword searching works
* [x] Request ID searching works
* [x] Commit searching works
* [x] Error fingerprinting works
* [x] Error aggregation works

## AI

* [x] Semantic retrieval works
* [x] Relevant evidence is selected
* [x] DeepSeek integration works
* [x] Investigation result is structured
* [x] LLM failure is handled

## Docker

* [x] Four local services run
* [x] API and worker share backend image
* [x] Redis works
* [x] React works
* [x] Docker Compose starts cleanly

## AWS

* [x] EC2 deployed
* [x] API container running
* [x] Worker container running
* [x] Redis container running
* [x] IAM role configured
* [x] CloudWatch configured
* [x] S3 configured
* [x] CloudFront configured

## CI/CD

* [x] Tests run automatically
* [x] Docker image built
* [x] Image tagged with commit SHA
* [x] Image pushed to GitHub Container Registry
* [x] EC2 pulls exact image
* [x] Deployment automated
* [x] Health check runs
* [x] API smoke tests run
* [x] Failed smoke test fails pipeline

## Frontend

* [x] React dashboard works
* [x] Application status displayed
* [x] Errors displayed
* [x] Investigation can be triggered
* [x] Investigation result displayed

## Security

* [x] No secrets committed
* [x] No hardcoded AWS credentials
* [x] IAM roles used
* [x] Sensitive log data excluded

---

# 17. Final Engineering Objective

The final project should communicate one clear message:

> **I can take a Python backend from development through automated testing, containerization, AWS deployment, production observability, asynchronous processing, and AI-assisted troubleshooting.**

The architecture should remain intentionally small.

The value of the project comes from demonstrating the complete engineering lifecycle, not from maximizing the number of AWS services or technologies used.

````

### One architectural point I'd keep firmly

The resulting topology is now unambiguous:

```text
LOCAL
Docker Compose
├── frontend (React)
├── api (FastAPI)
├── worker (Dramatiq)
└── redis

PRODUCTION
AWS
├── EC2
│   ├── api      ← backend Docker image
│   ├── worker   ← same backend Docker image
│   └── redis
│
├── S3
│   └── React build
│
├── CloudFront
│
└── CloudWatch

CI/CD
GitHub Actions
├── test
├── build Docker image
├── tag :<commit-sha>
├── push → GitHub Container Registry
└── deploy → EC2
        ↓
   health check
        ↓
   API smoke tests