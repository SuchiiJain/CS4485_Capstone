# Docrot Detector

Docrot Detector identifies documentation rot by detecting semantic code changes, not just text diffs. It parses source code into AST-derived fingerprints, compares behavior across scans, maps impacted code to docs, and flags documentation that should be reviewed.

## Frontend Dashboard

Dashboard URL:
- https://docrot-detector.web.app/

## Active Architecture

Docrot is currently deployed with a GitHub Action + Firebase ingestion flow:

1. A GitHub workflow triggers on push/PR.
2. The Docrot Action scans the repository.
3. The scanner generates report artifacts and baseline updates.
4. The Action posts scan payloads to a Firebase Cloud Function.
5. The Cloud Function writes scan data into Firestore.

Not in active flow:
- Webhook-based runtime execution.

## What Docrot Detects

- Public API/signature changes
- Control flow and condition changes
- Side-effect behavior changes (DB/file/network/auth patterns)
- Exception and return behavior changes
- Cumulative documentation impact via configurable thresholds

## Key Project Files

Core pipeline:
- action_entrypoint.py
- src/run.py
- src/ast_parser.py
- src/fingerprint.py
- src/comparator.py
- src/alerts.py
- src/report_generation.py
- src/persistence.py

Action and workflow:
- action.yml
- .github/workflows/docrot.yml

Firebase backend:
- functions/index.js
- functions/package.json
- firebase.json

## Folder Structure

```
CS4485_Capstone/
├── .github/                  # GitHub Actions workflows
├── MeetingMinutes/           # Meeting notes and weekly status reports
├── database/                 # Database schema and storage layer
├── docs/                     # Architecture, API contract, and proposal docs
├── examples/                 # Sample code and test repositories
├── functions/                # Firebase Cloud Function (ingestScan)
├── src/                      # Core scanner pipeline modules
│   ├── __init__.py
│   ├── alerts.py
│   ├── ast_parser.py
│   ├── comparator.py
│   ├── config.py
│   ├── fingerprint.py
│   ├── flagging_threshold.py
│   ├── github_integration.py
│   ├── models.py
│   ├── persistence.py
│   ├── report_generation.py
│   ├── run.py
│   └── webhook_server.py
├── .docrot-config.json       # Docrot configuration for this repo
├── .firebaserc               # Firebase project config
├── .gitignore
├── Procfile                  # Process file for deployment
├── Readme.md
├── action.yml                # GitHub Action definition
├── action_entrypoint.py      # Entry point for GitHub Action runs
├── firebase.json             # Firebase hosting and functions config
├── requirements.txt          # Python dependencies
└── run.py                    # Root entry script
```

## Setup

### Prerequisites

- Python 3.10+
- Git
- Node.js 20 (for Cloud Function deployment)
- Firebase / Google Cloud project
- GitHub repository with Actions enabled

### 1) Clone and install dependencies

```bash
git clone <your-repo-url>
cd CS4485_Capstone
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2) Add .docrot-config.json

Create .docrot-config.json at the repository root:

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

To enable AI-generated suggestions, add an `"ai"` block:

```json
{
  "language": "python",
  "doc_mappings": [
    {
      "code_glob": "src/*.py",
      "docs": ["README.md"]
    }
  ],
  "thresholds": {
    "per_function_substantial": 4,
    "per_doc_cumulative": 8
  },
  "ai": {
    "provider": "groq",
    "model": "llama-3.3-70b-versatile",
    "api_key_env": "GROQ_API_KEY"
  }
}
```

**Important:** Doc file names in `doc_mappings` are case-sensitive. Use `README.md` not `Readme.md`.

The Groq API key is managed server-side in Google Cloud. Users do not need to supply their own API key. AI responses are saved to Firestore under `repos/{repoId}/scan_runs/{scanId}/ai_suggestions`.

### 3) Required workflow file: .github/workflows/docrot.yml

Use this required workflow in your repository:

```yaml
name: Docrot Detector

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  docrot:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      issues: write
      contents: read
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Authenticate to Google Cloud
        id: auth
        uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: projects/147015144729/locations/global/workloadIdentityPools/github-oidc-pool/providers/github-provider
          service_account: docrot-github-action@docrot-detector.iam.gserviceaccount.com
          token_format: id_token
          id_token_audience: https://us-central1-docrot-detector.cloudfunctions.net/ingestScan
          id_token_include_email: true

      - uses: SuchiiJain/CS4485_Capstone@main
        with:
          backend_url: https://us-central1-docrot-detector.cloudfunctions.net/ingestScan
          backend_token: ${{ steps.auth.outputs.id_token }}
```

Notes:
- For development inside this repository, the local workflow can use `uses: ./`.
- For external repositories, use `uses: SuchiiJain/CS4485_Capstone@main` (or a release tag when available).
- To test the AI integration, point the workflow at `uses: SuchiiJain/CS4485_Capstone@ai-integration`.

### 4) Deploy the Cloud Function

```bash
cd functions
npm install
# deploy with your Firebase/GCP settings
```

## Action Inputs

Defined in action.yml:

- repo_path
  - Path to repository root (default: .)
- create_issue
  - Create/update issue when findings exist (default: true)
- backend_url
  - Cloud Function ingest URL
- backend_token
  - Bearer token from google-github-actions/auth id_token output

## Output Artifacts

- .docrot-fingerprints.json
- .docrot-report.json
- .docrot-report.txt

## Security Notes

- Use OIDC short-lived tokens from GitHub Actions.
- Keep Cloud Function unauthenticated access disabled.
- Restrict Workload Identity conditions to your org/repo scope.

## Troubleshooting

First run has no alerts:
- Expected. First run initializes baseline.

No doc alerts:
- Check .docrot-config.json and doc_mappings.
- Verify doc file names match exactly — they are case-sensitive.

No backend ingestion:
- Verify backend_url and backend_token are passed.
- Verify id_token audience matches Cloud Function URL.
- Check Cloud Function logs for request validation/auth failures.

AI suggestions not appearing:
- Confirm the "ai" block is present in .docrot-config.json.
- Confirm your workflow points to the ai-integration branch or a version that includes AI support.
- Check Firestore under repos/{repoId}/scan_runs/{scanId}/ai_suggestions.

## MVP Scope and Language Roadmap

For MVP, Docrot is intentionally Python-only.

- Current MVP scope: Python semantic fingerprinting and doc-rot detection.
- Reason: Faster validation of scoring quality, mapping accuracy, and CI reliability.

For GTM and deployment strategy, the long-term goal is broad language compatibility.

- Target direction: Expand the analysis engine to support additional major languages.
- GTM intent: Position Docrot as a language-agnostic documentation freshness platform.
