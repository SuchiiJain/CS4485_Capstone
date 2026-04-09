# Docrot Detector

Docrot Detector detects potential documentation rot by comparing semantic code behavior across commits. It analyzes Python (for the MVP) source code with AST-based fingerprints, scores behavior-level changes, maps those changes to docs, and reports docs that should be reviewed.

This repository is currently designed around GitHub Actions for automation. We are not using webhook-based execution in the active flow.

## Frontend Dashboard Link

Dashboard URL:
- https://docrot-detector.web.app/


## What This Project Does

Docrot focuses on behavior-aware change detection instead of text-only diffs.

- Parses Python files into semantic fingerprints per function/method.
- Compares old vs new fingerprints from baseline to current scan.
- Scores changes by impact (control flow, side effects, API/signature, exceptions, and more).
- Maps changed code to documentation files via config.
- Emits reports and optional issue automation in GitHub.
- Sends scan results to Firebase Cloud Function for Firestore storage.

## Current Deployment Model

Active model:
- GitHub Action runs on push.
- Composite action executes scanner.
- Scanner sends results to Cloud Function endpoint.
- Cloud Function writes into Firestore.

Not part of active model:
- Webhook-triggered runtime (legacy/experimental modules may exist in repo, but are not used in the current production path).

## High-Level Architecture

1. Trigger
- GitHub push event starts workflow.

2. Scan
- Action runs scanner entrypoint and full Docrot pipeline.

3. Detect
- Pipeline compares semantic fingerprints with stored baseline.

4. Report
- Generates machine and human readable report artifacts.

5. Persist
- Action sends payload to Cloud Function endpoint.
- Cloud Function writes scan, flags, and fingerprint baseline to Firestore.

## Repository Components

Core Python pipeline:
- action_entrypoint.py: Action runtime orchestration, issue handling, backend POST.
- src/run.py: Main scan pipeline for repository-level analysis.
- src/ast_parser.py: AST parsing and function extraction.
- src/fingerprint.py: Semantic feature extraction and fingerprinting.
- src/comparator.py: Fingerprint comparison and scoring.
- src/alerts.py: Doc mapping and threshold alert evaluation.
- src/report_generation.py: .docrot-report.json and .docrot-report.txt generation.
- src/persistence.py: Baseline fingerprint persistence in .docrot-fingerprints.json.

GitHub Action wiring:
- action.yml: Composite action definition and inputs.
- .github/workflows/docrot.yml: Workflow that authenticates to Google Cloud and runs action.

Firebase backend:
- functions/index.js: Cloud Function ingest endpoint writing to Firestore.
- firebase.json + functions/package.json: Firebase/Functions project config.

Optional API/backend modules in repository:
- database/app.py and database/storage.py support a separate Python API path.
- These are not required for GitHub Action -> Firebase ingestion flow.

## How Detection Works

The scanner follows this sequence:

1. Collect source files
- Walk repository and gather .py files (excluding common generated/dependency folders).

2. Build fingerprints
- For each function/method, extract normalized semantic features:
  - signature
  - control flow
  - conditions
  - calls
  - side effects (DB/file/network/auth patterns)
  - exception behavior
  - return behavior

3. Baseline logic
- First run: creates .docrot-fingerprints.json baseline and exits clean.
- Later runs: compares current fingerprints to baseline.

4. Score and classify changes
- Builds change events and severity-oriented flags.
- Identifies critical events and cumulative impact.

5. Map to docs and threshold
- Uses .docrot-config.json doc mappings.
- Flags documentation files when threshold criteria are met.

6. Emit artifacts
- .docrot-report.json
- .docrot-report.txt
- Updated .docrot-fingerprints.json baseline

## Firebase Ingestion Flow

The action sends results to the Cloud Function endpoint using a short-lived OIDC token.

### Request path
- Workflow authenticates with google-github-actions/auth.
- Action receives backend_url and backend_token inputs.
- action_entrypoint.py posts payload to ingestScan.

### Payload content (high level)
- repo metadata
- scan metadata (scan_id, commit, branch, status, timestamp)
- counts (total issues, high/medium/low)
- flags array
- optional fingerprint baseline snapshot

### Firestore write model
Cloud Function writes to:

- repos/{repo_doc_id}
  - metadata, latest scan pointer
- repos/{repo_doc_id}/scan_runs/{scan_id}
  - scan summary and counts
- repos/{repo_doc_id}/scan_runs/{scan_id}/flags/{flag_id}
  - issue-level records
- repos/{repo_doc_id}/fingerprint_baselines/{branch}
  - serialized fingerprint baseline by branch

## Setup

## Prerequisites

- Python 3.10+
- Git
- Node.js 20 (for Cloud Function development/deploy)
- Firebase project / Google Cloud project
- GitHub repository with Actions enabled & setup

## 1) Clone and install Python dependencies

```bash
git clone <your-repo-url>
cd CS4485_Capstone
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

<<<<<<< api-testing
## GitHub Action (Recommended)

Use this Action from any other repository by adding one workflow file and one config file. For Firebase/Firestore persistence, use GitHub OIDC + Google Workload Identity Federation (WIF).

### Step 1: Add .docrot-config.json to the Target Repository
=======
## 2) Create Docrot config in target repository
>>>>>>> main

Create .docrot-config.json in repository root:

```json
{
  "language": "python",
  "doc_mappings": [
    {
      "code_glob": "src/*.py",
      "docs": ["Readme.md", "docs/Architecture.md"]
    }
  ],
  "thresholds": {
    "per_function_substantial": 4,
    "per_doc_cumulative": 8
  }
}
```

## 4) Configure GitHub Action workflow

Use .github/workflows/docrot.yml as the automation entry.

Key parts:
- Checkout repository with history.
- Authenticate to Google Cloud via OIDC WIF.
- Pass Cloud Function URL and ID token to action inputs.

## 5) Deploy Firebase Cloud Function

<<<<<<< api-testing
jobs:
  docrot:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read
      issues: write
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Authenticate to Google Cloud
        id: auth
        uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: projects/YOUR_PROJECT_NUMBER/locations/global/workloadIdentityPools/docrot-github-pool/providers/github-provider
          service_account: docrot-github-action@YOUR_FIREBASE_PROJECT_ID.iam.gserviceaccount.com
          token_format: id_token
          id_token_audience: https://YOUR_CLOUD_FUNCTION_URL
          id_token_include_email: true

      # Prefer a stable tag (for example: @v1) after release.
      - uses: SuchiiJain/CS4485_Capstone@main
        with:
          backend_url: https://YOUR_CLOUD_FUNCTION_URL
          backend_token: ${{ steps.auth.outputs.id_token }}
```

### Step 3: Push and Verify

On each push, the action will:

1. Scan Python code and generate issue/report output.
2. Create or update a `docrot` issue when docs may be stale.
3. Exchange GitHub OIDC token for a Google-authenticated ID token (WIF step).
4. Send scan payload to your authenticated Cloud Function URL.
5. Let the Cloud Function write scan data to Firestore via Admin SDK.

### Action Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `repo_path` | No | `.` | Path to the repository root to scan |
| `create_issue` | No | `true` | Create/update a GitHub issue when alerts are found |
| `backend_url` | No | `` | Cloud Function URL used for backend ingestion |
| `backend_token` | No | `` | ID token from `google-github-actions/auth@v2` |

The Action uses the default `GITHUB_TOKEN` for GitHub issue operations and supports passing WIF-minted ID tokens for backend calls.
=======
From functions directory:

```bash
cd functions
npm install
# deploy with your Firebase/GCP settings
```

## GitHub Action Inputs

Defined in action.yml:

- repo_path
  - path to repository root to scan (default: .)
- create_issue
  - whether to create/update GitHub issue for findings (default: true)
- backend_url
  - Cloud Function endpoint URL
- backend_token
  - bearer token from google-github-actions/auth id_token output
>>>>>>> main

## Outputs and Behavior

<<<<<<< api-testing
Docrot can also run as a webhook server that automatically scans repos when code is pushed to GitHub.

### Quick Start

```sh
# Install webhook dependencies
pip install -r requirements.txt

# Set your webhook secret
export DOCROT_WEBHOOK_SECRET=$(python -c "import secrets; print(secrets.token_hex(32))")

# (Optional) Set a GitHub token for private repos + commit status posting
export GITHUB_TOKEN=ghp_your_token_here

### Setting Up the GitHub Webhook
=======
Pipeline result behavior:
- First run creates baseline with no alerts.
- Subsequent runs compare against baseline and generate findings.

Action behavior:
- Can create or update a tracking issue when findings are present.
- Can close the issue when scan returns clean.
- Sends scan payload to Firebase backend if backend_url is set.
>>>>>>> main

## Security and Auth Notes

- Use OIDC-based short-lived credentials from GitHub Actions.
- Keep Cloud Function unauthenticated access disabled.
- Restrict Workload Identity provider condition to your org/user scope.

## Troubleshooting

No findings on first run:
- Expected behavior. Baseline initialization run does not alert.

No doc alerts produced:
- Verify .docrot-config.json exists and doc_mappings are correct.

Backend write not happening:
- Confirm backend_url and backend_token are provided.
- Confirm OIDC audience matches Cloud Function URL.
- Check function logs for auth or payload validation failures.

## MVP Scope and Language Roadmap

For the MVP, Docrot is intentionally focused on Python code analysis only.

<<<<<<< api-testing
- **Language:** Python only (uses the built-in `ast` module).
- **Trigger:** GitHub webhook (push events), CI run, or manual invocation.
- **Storage:** JSON file (`.docrot-fingerprints.json`). SQLite planned for post-MVP.
- **Output:** CI log warnings + `.docrot-report.json` artifact + GitHub commit statuses. PR comments planned for post-MVP.

=======
- Current MVP scope: Python semantic fingerprinting and documentation-rot detection.
- Why: Python-first delivery lets us validate scoring, mapping, and CI workflow reliability quickly.
>>>>>>> main

For GTM and deployment strategy, the long-term goal is broad language compatibility.

- Target direction: expand the detection pipeline to support additional major languages.
- GTM intent: position Docrot as a language-agnostic documentation freshness platform over time.
