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
- Optionally generates AI-powered documentation fix suggestions via LLM.

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

4. Suggest (optional)
- If AI is configured, sends flagged docs + change context to an LLM.
- LLM returns specific, actionable edits for each stale doc.

5. Report
- Generates machine and human readable report artifacts.
- Includes AI suggestions in reports and GitHub issues when available.

6. Persist
- Action sends payload to Cloud Function endpoint.
- Cloud Function writes scan, flags, AI suggestions, and fingerprint baseline to Firestore.

## Repository Components

Core Python pipeline:
- action_entrypoint.py: Action runtime orchestration, issue handling, backend POST.
- src/run.py: Main scan pipeline for repository-level analysis.
- src/ast_parser.py: AST parsing and function extraction.
- src/fingerprint.py: Semantic feature extraction and fingerprinting.
- src/comparator.py: Fingerprint comparison and scoring.
- src/alerts.py: Doc mapping and threshold alert evaluation.
- src/ai_suggestions.py: Optional LLM-powered documentation fix suggestions.
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
- ai_suggestions array (when AI is configured)
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

## Zero-Manual Setup Wizard (npm)

If you want users to avoid manually creating `.github/workflows/docrot.yml` and `.docrot-config.json`, use the setup wizard CLI.

### Option A: One-time run with npx (recommended)

```bash
npx github:SuchiiJain/CS4485_Capstone
```

The wizard asks a few questions, then writes:

- `.docrot-config.json`
- `.github/workflows/docrot.yml`

### Option B: Install then run

```bash
npm install --save-dev github:SuchiiJain/CS4485_Capstone
npx docrot-init
```

### Non-interactive mode (CI/bootstrap scripts)

```bash
npx github:SuchiiJain/CS4485_Capstone --yes --code-glob "src/*.py" --docs "Readme.md,docs/Architecture.md"
```

Useful flags:

- `--yes` / `-y`: skip prompts and use defaults
- `--force`: overwrite existing generated files

Always-on behavior:

- The wizard always includes backend wiring (`backend_url` + `backend_token`) in workflow output.
- The wizard always includes the AI block in `.docrot-config.json` output.
- The wizard always generates `.github/workflows/docrot.yml` from one fixed template (push trigger + Google auth + `uses: ./`).

## 1) Clone and install Python dependencies

```bash
git clone <your-repo-url>
cd CS4485_Capstone
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## GitHub Action (Recommended)

Use this Action from any other repository by adding one workflow file and one config file. For Firebase/Firestore persistence, use GitHub OIDC + Google Workload Identity Federation (WIF).

### Step 1: Add .docrot-config.json to the Target Repository
## 2) Create Docrot config in target repository

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
From functions directory:

```bash
cd functions
npm install
# deploy with your Firebase/GCP settings
```

## AI-Powered Suggestions

When the scan finds documentation that may be stale, Docrot can automatically generate AI-powered fix suggestions that tell you exactly what to update. AI suggestions are **enabled by default** — no configuration required.

### How It Works

1. The scan pipeline detects code changes and flags documentation files that may be out of date.
2. For each flagged doc, the pipeline builds a prompt containing the doc's current content and a description of what changed in the code.
3. The Action sends this context to the Cloud Function backend as part of the scan payload.
4. The Cloud Function calls the Groq API (Llama 3.3 70B) using an API key stored as a Google Cloud secret.
5. The LLM returns specific, actionable edits (quoting existing text and providing corrected versions).
6. Suggestions are written to Firestore and returned to the Action for inclusion in the GitHub issue.

### Where Suggestions Appear

- **GitHub Issue**: AI suggestions appear in a collapsible section on the docrot tracking issue, one per flagged doc.
- **Firestore**: Stored in `scan_runs/{scan_id}/ai_suggestions/` for the frontend dashboard.
- **Report files**: Included in `.docrot-report.json` when generated locally with an API key.

### Configuration Options

AI behavior is controlled through the `ai` field in `.docrot-config.json`. There are three modes:

**1. Default (no `ai` field) — server-side suggestions enabled**

If your config has no `ai` field at all, AI suggestions are generated automatically by the Cloud Function backend. This is the default and requires no setup from the user.

```json
{
  "language": "python",
  "doc_mappings": [
    {
      "code_glob": "src/*.py",
      "docs": ["README.md", "docs/Architecture.md"]
    }
  ],
  "thresholds": {
    "per_function_substantial": 4,
    "per_doc_cumulative": 8
  }
}
```

**2. Opt out — disable AI suggestions entirely**

Set `"ai": false` to disable all AI suggestions. No LLM calls will be made, and no suggestion context will be sent to the backend.

```json
{
  "language": "python",
  "doc_mappings": [...],
  "thresholds": {...},
  "ai": false
}
```

**3. Custom provider — bring your own API key**

If you want to use your own LLM provider instead of (or in addition to) the default Groq backend, add a full `ai` configuration block. This runs the LLM call locally during the scan, before results are sent to the backend.

```json
{
  "language": "python",
  "doc_mappings": [...],
  "thresholds": {...},
  "ai": {
    "provider": "anthropic",
    "model": "claude-sonnet-4-20250514",
    "api_key_env": "ANTHROPIC_API_KEY"
  }
}
```

Supported providers: `groq`, `anthropic`, `openai`.

For local development, install the provider package and set the environment variable:

```bash
pip install anthropic  # or: pip install groq / pip install openai
export ANTHROPIC_API_KEY=your_key_here
```

To use a custom provider in the GitHub Action, add the API key as a repository secret (Settings > Secrets and variables > Actions) and pass it through in your workflow:

```yaml
- uses: SuchiiJain/CS4485_Capstone@main
  env:
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
  with:
    firebase_service_account: ${{ secrets.FIREBASE_SERVICE_ACCOUNT }}
```

When a custom provider is configured with a valid API key, local suggestions are generated during the scan and included in the report files. Server-side suggestions from the Cloud Function backend are also generated independently and appear on the GitHub issue.

## Outputs and Behavior

Pipeline result behavior:
- First run creates baseline with no alerts.
- Subsequent runs compare against baseline and generate findings.

Action behavior:
- Can create or update a tracking issue when findings are present.
- Can close the issue when scan returns clean.
- Sends scan payload to Firebase backend if backend_url is set.

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

- **Language:** Python only (uses the built-in `ast` module).
- **Trigger:** GitHub Action on push events.
- **Storage:** Firestore via Cloud Function. Local baseline in `.docrot-fingerprints.json`.
- **Output:** `.docrot-report.json` + `.docrot-report.txt` + GitHub issue automation + optional AI suggestions.

- Current MVP scope: Python semantic fingerprinting and documentation-rot detection.
- Why: Python-first delivery lets us validate scoring, mapping, and CI workflow reliability quickly.

For GTM and deployment strategy, the long-term goal is broad language compatibility.

- Target direction: expand the detection pipeline to support additional major languages.
- GTM intent: position Docrot as a language-agnostic documentation freshness platform over time.
