# CI/CD Pipeline Documentation

## Overview

This project uses GitHub Actions to automate testing, code quality checks, and deployment. The pipeline ensures code quality, security, and reliability across the DermaAI CKPA codebase.

## Workflows

### 1. Backend Tests (`backend-tests.yml`)

**Triggers:**
- Push to `main` or `develop` branches (when backend files change)
- Pull requests to `main` or `develop` branches (when backend files change)

**Matrix Testing:**
- Python versions: 3.9, 3.10, 3.11

**Jobs:**
- **Linting (Ruff)**: Checks code style and potential bugs
- **Format Check (Black)**: Ensures consistent code formatting
- **Type Checking (mypy)**: Validates Python type hints
- **Testing (pytest)**: Runs unit tests with coverage reporting
- **Coverage Upload**: Sends coverage reports to Codecov

**Example:** Push changes to `backend/app/` → All tests run automatically

---

### 2. Frontend Tests (`frontend-tests.yml`)

**Triggers:**
- Push to `main` or `develop` branches (when frontend files change)
- Pull requests to `main` or `develop` branches (when frontend files change)

**Matrix Testing:**
- Node versions: 18.x, 20.x

**Jobs:**
- **Install & Build**: Installs dependencies and runs `npm run build`
- **Artifact Upload**: Stores build artifacts for inspection

**Example:** Update React components → Frontend builds on Node 18 and 20

---

### 3. Code Quality (`code-quality.yml`)

**Triggers:**
- Push to `main` or `develop`
- All pull requests

**Jobs:**
- **Security Scan (Trivy)**: Scans filesystem for vulnerabilities
- **Python Dependency Check**: Checks for known vulnerabilities with `safety`
- **Node Dependency Check**: Checks npm packages with `npm audit`

**Note:** Dependency checks run with `continue-on-error: true` to report issues without failing

---

### 4. Integration Tests (`integration-tests.yml`)

**Triggers:**
- Push to `main` or `develop`
- All pull requests

**Services:**
- Redis (for caching/session support)

**Jobs:**
- Sets up both backend (Python 3.11) and frontend (Node 20.x)
- Starts backend server and tests health endpoint
- Builds frontend and verifies output
- Ensures backend and frontend work together

**Example:** Tests that the backend API responds and frontend builds successfully

---

### 5. Release & Deploy (`release.yml`)

**Triggers:**
- Push to `main` branch
- Tag creation (v*)

**Jobs:**
- **Build & Push**: Creates Docker images and pushes to GitHub Container Registry (GHCR)
- **Create Release**: Generates GitHub release notes when a tag is created

**Docker Image:**
- Built from `backend/Dockerfile`
- Tagged with commit SHA and semantic version
- Pushed to `ghcr.io/{owner}/backend:{tag}`

**Example:** Tag commit as `v1.0.0` → Docker image built and pushed, GitHub release created

---

## Quick Reference

### Running Tests Locally

```bash
# Backend tests
cd backend
pytest tests/ -v --cov=app

# Frontend build
cd frontend
npm run build

# Code quality checks
cd backend
ruff check app/
black --check app/
mypy app/
```

### Branch Protection Rules (Recommended)

In GitHub repository settings, configure branch protection for `main`:

```
✓ Require status checks to pass before merging:
  - Backend Tests (Python 3.11)
  - Frontend Tests (Node 20.x)
  - Code Quality
  - Integration Tests
✓ Require code reviews before merging
✓ Require branches to be up to date before merging
```

### Viewing Results

1. Go to **Actions** tab in GitHub repository
2. Select a workflow run
3. View logs for each job
4. Check **Artifacts** for build outputs (frontend/dist)

### Environment Variables & Secrets

For workflows that need API keys or credentials:

1. Go to **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Add secrets (e.g., `ANTHROPIC_API_KEY`, `PINECONE_API_KEY`)
4. Reference in workflows: `${{ secrets.SECRET_NAME }}`

---

## Customization

### Adding Status Badges

Add these to your README.md:

```markdown
[![Backend Tests](https://github.com/{owner}/{repo}/actions/workflows/backend-tests.yml/badge.svg)](https://github.com/{owner}/{repo}/actions)
[![Frontend Tests](https://github.com/{owner}/{repo}/actions/workflows/frontend-tests.yml/badge.svg)](https://github.com/{owner}/{repo}/actions)
[![Code Quality](https://github.com/{owner}/{repo}/actions/workflows/code-quality.yml/badge.svg)](https://github.com/{owner}/{repo}/actions)
```

### Modifying Python Versions

Edit `backend-tests.yml` matrix:

```yaml
strategy:
  matrix:
    python-version: ['3.9', '3.10', '3.11', '3.12']
```

### Modifying Node Versions

Edit `frontend-tests.yml` matrix:

```yaml
strategy:
  matrix:
    node-version: [18.x, 20.x, 22.x]
```

### Adding Deployment Step

To deploy after tests pass, add a step to `release.yml`:

```yaml
- name: Deploy to Production
  run: |
    # Add deployment command here
    # e.g., kubectl apply, serverless deploy, etc.
  env:
    DEPLOY_KEY: ${{ secrets.DEPLOY_KEY }}
```

---

## Troubleshooting

### Tests Fail on PR but Pass Locally

- Ensure Python/Node versions match workflow
- Check `.env` file is set up correctly
- Verify all dependencies in `requirements.txt` or `package.json`

### Docker Build Fails

- Check `backend/Dockerfile` exists and is valid
- Verify all layers can access required files
- View build logs in Actions tab

### Coverage Upload Fails

- Add `coverage.xml` to `.gitignore` (it's auto-generated)
- Ensure pytest-cov is installed
- Codecov token is optional for public repos

---

## Next Steps

1. **Push to GitHub** to trigger workflows
2. **Monitor Actions tab** for results
3. **Configure branch protection** rules
4. **Add status badges** to README
5. **Integrate with Slack/Discord** for notifications (optional)

---

For more details, see:
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Backend README](../backend/README.md)
- [Frontend Setup](../frontend/README.md)
