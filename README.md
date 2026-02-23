# hippo-hello-world

A production-ready Flask hello-world service with Prometheus metrics, Kubernetes health probes, and a GitOps-based CD pipeline via ArgoCD.

## Features

- `GET /` — Returns `{"message": "Hello, World!"}`
- `GET /health` — Kubernetes liveness probe
- `GET /ready` — Kubernetes readiness probe (returns 503 during startup/shutdown)
- `GET /metrics` — Prometheus metrics endpoint

**Prometheus metrics (golden signals):**
- `http_requests_total` — request counter (method, endpoint, status)
- `http_request_duration_seconds` — request latency histogram
- `http_requests_in_progress` — concurrent request gauge
- `app_uptime_seconds` — seconds since process start
- `app_ready` — readiness state (0/1)

## Project Structure

```
.
├── app/
│   ├── main.py              # Flask application
│   └── requirements.txt     # Python dependencies
├── tests/
│   └── unit/
│       └── test_app.py      # Unit tests
├── service-settings/        # GitOps/ArgoCD deployment config
│   ├── components-manifest.yml
│   ├── default/values.yml   # Dev/staging Helm values
│   └── overrides/values.yml # Production Helm overrides
├── .github/workflows/
│   ├── ci.yml               # Lint, test, and Docker build on PRs and main
│   └── release.yml          # Semantic version releases to GAR
├── Dockerfile               # Multi-stage production image
└── Makefile                 # Build, test, and run targets
```

## Local Development

**Prerequisites:** Python 3.12+ or Docker

### Run with Python

```bash
pip install -r app/requirements.txt
python app/main.py
# Listening on http://localhost:8080
```

### Run with Docker / Make

```bash
make build   # Build Docker image
make run     # Run on http://localhost:8080
make stop    # Stop the container
make clean   # Remove image and Python cache
```

### Run tests

```bash
make test
# or directly:
python -m pytest tests/unit/ -v
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `PORT` | `8080` | Server port |
| `FLASK_DEBUG` | `false` | Flask debug mode |
| `STARTUP_DELAY_SECONDS` | `0` | Simulated startup delay before service becomes ready |
| `APP_ENV` | — | Environment label (`development` / `production`) |

## CI/CD

### CI (`ci.yml`)

Runs on every push to `main` and on pull requests. No GCP credentials required.

1. Lints code with `ruff`
2. Runs unit tests with `pytest`
3. Builds the Docker image to validate the `Dockerfile` (never pushed)

### Release (`release.yml`)

Triggered by pushing a semantic version tag (e.g. `v1.2.3`):

1. Authenticates to GCP via **Workload Identity Federation** (no long-lived keys)
2. Builds and pushes the image to **Google Artifact Registry (GAR)**:
   `<GAR_LOCATION>-docker.pkg.dev/<GAR_PROJECT_ID>/<GAR_REPOSITORY>/hippo-hello-world:<version>`
3. Also tags as `latest`
4. Updates `image_tag` in `service-settings/components-manifest.yml` and commits back to `main` (`[skip ci]`)
5. ArgoCD picks up the manifest change and syncs dev automatically; production requires a manual sync

**To cut a release:**

```bash
git tag v1.2.3
git push origin v1.2.3
```

### Required GitHub Secrets

The release workflow uses Workload Identity Federation. The GCP service account and WIF binding are managed by Terraform in `hippo_cloud`.

| Secret | Value |
|---|---|
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | WIF provider resource name (from `terraform output -raw wif_provider`) |
| `GCP_SERVICE_ACCOUNT` | SA email with `roles/artifactregistry.writer` (from `terraform output github_ci_service_accounts`) |
| `GAR_LOCATION` | e.g. `us-central1` |
| `GAR_PROJECT_ID` | GCP project ID |
| `GAR_REPOSITORY` | AR repository name (e.g. `hippo-images`) |

## Kubernetes Deployment

Deployment is managed via Helm charts configured through ArgoCD ApplicationSet (owned by `hippo_k8s-service`). The `service-settings/` directory provides the values. `components-manifest.yml` is the only file you edit for deployment configuration — the platform reads it automatically.

The container image path is constructed by the platform from the component `name`:
```
<GAR_LOCATION>-docker.pkg.dev/<GAR_PROJECT_ID>/<GAR_REPOSITORY>/hippo-hello-world
```
No `image_repository` field is needed in `components-manifest.yml`.

| Setting | Dev/Staging | Production |
|---|---|---|
| Replicas | 2 | 4 |
| HPA max | 10 | 50 |
| CPU target | 70% | 60% |
| Pod anti-affinity | Soft | Hard |
| PDB min available | 1 | 2 |
| Memory limit | 256Mi | 512Mi |
| Ingress | `hello-dev.hippo.example.com` | `hello.hippo.example.com` |

## Dependencies

```
flask==3.1.0
gunicorn==23.0.0
prometheus-client==0.21.1
```
