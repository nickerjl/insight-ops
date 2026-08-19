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
- GitLab CI/CD
- GitLab Container Registry
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
GitLab CI
    ↓
Run Tests
    ↓
Build Backend Docker Image
    ↓
Tag With Git Commit SHA
    ↓
Push To GitLab Container Registry
    ↓
EC2 Pulls Exact Image
    ↓
FastAPI + Worker Containers
```

Example image:

```text
registry.gitlab.com/<namespace>/insight-ops/backend:8f31a2c
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
Push Image To GitLab Container Registry
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

* [ ] Create repository `insight-ops`
* [ ] Create README.md
* [ ] Create PROJECT_PLAN.md
* [ ] Add LICENSE
* [ ] Add `.gitignore`
* [ ] Add `.env.example`
* [ ] Create backend directory
* [ ] Create frontend directory
* [ ] Create smoke-test directory
* [ ] Create initial Docker Compose file
* [ ] Create initial GitLab CI configuration
* [ ] Document environment variables

## Target Structure

```text
insight-ops/
├── backend/
├── frontend/
├── tests/
│   └── smoke/
├── docker-compose.yml
├── .gitlab-ci.yml
├── .env.example
├── LICENSE
├── PROJECT_PLAN.md
└── README.md
```

## Acceptance Criteria

* [ ] Repository can be cloned
* [ ] No secrets committed
* [ ] README describes project
* [ ] PROJECT_PLAN describes implementation
* [ ] Git repository is clean

---

# Phase 2 — FastAPI Foundation

## Goal

Create the basic FastAPI application.

## Tasks

* [ ] Create FastAPI application
* [ ] Add configuration
* [ ] Add environment-based settings
* [ ] Add `/health`
* [ ] Add `/ready`
* [ ] Add API versioning convention
* [ ] Add centralized exception handling
* [ ] Add initial tests
* [ ] Create backend Dockerfile

## Acceptance Criteria

* [ ] FastAPI starts
* [ ] `/health` returns 200
* [ ] `/ready` returns 200
* [ ] `/docs` works
* [ ] Tests pass
* [ ] Docker image builds

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

* [ ] Implement request logging middleware
* [ ] Generate request ID
* [ ] Capture endpoint
* [ ] Capture endpoint name
* [ ] Capture HTTP method
* [ ] Capture status code
* [ ] Capture client IP
* [ ] Capture timestamp
* [ ] Capture service name
* [ ] Capture deployment commit hash
* [ ] Implement JSON formatting
* [ ] Implement centralized exception logging
* [ ] Add client error information for 4xx
* [ ] Add server error information for 5xx
* [ ] Capture exception type
* [ ] Capture exception message
* [ ] Capture traceback where appropriate
* [ ] Exclude secrets
* [ ] Add tests

## Acceptance Criteria

* [ ] Every request produces structured JSON
* [ ] Every request has a request ID
* [ ] 4xx errors contain client error information
* [ ] 5xx errors contain server error information
* [ ] Commit hash is present
* [ ] Sensitive data is excluded

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

* [ ] Define aggregation key
* [ ] Normalize dynamic error values
* [ ] Generate SHA-256 fingerprint
* [ ] Add fingerprint to error logs
* [ ] Add unit tests

## Acceptance Criteria

* [ ] Same error produces same fingerprint
* [ ] Different errors produce different fingerprints
* [ ] Dynamic values do not unnecessarily create different fingerprints

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

* [ ] Implement success endpoint
* [ ] Implement 400 endpoint
* [ ] Implement 500 endpoint
* [ ] Implement payment timeout simulation
* [ ] Ensure structured logs are produced
* [ ] Add tests

## Acceptance Criteria

* [ ] Expected status code returned
* [ ] Structured logs generated
* [ ] 500 errors contain exception details

---

# Phase 6 — Redis + Dramatiq

## Goal

Introduce asynchronous background processing.

## Tasks

* [ ] Add Redis service
* [ ] Add Dramatiq dependency
* [ ] Configure Redis broker
* [ ] Create worker module
* [ ] Create example actor/task
* [ ] Add task enqueue API
* [ ] Configure late acknowledgement
* [ ] Configure retry behavior
* [ ] Configure retry backoff
* [ ] Configure maximum 3 retries
* [ ] Log success
* [ ] Log failure
* [ ] Log final failure

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

* [ ] API can enqueue task
* [ ] Worker consumes task
* [ ] Successful task logs success
* [ ] Failed task retries
* [ ] Backoff occurs
* [ ] Maximum retries is 3
* [ ] Final failure is logged
* [ ] API does not block waiting for task

---

# Phase 7 — Error Aggregation

## Goal

Aggregate recurring errors asynchronously.

## Tasks

* [ ] Create aggregation task
* [ ] Group errors by fingerprint
* [ ] Count occurrences
* [ ] Track first seen
* [ ] Track last seen
* [ ] Track endpoint
* [ ] Track error type
* [ ] Track deployment commit
* [ ] Produce aggregation result
* [ ] Add tests

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

* [ ] Create backend Dockerfile
* [ ] Create frontend Dockerfile
* [ ] Configure `api`
* [ ] Configure `worker`
* [ ] Configure Redis
* [ ] Configure frontend
* [ ] Configure Docker networking
* [ ] Configure environment variables
* [ ] Configure service dependencies
* [ ] Configure health checks
* [ ] Verify API → Redis communication
* [ ] Verify worker → Redis communication
* [ ] Verify frontend → API communication
* [ ] Verify clean startup

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

* [ ] Create CloudWatch log group
* [ ] Configure IAM role
* [ ] Grant minimal CloudWatch permissions
* [ ] Configure application logging
* [ ] Configure worker logging
* [ ] Verify logs arrive
* [ ] Configure retention
* [ ] Document Logs Insights queries

## Required Queries

Demonstrate:

* [ ] status-code filtering
* [ ] endpoint filtering
* [ ] IP filtering
* [ ] request ID search
* [ ] keyword search
* [ ] error-type filtering
* [ ] commit-hash filtering

## Acceptance Criteria

* [ ] Production logs appear in CloudWatch
* [ ] Logs remain structured
* [ ] Logs Insights queries return expected records

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

* [ ] Define investigation query
* [ ] Define evidence model
* [ ] Implement log retrieval
* [ ] Normalize logs
* [ ] Implement semantic representation
* [ ] Implement similarity retrieval
* [ ] Rank evidence
* [ ] Limit context size
* [ ] Add tests

## Acceptance Criteria

* [ ] Natural-language queries retrieve relevant evidence
* [ ] Irrelevant logs are minimized
* [ ] Context size is bounded

---

# Phase 11 — DeepSeek Investigation

## Goal

Use DeepSeek to reason over retrieved evidence.

## Tasks

* [ ] Add DeepSeek client
* [ ] Configure API key via environment variable
* [ ] Create investigation prompt
* [ ] Send retrieved evidence
* [ ] Request structured output
* [ ] Parse result
* [ ] Handle LLM failure
* [ ] Add mocked tests
* [ ] Add investigation service

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

* [ ] Natural-language investigation can be submitted
* [ ] Relevant evidence is retrieved
* [ ] DeepSeek receives relevant evidence
* [ ] Structured investigation result returned
* [ ] LLM failure handled gracefully

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

* [ ] Create request model
* [ ] Create response model
* [ ] Implement endpoint
* [ ] Validate input
* [ ] Dispatch investigation task
* [ ] Return task identifier
* [ ] Handle failures
* [ ] Add tests

## Acceptance Criteria

The API can accept a natural-language investigation query.

---

# Phase 13 — React Frontend

## Goal

Create a lightweight investigation dashboard.

## Tasks

* [ ] Create React application
* [ ] Configure Vite
* [ ] Create API client
* [ ] Add application status
* [ ] Add recent errors
* [ ] Add error aggregation
* [ ] Add investigation form
* [ ] Add task status
* [ ] Add investigation result
* [ ] Add loading states
* [ ] Add error states

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

* [ ] Create EC2 instance
* [ ] Configure security group
* [ ] Create EC2 IAM role
* [ ] Grant minimal required permissions
* [ ] Install Docker
* [ ] Configure production environment
* [ ] Configure CloudWatch
* [ ] Configure S3
* [ ] Configure CloudFront
* [ ] Verify network connectivity

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

* [ ] EC2 accessible
* [ ] Docker available
* [ ] IAM role works
* [ ] CloudWatch permissions work
* [ ] S3 frontend deployment works
* [ ] CloudFront serves frontend

---

# Phase 15 — GitLab Container Registry

## Goal

Use GitLab Container Registry as the Docker image artifact repository.

## Tasks

* [ ] Configure GitLab Container Registry
* [ ] Configure CI authentication
* [ ] Build backend image
* [ ] Tag image with commit SHA
* [ ] Push image to registry
* [ ] Verify image can be pulled

## Example

```text
registry.gitlab.com/<namespace>/insight-ops/backend:<commit-sha>
```

## Acceptance Criteria

* [ ] CI can build image
* [ ] CI can push image
* [ ] Image is tagged with commit SHA
* [ ] EC2 can authenticate and pull image

---

# Phase 16 — GitLab CI/CD

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
Push To GitLab Container Registry
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

* [ ] Create `.gitlab-ci.yml`
* [ ] Add test stage
* [ ] Add Docker build stage
* [ ] Add registry push
* [ ] Add deployment stage
* [ ] Add health check
* [ ] Add smoke test stage
* [ ] Configure CI variables
* [ ] Ensure secrets are not printed
* [ ] Ensure failed tests stop pipeline
* [ ] Ensure failed health check stops pipeline
* [ ] Ensure failed smoke test fails pipeline

---

# Phase 17 — EC2 Deployment

## Goal

Deploy the exact Docker image produced by GitLab CI.

## Deployment Flow

```text
GitLab CI
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
GitLab Container Registry
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

* [ ] Configure EC2 deployment script
* [ ] Authenticate to GitLab Registry
* [ ] Pull commit-specific image
* [ ] Stop/recreate API container
* [ ] Stop/recreate worker container
* [ ] Keep Redis data as appropriate
* [ ] Start API
* [ ] Start worker
* [ ] Verify container status
* [ ] Verify logs
* [ ] Run health check

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

* [ ] Create Python smoke-test script
* [ ] Configure target base URL
* [ ] Test `/health`
* [ ] Test `/ready`
* [ ] Test successful endpoint
* [ ] Test critical API flow
* [ ] Verify status codes
* [ ] Verify important response fields
* [ ] Configure request timeout
* [ ] Return non-zero exit code on failure

## Example

```python
response = requests.get(
    f"{BASE_URL}/health",
    timeout=10,
)

assert response.status_code == 200
```

## Acceptance Criteria

* [ ] Smoke tests pass against healthy deployment
* [ ] Broken API causes test failure
* [ ] GitLab CI detects failure
* [ ] Failed smoke test marks deployment pipeline failed

---

# Phase 19 — Production Hardening

## Goal

Add practical production safeguards without overengineering.

## Tasks

* [ ] Validate configuration
* [ ] Add outbound API timeouts
* [ ] Review retry behavior
* [ ] Review worker failure behavior
* [ ] Review structured logs
* [ ] Review sensitive data handling
* [ ] Review IAM permissions
* [ ] Review Docker image
* [ ] Review health checks
* [ ] Review CloudWatch retention
* [ ] Review CORS
* [ ] Review error responses
* [ ] Review resource usage

## Acceptance Criteria

* [ ] No credentials exposed
* [ ] External calls have timeouts
* [ ] Worker failures are predictable
* [ ] Sensitive information is excluded
* [ ] IAM permissions are minimal
* [ ] Health checks work
* [ ] Application can recover from common transient failures

---

# Phase 20 — Portfolio Demonstration

## Goal

Prepare the project for recruiter/interviewer review.

## Tasks

* [ ] Finalize README
* [ ] Verify architecture diagram
* [ ] Verify setup instructions
* [ ] Add screenshots
* [ ] Add GitLab pipeline screenshot
* [ ] Add AWS deployment screenshot
* [ ] Add CloudWatch screenshot
* [ ] Add investigation screenshot
* [ ] Add smoke-test output
* [ ] Verify no secrets
* [ ] Remove unused dependencies
* [ ] Remove dead code
* [ ] Verify meaningful Git history

---

# 11. End-to-End Demonstration

The final demo should show:

```text
1. Git Push
      ↓
2. GitLab CI
      ↓
3. Automated Tests
      ↓
4. Docker Image Build
      ↓
5. Commit SHA Tag
      ↓
6. Push To GitLab Container Registry
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

**Phase 1 — Repository Foundation**

## Completed

* [ ] Repository created
* [ ] README created
* [ ] PROJECT_PLAN created

## In Progress

* None

## Blocked

* None

## Next Step

Complete Phase 1 before starting Phase 2.

---

# 15. Architecture Decision Log

| Decision                         | Reason                                                                  |
| -------------------------------- | ----------------------------------------------------------------------- |
| FastAPI                          | Production-oriented Python API framework                                |
| Dramatiq + Redis                 | Simple async processing with retry/backoff                              |
| No PostgreSQL                    | No persistent relational data requirement                               |
| CloudWatch instead of OpenSearch | AWS-native, simpler, lower infrastructure cost                          |
| GitLab Container Registry        | Natural integration with GitLab CI/CD                                   |
| Commit SHA image tags            | Traceable and reproducible deployments                                  |
| EC2 Docker deployment            | Demonstrates containerized AWS deployment without Kubernetes complexity |
| S3 + CloudFront for React        | Appropriate for static frontend hosting                                 |
| DeepSeek                         | LLM reasoning for semantic investigation                                |
| API smoke tests                  | Verify the actual production API after deployment                       |

---

# 16. Definition of Done

InsightOps is complete when:

## Backend

* [ ] FastAPI APIs work
* [ ] Health endpoint works
* [ ] Readiness endpoint works
* [ ] Centralized error handling works
* [ ] Request IDs work
* [ ] Structured JSON logging works

## Async

* [ ] Dramatiq works
* [ ] Redis works
* [ ] Late acknowledgement configured
* [ ] Retry configured
* [ ] Backoff configured
* [ ] Maximum 3 retries
* [ ] Success logged
* [ ] Failure logged

## Observability

* [ ] CloudWatch receives logs
* [ ] Logs are structured
* [ ] Endpoint filtering works
* [ ] IP filtering works
* [ ] Status filtering works
* [ ] Keyword searching works
* [ ] Request ID searching works
* [ ] Commit searching works
* [ ] Error fingerprinting works
* [ ] Error aggregation works

## AI

* [ ] Semantic retrieval works
* [ ] Relevant evidence is selected
* [ ] DeepSeek integration works
* [ ] Investigation result is structured
* [ ] LLM failure is handled

## Docker

* [ ] Four local services run
* [ ] API and worker share backend image
* [ ] Redis works
* [ ] React works
* [ ] Docker Compose starts cleanly

## AWS

* [ ] EC2 deployed
* [ ] API container running
* [ ] Worker container running
* [ ] Redis container running
* [ ] IAM role configured
* [ ] CloudWatch configured
* [ ] S3 configured
* [ ] CloudFront configured

## CI/CD

* [ ] Tests run automatically
* [ ] Docker image built
* [ ] Image tagged with commit SHA
* [ ] Image pushed to GitLab Registry
* [ ] EC2 pulls exact image
* [ ] Deployment automated
* [ ] Health check runs
* [ ] API smoke tests run
* [ ] Failed smoke test fails pipeline

## Frontend

* [ ] React dashboard works
* [ ] Application status displayed
* [ ] Errors displayed
* [ ] Investigation can be triggered
* [ ] Investigation result displayed

## Security

* [ ] No secrets committed
* [ ] No hardcoded AWS credentials
* [ ] IAM roles used
* [ ] Sensitive log data excluded

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
GitLab
├── test
├── build Docker image
├── tag :<commit-sha>
├── push → GitLab Container Registry
└── deploy → EC2
        ↓
   health check
        ↓
   API smoke tests