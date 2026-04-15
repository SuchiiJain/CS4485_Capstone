#!/usr/bin/env node

const fs = require("node:fs");
const path = require("node:path");
const readline = require("node:readline/promises");
const { stdin, stdout } = require("node:process");

const argv = process.argv.slice(2);

function hasFlag(name) {
  return argv.includes(name);
}

function getArgValue(name) {
  const index = argv.indexOf(name);
  if (index === -1) {
    return undefined;
  }
  return argv[index + 1];
}

function parseBool(value, defaultValue) {
  if (value === undefined || value === null || value === "") {
    return defaultValue;
  }
  const normalized = String(value).trim().toLowerCase();
  if (["1", "true", "yes", "y"].includes(normalized)) {
    return true;
  }
  if (["0", "false", "no", "n"].includes(normalized)) {
    return false;
  }
  return defaultValue;
}

async function ask(rl, question, defaultValue) {
  const suffix = defaultValue ? ` (${defaultValue})` : "";
  const answer = await rl.question(`${question}${suffix}: `);
  const trimmed = answer.trim();
  return trimmed || defaultValue || "";
}

function ensureParentDir(filePath) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
}

function writeFileSafely(filePath, content, force) {
  if (fs.existsSync(filePath) && !force) {
    return { wrote: false, reason: "exists" };
  }
  ensureParentDir(filePath);
  fs.writeFileSync(filePath, content, "utf8");
  return { wrote: true };
}

function buildConfigJson(sourceGlob, docs, withAi) {
  const parsedDocs = docs
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);

  const config = {
    language: "python",
    doc_mappings: [
      {
        code_glob: sourceGlob,
        docs: parsedDocs.length > 0 ? parsedDocs : ["Readme.md", "docs/Architecture.md"],
      },
    ],
    thresholds: {
      per_function_substantial: 4,
      per_doc_cumulative: 8,
    },
  };

  if (withAi) {
    config.ai = {
      provider: "groq",
      model: "llama-3.3-70b-versatile",
      api_key_env: "GROQ_API_KEY",
    };
  }

  return `${JSON.stringify(config, null, 2)}\n`;
}

function buildWorkflowYaml(options) {
  const {
    actionRef,
    defaultBranch,
    createIssue,
    repoPath,
    withBackend,
  } = options;

  const backendBlock = withBackend
    ? `
      - name: Authenticate to Google Cloud
        id: auth
        uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: projects/YOUR_PROJECT_NUMBER/locations/global/workloadIdentityPools/docrot-github-pool/providers/github-provider
          service_account: docrot-github-action@YOUR_FIREBASE_PROJECT_ID.iam.gserviceaccount.com
          token_format: id_token
          id_token_audience: https://YOUR_CLOUD_FUNCTION_URL
          id_token_include_email: true
`
    : "";

  const backendInputs = withBackend
    ? `
          backend_url: https://YOUR_CLOUD_FUNCTION_URL
          backend_token: \${{ steps.auth.outputs.id_token }}`
    : "";

  return `name: docrot

on:
  push:
    branches: ["${defaultBranch}"]
  pull_request:
    branches: ["${defaultBranch}"]

jobs:
  docrot:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      issues: write
      id-token: write
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0${backendBlock}
      - name: Run Docrot Detector
        uses: ${actionRef}
        with:
          repo_path: ${repoPath}
          create_issue: "${createIssue}"${backendInputs}
`;
}

async function run() {
  const cwd = process.cwd();
  const yesMode = hasFlag("--yes") || hasFlag("-y");
  const force = hasFlag("--force");

  let actionRef = getArgValue("--action") || "SuchiiJain/CS4485_Capstone@main";
  let defaultBranch = getArgValue("--branch") || "main";
  let sourceGlob = getArgValue("--code-glob") || "src/*.py";
  let docs = getArgValue("--docs") || "Readme.md,docs/Architecture.md";
  let repoPath = getArgValue("--repo-path") || ".";
  let createIssue = parseBool(getArgValue("--create-issue"), true);
  let withBackend = parseBool(getArgValue("--with-backend"), false);
  let withAi = parseBool(getArgValue("--with-ai"), false);

  if (!yesMode) {
    const rl = readline.createInterface({ input: stdin, output: stdout });

    stdout.write("\nDocrot Setup Wizard\n");
    stdout.write("This will create .docrot-config.json and .github/workflows/docrot.yml in the current repository.\n\n");

    actionRef = await ask(rl, "Action reference (owner/repo@ref)", actionRef);
    defaultBranch = await ask(rl, "Default branch", defaultBranch);
    sourceGlob = await ask(rl, "Code glob for mapping", sourceGlob);
    docs = await ask(rl, "Docs list (comma separated)", docs);
    repoPath = await ask(rl, "Repository scan path", repoPath);
    createIssue = parseBool(await ask(rl, "Create GitHub issue (true/false)", String(createIssue)), createIssue);
    withBackend = parseBool(await ask(rl, "Enable Firebase backend block (true/false)", String(withBackend)), withBackend);
    withAi = parseBool(await ask(rl, "Include AI config block (true/false)", String(withAi)), withAi);

    rl.close();
  }

  const configPath = path.join(cwd, ".docrot-config.json");
  const workflowPath = path.join(cwd, ".github", "workflows", "docrot.yml");

  const configContent = buildConfigJson(sourceGlob, docs, withAi);
  const workflowContent = buildWorkflowYaml({
    actionRef,
    defaultBranch,
    createIssue,
    repoPath,
    withBackend,
  });

  const configResult = writeFileSafely(configPath, configContent, force);
  const workflowResult = writeFileSafely(workflowPath, workflowContent, force);

  stdout.write("\nSetup results:\n");
  stdout.write(`- ${configPath}: ${configResult.wrote ? "written" : "skipped (already exists, use --force to overwrite)"}\n`);
  stdout.write(`- ${workflowPath}: ${workflowResult.wrote ? "written" : "skipped (already exists, use --force to overwrite)"}\n`);

  stdout.write("\nNext steps:\n");
  stdout.write("1) Review generated files and adjust doc mappings.\n");
  if (withBackend) {
    stdout.write("2) Replace Cloud Function placeholders in workflow and configure GitHub OIDC/WIF.\n");
    stdout.write("3) Commit and push to trigger the first scan.\n\n");
  } else {
    stdout.write("2) Commit and push to trigger the first scan.\n\n");
  }
}

run().catch((error) => {
  console.error("Docrot setup failed:", error.message);
  process.exit(1);
});