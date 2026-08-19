# InsightOps

InsightOps is a production-style, full-stack observability and AI-assisted debugging platform.

The project demonstrates how to build, test, deploy, operate, and troubleshoot a modern Python backend end to end using AWS, Docker, GitLab CI/CD, structured logging, asynchronous processing, semantic retrieval, and LLM-assisted investigation.

This is intentionally a **portfolio demonstration**, not a replacement for commercial observability platforms such as Datadog or OpenSearch.

The goal is to demonstrate practical production engineering decisions while keeping the architecture small and cost-conscious.

---

# 🎯 What This Project Demonstrates

| Area | Demonstration |
|---|---|
| Python Backend | FastAPI REST APIs |
| Async Processing | Dramatiq + Redis |
| Containerization | Docker |
| AWS | EC2, IAM, CloudWatch, S3, CloudFront |
| CI/CD | GitLab CI/CD |
| Container Registry | GitLab Container Registry |
| Deployment | Commit-tagged Docker image deployed to EC2 |
| Verification | Health checks + post-deployment API smoke tests |
| Logging | Structured JSON application logs |
| Log Investigation | CloudWatch Logs Insights |
| Error Handling | Error fingerprinting and aggregation |
| AI | Semantic log retrieval + DeepSeek |
| Frontend | React |
| Security | IAM roles and environment-based secrets |
| Production Practices | Retry, backoff, correlation IDs, deployment tracking |

The primary objective is:

> **Demonstrate the ability to build, deploy, operate, and troubleshoot a production-style Python application end to end.**

---

# 🏗️ Architecture

## High-Level Architecture

```text
                              Developer
                                  │
                              Git Push
                                  │
                                  ▼
                         ┌─────────────────┐
                         │    GitLab CI    │
                         │                 │
                         │ Test            │
                         │ Build           │
                         │ Deploy          │
                         │ Smoke Test      │
                         └────────┬────────┘
                                  │
                         Build Docker Image
                                  │
                                  ▼
                    ┌──────────────────────────┐
                    │ GitLab Container Registry│
                    │                          │
                    │ backend:<commit-sha>     │
                    └────────────┬─────────────┘
                                 │
                              Pull Image
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────┐
│                            AWS                               │
│                                                              │
│   ┌──────────────────────────────────────────────────────┐   │
│   │                        EC2                           │   │
│   │                                                      │   │
│   │  ┌─────────────────┐    ┌────────────────────────┐  │   │
│   │  │ FastAPI         │    │ Dramatiq Worker        │  │   │
│   │  │ Container       │    │ Container              │  │   │
│   │  │                 │    │                        │  │   │
│   │  │ Backend Image   │    │ Same Backend Image     │  │   │
│   │  └────────┬────────┘    └───────────┬────────────┘  │   │
│   │           │                         │               │   │
│   │           │                         ▼               │   │
│   │           │                  ┌───────────────┐      │   │
│   │           │                  │ Redis         │      │   │
│   │           │                  │ Container     │      │   │
│   │           │                  └───────────────┘      │   │
│   └───────────┼──────────────────────────────────────────┘   │
│               │                                              │
│               │ IAM Role                                     │
│               ▼                                              │
│       ┌───────────────────┐                                  │
│       │    CloudWatch     │                                  │
│       │                   │                                  │
│       │ Structured Logs   │                                  │
│       │ Logs Insights     │                                  │
│       └───────────────────┘                                  │
│                                                              │
│       ┌───────────────────┐                                  │
│       │       S3          │                                  │
│       │                   │                                  │
│       │ React Static App  │                                  │
│       └─────────┬─────────┘                                  │
│                 │                                            │
│                 ▼                                            │
│       ┌───────────────────┐                                  │
│       │    CloudFront     │                                  │
│       │                   │                                  │
│       │ React CDN         │                                  │
│       └───────────────────┘                                  │
│                                                              │
└──────────────────────────────────────────────────────────────┘
````

---

# 🐳 Container Architecture

## Local Development

Docker Compose runs four containers:

```text
┌─────────────────────┐
│ React Frontend      │
│ frontend            │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ FastAPI             │
│ api                 │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Redis               │
│ redis               │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Dramatiq Worker     │
│ worker              │
└─────────────────────┘
```

The FastAPI API and Dramatiq worker use the **same backend Docker image**, but run different commands.

For example:

```text
api:
    uvicorn app.main:app ...

worker:
    dramatiq app.tasks ...
```

This avoids maintaining two separate backend images.

---

# ☁️ Production Container Architecture

Production runs the backend workloads on AWS EC2.

```text
AWS EC2
│
├── FastAPI container
│     └── Backend Docker image
│
├── Dramatiq worker container
│     └── Same Backend Docker image
│
└── Redis container
```

The React frontend is deployed separately:

```text
React build
    ↓
S3
    ↓
CloudFront
```

Application logs are sent to:

```text
FastAPI / Worker
      ↓
CloudWatch
```

---

# 🔄 CI/CD Pipeline

Every deployment follows this flow:

```text
Git Push
   ↓
Run Automated Tests
   ↓
Build Backend Docker Image
   ↓
Tag Image With Git Commit SHA
   ↓
Push Image To GitLab Container Registry
   ↓
Deploy Image To AWS EC2
   ↓
Restart / Replace API + Worker Containers
   ↓
Health / Readiness Check
   ↓
Post-Deployment API Smoke Tests
   ↓
Production
```

The Docker image is tagged with the Git commit SHA.

Example:

```text
insight-ops-backend:8f31a2c
```

This makes the deployed version directly traceable to source control.

The deployment does not rely solely on `latest`.

---

# 🚀 Deployment Flow

A typical deployment looks like:

```text
Developer
   │
   │ git push
   ▼
GitLab
   │
   ├── Tests
   │
   ├── Docker Build
   │
   └── Push Image
          │
          ▼
GitLab Container Registry
          │
          │ pull
          ▼
       AWS EC2
          │
          ├── FastAPI
          ├── Dramatiq
          └── Redis
          │
          ▼
     Health Check
          │
          ▼
  API Smoke Tests
          │
          ▼
       Success
```

If the health check or smoke test fails, the deployment pipeline fails.

---

# 🧪 Post-Deployment API Smoke Tests

A deployment is not considered successful simply because the Docker containers started.

After deployment, GitLab CI runs a small Python-based API smoke-test suite against the actual deployed application.

These are **API smoke tests**, not browser-based E2E tests.

Example:

```python
response = requests.get(
    f"{BASE_URL}/health",
    timeout=10,
)

assert response.status_code == 200
```

Critical API flows are also tested.

The smoke tests verify that:

* the API is reachable
* routing works
* the application is responding correctly
* expected HTTP status codes are returned
* important response fields are present

This catches problems that a simple container or process health check cannot detect.

---

# 🐍 FastAPI Backend

The backend is implemented using FastAPI.

It demonstrates:

* REST API design
* request validation
* middleware
* centralized exception handling
* request correlation IDs
* structured logging
* health/readiness endpoints
* asynchronous task dispatch
* investigation APIs

Example endpoints:

```text
GET  /health
GET  /ready

GET  /demo/success
GET  /demo/error/400
GET  /demo/error/500
GET  /demo/error/payment-timeout

POST /api/investigations
```

---

# ⚙️ Async Processing

Long-running operations are processed asynchronously using:

* Dramatiq
* Redis

The API does not block while background work is performed.

```text
FastAPI
   │
   │ enqueue task
   ▼
 Redis
   │
   ▼
Dramatiq Worker
   │
   ├── Success
   │     └── Structured log
   │
   └── Failure
         │
         ▼
       Retry
         │
         ▼
       Backoff
         │
         ▼
       Retry
         │
         ▼
       Retry
         │
         ▼
    Final failure
         │
         └── Structured log
```

The worker demonstrates:

* late acknowledgement
* retry on failure
* retry backoff
* maximum 3 retries
* success logging
* failure logging

The project intentionally does not implement exactly-once processing or a durable task-result database.

This is a portfolio demonstration rather than a transactional processing platform.

---

# 📝 Structured Logging

InsightOps uses structured JSON logging.

Example:

```json
{
  "timestamp": "2026-08-19T10:30:15Z",
  "level": "ERROR",
  "service": "payment-api",
  "endpoint_name": "payment-api",
  "endpoint": "/api/payments",
  "method": "POST",
  "status_code": 500,
  "ip_address": "10.0.1.25",
  "request_id": "abc-123",
  "commit_hash": "8f31a2c",
  "error_type": "PaymentProviderTimeout",
  "error_message": "Payment provider timed out"
}
```

For server-side failures, exception information is also captured where appropriate:

```json
{
  "level": "ERROR",
  "error_type": "PaymentProviderTimeout",
  "exception": {
    "type": "TimeoutError",
    "message": "Upstream request timed out",
    "traceback": "..."
  }
}
```

Sensitive information is intentionally excluded from logs.

Examples:

* authentication tokens
* API keys
* passwords
* payment information
* secrets

---

# 🔗 Request Correlation

Every API request receives a `request_id`.

This allows related logs to be connected.

```text
Client Request
      │
      ▼
request_id = abc-123
      │
      ├── API log
      ├── Application log
      ├── Background task log
      └── Error log
```

This provides lightweight request tracing without introducing a full distributed tracing system.

---

# 🚨 Error Fingerprinting

Recurring errors are assigned a stable fingerprint.

The aggregation key can contain:

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

The key is hashed:

```python
log_hash = hashlib.sha256(
    aggregate_key.encode()
).hexdigest()[:20]
```

Repeated occurrences can therefore be grouped:

```text
PaymentProviderTimeout
POST /api/payments
Count: 127
```

instead of being treated as 127 unrelated errors.

---

# 📊 Error Aggregation

Error aggregation is performed asynchronously by Dramatiq.

The aggregation process groups recurring errors by fingerprint and can track:

```text
Fingerprint
Error type
Endpoint
Count
First seen
Last seen
Deployment commit
```

The project intentionally does not implement the original Slack notification workflow.

The portfolio version focuses on:

```text
Error
  ↓
Fingerprint
  ↓
Aggregate
  ↓
Investigate
```

rather than building a notification system that isn't required to demonstrate the core engineering concepts.

---

# ☁️ CloudWatch Observability

AWS CloudWatch is used as the centralized log platform.

CloudWatch was selected instead of OpenSearch because the project's primary goal is to demonstrate:

* structured logging
* AWS-native observability
* operational debugging
* field-based filtering
* keyword searching
* error investigation

without adding the infrastructure and cost of a dedicated search cluster.

---

# 🔎 CloudWatch Logs Insights

Structured logs allow developers to investigate production behavior.

### Filter by status code

```text
fields @timestamp, endpoint, status_code, error_type
| filter status_code >= 500
| sort @timestamp desc
```

### Filter by endpoint

```text
fields @timestamp, endpoint, status_code, error_type
| filter endpoint = "/api/payments"
| sort @timestamp desc
```

### Filter by IP address

```text
fields @timestamp, ip_address, endpoint, status_code
| filter ip_address = "10.0.1.25"
```

### Search by keyword

```text
fields @timestamp, endpoint, error_message
| filter error_message like /timeout/
| sort @timestamp desc
```

### Search by request ID

```text
fields @timestamp, request_id, endpoint, status_code
| filter request_id = "abc-123"
```

### Search by deployment

```text
fields @timestamp, commit_hash, endpoint, status_code
| filter commit_hash = "8f31a2c"
```

This demonstrates practical production log debugging without requiring OpenSearch.

---

# 🤖 Semantic Debugging

Traditional log debugging requires the developer to know what to search for.

For example:

```text
status_code = 500
endpoint = /api/payments
error_type = PaymentProviderTimeout
```

InsightOps adds a semantic investigation layer.

A developer can ask:

> Why are payment errors increasing?

or:

> What caused the spike in 500 errors after the latest deployment?

The system retrieves relevant evidence before sending it to the LLM.

```text
Developer Question
       │
       ▼
Investigation API
       │
       ▼
Retrieve Relevant Logs
       │
       ├── Error fingerprints
       ├── Error counts
       ├── Relevant endpoints
       ├── Request context
       └── Deployment context
       │
       ▼
Semantic Retrieval
       │
       ▼
Relevant Evidence
       │
       ▼
DeepSeek
       │
       ▼
Investigation
```

The LLM does not receive the entire log stream.

Only relevant evidence is provided.

---

# 🧠 DeepSeek Investigation

DeepSeek is used for reasoning over retrieved operational evidence.

Example:

```text
Developer:

"Why are payment errors increasing?"
```

InsightOps retrieves relevant evidence such as:

```text
POST /api/payments
HTTP 500
PaymentProviderTimeout
Count: 127
Commit: 8f31a2c
```

DeepSeek then analyzes the evidence.

Example result:

```text
Payment failures increased significantly after deployment 8f31a2c.

The dominant failure is PaymentProviderTimeout,
representing the majority of recent payment errors.

The failures are concentrated on:

POST /api/payments

The timing and error pattern suggest the latest deployment
may have introduced a change affecting the upstream payment
provider interaction.
```

The AI is intended to assist developers during investigation, not replace human judgment.

---

# 💥 Error Simulation

The application includes deterministic failure endpoints.

Example:

```text
GET /demo/success
GET /demo/error/400
GET /demo/error/500
GET /demo/error/payment-timeout
```

This makes it possible to demonstrate the complete observability workflow without requiring a real production incident.

Example:

```text
Generate 500 errors
       ↓
Structured API logs
       ↓
CloudWatch
       ↓
Dramatiq aggregation
       ↓
Semantic retrieval
       ↓
DeepSeek investigation
       ↓
React dashboard
```

---

# 🖥️ React Frontend

The frontend provides a lightweight dashboard for:

* application status
* error activity
* error aggregation
* asynchronous task status
* semantic investigation
* AI investigation results

Production hosting:

```text
React Build
    ↓
S3
    ↓
CloudFront
```

The frontend is intentionally lightweight.

The primary engineering focus is the backend, cloud deployment, observability, CI/CD, and AI-assisted debugging.

---

# 🔐 Security

The project demonstrates basic production security practices.

* AWS IAM roles instead of hardcoded AWS credentials
* Environment-based secrets
* No API keys committed to source control
* Sensitive information excluded from logs
* Minimal IAM permissions where practical
* Separate local and production configuration

The EC2 instance uses an IAM role to access AWS services.

AWS credentials are not stored inside the Docker image.

---

# 💰 Cost-Conscious Design

InsightOps is intentionally designed as a portfolio demonstration.

The architecture avoids infrastructure that is unnecessary for demonstrating the intended engineering concepts.

It does not use:

* OpenSearch
* Kubernetes / EKS
* Kafka
* Managed Kafka
* Distributed tracing infrastructure
* Dedicated log-search clusters
* Managed task-processing platforms

The intended production footprint is:

```text
EC2
├── FastAPI
├── Dramatiq
└── Redis

CloudWatch
└── Application logs

S3 + CloudFront
└── React frontend
```

DeepSeek is called for investigations rather than for every application log.

Actual AWS cost depends on region, traffic, storage, account eligibility, and current AWS pricing/free-tier terms.

---

# 🚀 Quick Start

## Prerequisites

* Python 3.11+
* Node.js 18+
* Docker
* Docker Compose
* AWS account for deployment
* GitLab account
* DeepSeek API key

---

## Clone

```bash
git clone https://gitlab.com/<your-username>/insight-ops.git

cd insight-ops
```

---

# 🐳 Local Development

Start the complete stack:

```bash
docker compose up --build
```

Docker Compose runs:

```text
frontend
api
worker
redis
```

The API and worker use the same backend Docker image.

Local endpoints:

```text
Frontend:
http://localhost:5173

API:
http://localhost:8000

API Documentation:
http://localhost:8000/docs
```

## Backend-only (no Docker)

Useful when only working on the backend (Redis required for task dispatch):

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/uvicorn app.main:app --reload --port 8000
# in a second terminal, run the worker:
.venv/bin/dramatiq app.tasks
```

> The code targets Python 3.11+; the same suite also runs on 3.9 locally.

---

# 🧪 Testing

InsightOps uses several levels of testing.

## Automated Tests

Backend unit/integration tests (pytest, no real Redis or network needed —
a StubBroker + fakeredis are used):

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q
```

Example output:

```text
................................  [100%]
54 passed in 2.54s
```

## Health Checks

Run after deployment:

```text
GET /health
GET /ready
```

## API Smoke Tests

Run against the actual deployed environment (or the local stack):

```bash
BASE_URL=http://localhost:8000 python -m pytest tests/smoke -q
```

The smoke tests verify:

* API availability
* critical endpoints
* expected HTTP status codes
* important response fields
* the async error-aggregation flow (error -> fingerprint aggregation)
* investigation creation + polling

A smoke-test failure causes the CI/CD pipeline to fail. Captured output:
`docs/smoke-test-output.txt`.

---

# 📁 Repository Structure

```text
insight-ops/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── logging/
│   │   ├── services/
│   │   ├── tasks/
│   │   └── investigation/
│   │
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   ├── package.json
│   └── Dockerfile
│
├── tests/
│   └── smoke/
│       └── test_deployment.py
│
├── docker-compose.yml
├── .gitlab-ci.yml
├── .env.example
├── LICENSE
├── PROJECT_PLAN.md
└── README.md
```

---

# 🎯 End-to-End Demonstration

The complete portfolio demonstration follows this flow:

```text
1. Developer pushes code
        ↓
2. GitLab CI runs tests
        ↓
3. Docker image is built
        ↓
4. Image is tagged with commit SHA
        ↓
5. Image is pushed to GitLab Container Registry
        ↓
6. EC2 pulls the new image
        ↓
7. FastAPI + Dramatiq containers restart
        ↓
8. Health / readiness checks run
        ↓
9. Post-deployment API smoke tests run
        ↓
10. Production deployment succeeds
        ↓
11. Generate simulated 500 errors
        ↓
12. Structured logs appear in CloudWatch
        ↓
13. Investigate logs using Logs Insights
        ↓
14. Error fingerprints are aggregated
        ↓
15. Ask a natural-language question
        ↓
16. Semantic retrieval finds relevant evidence
        ↓
17. DeepSeek analyzes the evidence
        ↓
18. React dashboard displays the investigation
```

---

# 📌 Project Scope

InsightOps is intentionally scoped to demonstrate production engineering fundamentals rather than recreate a commercial observability platform.

The core engineering story is:

```text
Python Backend
      +
Docker
      +
AWS
      +
CI/CD
      +
Structured Logging
      +
Async Processing
      +
Operational Debugging
      +
Semantic Retrieval
      +
AI Investigation
```

The project demonstrates the ability to take a backend application from development through production deployment and operational troubleshooting.

---

# 📄 License

MIT License