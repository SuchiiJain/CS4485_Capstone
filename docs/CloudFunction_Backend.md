# Setting Up GitHub OIDC + Workload Identity Federation for Docrot

## Prerequisites

Before starting, you need:

- A Google Cloud project (your Firebase project is the same Google Cloud project)
- The `gcloud` CLI installed
- Owner or Editor access on the Google Cloud project
- Your GitHub org or username

## Overview

```text
GitHub Action (any user's repo)
    |
    | 1. Requests OIDC token from GitHub
    | 2. Exchanges token for short-lived Google credential (via WIF)
    | 3. Calls Cloud Function with that credential
    v
Cloud Function (your Firebase project)
    |
    | 4. Authenticated request verified by Google IAM
    | 5. Writes scan results to Firestore via Admin SDK
    v
Firestore
```

## Part 1: Google Cloud Configuration

1. Log in and set project:

```bash
gcloud auth login
gcloud config set project YOUR_FIREBASE_PROJECT_ID
```

2. Enable APIs:

```bash
gcloud services enable \
  iam.googleapis.com \
  cloudresourcemanager.googleapis.com \
  iamcredentials.googleapis.com \
  sts.googleapis.com \
  cloudfunctions.googleapis.com \
  cloudbuild.googleapis.com \
  run.googleapis.com
```

3. Create service account:

```bash
gcloud iam service-accounts create docrot-github-action \
  --display-name="Docrot GitHub Action" \
  --description="Impersonated by GitHub Actions via WIF to call Cloud Functions" \
  --project=YOUR_FIREBASE_PROJECT_ID
```

4. Create Workload Identity Pool:

```bash
gcloud iam workload-identity-pools create "docrot-github-pool" \
  --project="YOUR_FIREBASE_PROJECT_ID" \
  --location="global" \
  --display-name="Docrot GitHub Actions Pool"
```

5. Create OIDC provider:

```bash
gcloud iam workload-identity-pools providers create-oidc "github-provider" \
  --project="YOUR_FIREBASE_PROJECT_ID" \
  --location="global" \
  --workload-identity-pool="docrot-github-pool" \
  --display-name="GitHub OIDC Provider" \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository,attribute.repository_owner=assertion.repository_owner" \
  --attribute-condition="assertion.repository_owner == 'YOUR_GITHUB_ORG_OR_USERNAME'"
```

6. Get provider resource name:

```bash
gcloud iam workload-identity-pools providers describe "github-provider" \
  --project="YOUR_FIREBASE_PROJECT_ID" \
  --location="global" \
  --workload-identity-pool="docrot-github-pool" \
  --format="value(name)"
```

7. Allow WIF principal to impersonate service account:

```bash
gcloud iam service-accounts add-iam-policy-binding \
  "docrot-github-action@YOUR_FIREBASE_PROJECT_ID.iam.gserviceaccount.com" \
  --project="YOUR_FIREBASE_PROJECT_ID" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/YOUR_PROJECT_NUMBER/locations/global/workloadIdentityPools/docrot-github-pool/attribute.repository_owner/YOUR_GITHUB_ORG_OR_USERNAME"
```

8. Grant service account invoker role:

```bash
gcloud projects add-iam-policy-binding YOUR_FIREBASE_PROJECT_ID \
  --member="serviceAccount:docrot-github-action@YOUR_FIREBASE_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/run.invoker"
```

## Part 2: Deploy the Cloud Function

The function source is in `functions/index.js` and exports `ingestScan`.

Deploy:

```bash
cd functions
npm install

gcloud functions deploy ingestScan \
  --gen2 \
  --runtime=nodejs20 \
  --region=us-central1 \
  --trigger-http \
  --no-allow-unauthenticated \
  --entry-point=ingestScan \
  --project=YOUR_FIREBASE_PROJECT_ID \
  --source=.
```

## Part 3: Workflow YAML

Use this pattern in the consuming repository:

```yaml
name: Docrot Scan

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

permissions:
  contents: read
  id-token: write
  issues: write

jobs:
  scan:
    runs-on: ubuntu-latest
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

      - uses: SuchiiJain/CS4485_Capstone@main
        with:
          backend_url: https://YOUR_CLOUD_FUNCTION_URL
          backend_token: ${{ steps.auth.outputs.id_token }}
```

## Verification

1. Push a commit in a repo with this workflow.
2. Confirm auth step succeeds.
3. Confirm Docrot action sends scan to backend.
4. Confirm Firestore writes under `repos`, `scan_runs`, and nested `flags`/`fingerprint_baselines`.
