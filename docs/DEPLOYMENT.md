# InsightOps deployment runbook

This guide walks through deploying InsightOps end-to-end: infrastructure via
CloudFormation, then the app via the GitLab CI/CD pipeline.

> Prerequisites: AWS account, GitLab project, GitLab runner (or GitLab.com
> shared runners with Docker), an EC2 key pair.

## 1. Provision AWS infrastructure

```bash
# Get a real Amazon Linux 2023 AMI id for your region first
# (update deploy/cloudformation.yaml RegionMap), then:
aws cloudformation deploy \
  --template-file deploy/cloudformation.yaml \
  --stack-name insight-ops \
  --parameter-overrides KeyPairName=your-key-pair \
  --capabilities CAPABILITY_IAM
```

Note the stack outputs:

| Output | Purpose |
| --- | --- |
| `Ec2PublicDns` / `Ec2PublicIp` | set `EC2_HOST` CI variable |
| `ApiUrl` | set `DEPLOYMENT_URL` CI variable |
| `FrontendUrl` | CloudFront URL of the dashboard |
| `FrontendBucketName` | set `S3_FRONTEND_BUCKET` CI variable |
| `CloudFrontDistributionId` | set `CLOUDFRONT_DISTRIBUTION_ID` CI variable |
| `LogGroupName` | CloudWatch log group (retention 7 days) |

The EC2 user-data installs Docker + compose and creates `/opt/insight-ops`.
The instance IAM role is limited to CloudWatch logs.

## 2. Configure GitLab CI/CD variables

Settings → CI/CD → Variables (all **masked**, `SSH_PRIVATE_KEY`/AWS keys
also **protected**):

| Variable | Example |
| --- | --- |
| `EC2_HOST` | `ec2-1-2-3-4.eu-west-1.compute.amazonaws.com` |
| `DEPLOYMENT_URL` | `http://ec2-1-2-3-4.eu-west-1.compute.amazonaws.com:8000` |
| `SSH_PRIVATE_KEY` | private key of `KeyPairName` (for user `ec2-user`) |
| `SSH_USER` | `ec2-user` (default) |
| `DEEPSEEK_API_KEY` | DeepSeek API key (leave empty for degraded mode) |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | CI credentials for S3 sync + CloudFront invalidation |
| `AWS_DEFAULT_REGION` | e.g. `eu-west-1` |
| `S3_FRONTEND_BUCKET` | from stack outputs |
| `CLOUDFRONT_DISTRIBUTION_ID` | from stack outputs |
| `PROD_ENV_FILE` | (optional) path to a `.env.prod` to upload to EC2 |

The GitLab Container Registry is enabled by default on GitLab.com; the
pipeline uses the built-in `CI_REGISTRY_*` variables.

## 3. Push and let CI/CD run

```bash
git push origin main
```

The pipeline: `test → build (push commit-tagged image) → deploy (EC2 + S3) →
smoke tests`. If smoke tests fail, the pipeline fails.

## 4. Verify

- Dashboard: `https://<FrontendUrl>`
- API health: `curl <DEPLOYMENT_URL>/health`
- Logs: CloudWatch → Logs Insights → log group `/insight-ops/prod`
  (queries in `docs/logs-insights-queries.md`)
- Demo: hit `<DEPLOYMENT_URL>/demo/error/500` a few times, then
  `<DEPLOYMENT_URL>/api/errors/aggregations`

## Manual rollback

Redeploy a previous commit:

```bash
# In CI or locally with the same variables:
BACKEND_IMAGE=registry.gitlab.com/<ns>/insight-ops/backend:<previous-sha> \
  ./deploy/deploy_ec2.sh
```

Redis aggregation state is ephemeral (TTL); CloudWatch logs are the
persistent record, so rollback loses no observability history.

## Security notes (Phase 19)

- Secrets live only in GitLab CI/CD variables; `.env.prod` is created on
  the host by the deploy script and never committed.
- The instance IAM role is scoped to CloudWatch logs for the app log group.
- SSH and the API port are open per the `RunnerIp`/`CloudFrontAccessIp`
  parameters — restrict them to your runner/IPs in production.
- Production hardening would front the API with ALB/TLS and require auth on
  the dashboard; see PROJECT_PLAN Phase 19.
