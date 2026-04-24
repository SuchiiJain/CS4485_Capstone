const { onRequest } = require("firebase-functions/v2/https");
const { defineSecret } = require("firebase-functions/params");
const admin = require("firebase-admin");

admin.initializeApp();
const db = admin.firestore();

const groqApiKey = defineSecret("GROQ_API_KEY");

const GROQ_MODEL = "llama-3.3-70b-versatile";
const GROQ_MAX_TOKENS = 1024;

/**
 * Call the Groq chat completions API for a single doc's prompts.
 */
async function callGroq(apiKey, systemPrompt, userPrompt) {
  const resp = await fetch("https://api.groq.com/openai/v1/chat/completions", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model: GROQ_MODEL,
      max_tokens: GROQ_MAX_TOKENS,
      messages: [
        { role: "system", content: systemPrompt },
        { role: "user", content: userPrompt },
      ],
    }),
  });

  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`Groq API ${resp.status}: ${text.slice(0, 200)}`);
  }

  const data = await resp.json();
  return data.choices?.[0]?.message?.content || "";
}

/**
 * Process AI context items: call Groq for each flagged doc and return suggestions.
 */
async function generateAiSuggestions(apiKey, aiContext) {
  const suggestions = [];

  for (const item of aiContext) {
    try {
      const suggestionText = await callGroq(
        apiKey,
        item.system_prompt,
        item.user_prompt
      );
      suggestions.push({
        doc_path: item.doc_path,
        triggered_by: item.triggered_by || [],
        suggestion: suggestionText,
        model_used: GROQ_MODEL,
      });
    } catch (err) {
      console.error(`AI suggestion failed for ${item.doc_path}:`, err.message);
      suggestions.push({
        doc_path: item.doc_path,
        triggered_by: item.triggered_by || [],
        suggestion: `(AI suggestion unavailable: ${err.message})`,
        model_used: GROQ_MODEL,
      });
    }
  }

  return suggestions;
}

exports.ingestScan = onRequest(
  {
    region: "us-central1",
    secrets: [groqApiKey],
  },
  async (req, res) => {
    // --- GET: return stored fingerprint baseline ---
    if (req.method === "GET") {
      const repo = req.query.repo;
      const branch = req.query.branch;
      if (!repo || !branch) {
        res.status(400).json({ error: "Missing required query params: repo, branch" });
        return;
      }
      try {
        const repoDocId = repo.replace("/", "_");
        const fpDoc = await db
          .collection("repos").doc(repoDocId)
          .collection("fingerprint_baselines").doc(branch)
          .get();
        if (!fpDoc.exists) {
          res.status(404).json({ error: "No baseline found" });
          return;
        }
        res.status(200).json({ fingerprints: fpDoc.data().fingerprints });
      } catch (error) {
        console.error("getBaseline error:", error);
        res.status(500).json({ error: "Internal server error" });
      }
      return;
    }

    // --- POST: ingest scan results ---
    if (req.method !== "POST") {
      res.status(405).send("Method not allowed");
      return;
    }

    try {
      const payload = req.body;

      if (!payload.repo_name || !payload.scan_id || !payload.commit_hash) {
        res.status(400).json({ error: "Missing required fields: repo_name, scan_id, commit_hash" });
        return;
      }

      // --- AI suggestions (server-side) ---
      let aiSuggestions = [];
      const aiContext = payload.ai_context;
      const apiKey = groqApiKey.value();

      if (aiContext && Array.isArray(aiContext) && aiContext.length > 0 && apiKey) {
        console.log(`Generating AI suggestions for ${aiContext.length} doc(s)...`);
        aiSuggestions = await generateAiSuggestions(apiKey, aiContext);
        console.log(`Generated ${aiSuggestions.length} AI suggestion(s).`);
      }

      // --- Firestore writes ---
      const repoDocId = payload.repo_name.replace("/", "_");
      const batch = db.batch();

      const repoRef = db.collection("repos").doc(repoDocId);
      batch.set(
        repoRef,
        {
          full_name: payload.repo_name,
          github_url: payload.github_url || null,
          first_seen_at: admin.firestore.FieldValue.serverTimestamp(),
          latest_scan_id: payload.scan_id,
        },
        { merge: true }
      );

      const highCount = payload.high_count || 0;
      const mediumCount = payload.medium_count || 0;
      const lowCount = payload.low_count || 0;
      const rotScore = Math.min(100, highCount * 15 + mediumCount * 8 + lowCount * 3);

      const scanRef = repoRef.collection("scan_runs").doc(payload.scan_id);
      batch.set(scanRef, {
        commit_hash: payload.commit_hash,
        branch: payload.branch || null,
        status: payload.status || "unknown",
        scanned_at: admin.firestore.FieldValue.serverTimestamp(),
        total_issues: payload.total_issues || 0,
        high_count: highCount,
        medium_count: mediumCount,
        low_count: lowCount,
        rot_score: rotScore,
      });

      if (payload.flags && Array.isArray(payload.flags)) {
        for (const flag of payload.flags) {
          const flagRef = scanRef.collection("flags").doc();
          batch.set(flagRef, {
            reason: flag.reason,
            severity: flag.severity,
            file_path: flag.file_path || null,
            symbol: flag.symbol || null,
            message: flag.message || null,
            suggestion: flag.suggestion || null,
            signature: flag.signature || null,
            params: flag.params || [],
            return_type: flag.return_type || null,
            doc_file: flag.doc_file || null,
            doc_symbol: flag.doc_symbol || null,
            // Carried through from the scanner so applyFix can update the
            // baseline entry for this single function after a successful PR.
            new_fingerprint: flag.new_fingerprint || null,
            stable_id: flag.stable_id || null,
          });
        }
      }

      // Write AI suggestions to Firestore
      if (aiSuggestions.length > 0) {
        for (const suggestion of aiSuggestions) {
          const sugRef = scanRef.collection("ai_suggestions").doc();
          batch.set(sugRef, {
            doc_path: suggestion.doc_path,
            triggered_by: suggestion.triggered_by,
            suggestion: suggestion.suggestion,
            model_used: suggestion.model_used,
          });
        }
      }

      if (payload.fingerprints && payload.branch) {
        const fpRef = repoRef.collection("fingerprint_baselines").doc(payload.branch);
        batch.set(fpRef, {
          fingerprints: payload.fingerprints,
          updated_at: admin.firestore.FieldValue.serverTimestamp(),
        });
      }

      await batch.commit();

      res.status(200).json({
        success: true,
        scan_id: payload.scan_id,
        flags_written: payload.flags ? payload.flags.length : 0,
        ai_suggestions: aiSuggestions,
      });
    } catch (error) {
      console.error("ingestScan error:", error);
      res.status(500).json({ error: "Internal server error" });
    }
  }
);


// ---------------------------------------------------------------------------
// applyFix — open a pull request on the user's repo that applies a
// deterministic doc patch for a single flag detected by a previous scan.
//
// This is the HTTP-facing counterpart to src/auto_fix.py. The logic is
// intentionally duplicated here (in JS) so that the frontend dashboard
// can trigger a fix without going through the GitHub Action runner.
//
// Request (POST):
//   {
//     repo_id:   "owner_repo"     // Firestore doc id
//     scan_id:   "<uuid>"         // scan that produced the flag
//     flag_id:   "<auto-id>"      // id of the flag document to fix
//     user_token: "<gh-token>"    // user's OAuth token (repo scope)
//     base_branch: "main"         // optional, defaults to repo default
//     dry_run:   false            // optional preview mode
//   }
//
// Response:
//   { success: true, pr_url: "...", branch: "...", summary: "..." }
//   { success: false, error: "..." }
// ---------------------------------------------------------------------------

const SUPPORTED_REASONS = new Set([
  "signature_changed",
  "parameter_added",
  "parameter_removed",
  "parameter_renamed",
  "return_type_changed",
  "symbol_removed",
]);

const GH_API_ROOT = "https://api.github.com";


function sanitizeBranchName(name) {
  const cleaned = (name || "")
    .replace(/[^A-Za-z0-9._/-]+/g, "-")
    .replace(/^[-./]+|[-./]+$/g, "");
  return cleaned || `docrot-fix-${Date.now()}`;
}


function buildBranchName(flagId, symbol) {
  const shortId = (flagId || "fix").slice(0, 8);
  const safeSymbol = sanitizeBranchName(symbol || "doc");
  return sanitizeBranchName(`docrot/fix-${shortId}-${safeSymbol}`);
}


function formatParam(param) {
  const name = param.name || "";
  const annotation = param.annotation || param.type;
  const hasDefault =
    Object.prototype.hasOwnProperty.call(param, "default") &&
    param.default !== null &&
    param.default !== "";
  let rendered = name;
  if (annotation) rendered = `${rendered}: ${annotation}`;
  if (hasDefault) rendered = `${rendered} = ${param.default}`;
  return rendered;
}


function buildSignatureLine(symbol, params, returnType) {
  const rendered = (params || [])
    .filter((p) => p && p.name)
    .map(formatParam)
    .join(", ");
  let header = `def ${symbol}(${rendered})`;
  if (returnType) header = `${header} -> ${returnType}`;
  return `${header}:`;
}


function fallbackSignature(flag) {
  const sig = flag.signature;
  if (sig && typeof sig === "string") {
    const trimmed = sig.trim();
    if (trimmed.startsWith("def ")) {
      return trimmed.endsWith(":") ? trimmed : `${trimmed}:`;
    }
  }
  if (!flag.symbol) return null;
  return buildSignatureLine(
    flag.symbol,
    flag.params || [],
    flag.return_type || null,
  );
}


function replaceSignatureInPythonBlocks(content, symbol, newSignatureLine) {
  const fenceRe = /```([a-zA-Z0-9_+-]*)\s*\n([\s\S]*?)\n```/g;
  const sigRe = new RegExp(
    `(?:async\\s+)?def\\s+${escapeRegExp(symbol)}\\s*\\([^)]*\\)(?:\\s*->\\s*[^:\\n]+)?\\s*:?`,
    "gm",
  );

  let total = 0;
  const rebuilt = content.replace(fenceRe, (full, lang, body) => {
    const isPython = !lang || /^(python|py)$/i.test(lang);
    if (!isPython) return full;
    const next = body.replace(sigRe, () => {
      total += 1;
      return newSignatureLine;
    });
    return full.replace(body, next);
  });
  return { content: rebuilt, count: total };
}


function annotateProseMentions(content, symbol, note) {
  const lines = content.split("\n");
  const mentionRe = new RegExp(
    "`" + escapeRegExp(symbol) + "(?:\\([^`)]*\\))?`",
  );
  let inFence = false;
  let count = 0;
  for (let i = 0; i < lines.length; i += 1) {
    const line = lines[i];
    if (line.trimStart().startsWith("```")) {
      inFence = !inFence;
      continue;
    }
    if (inFence) continue;
    if (mentionRe.test(line)) {
      lines[i] = `${line}  <!-- docrot: ${note} -->`;
      count += 1;
    }
  }
  return { content: lines.join("\n"), count };
}


function escapeRegExp(str) {
  return String(str).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}


function generatePatch(flag, docContent) {
  const reason = flag.reason;
  const symbol = flag.symbol;
  const docPath = flag.doc_file;
  if (!reason || !symbol || !docPath) return null;
  if (!SUPPORTED_REASONS.has(reason)) return null;

  const newSignature = fallbackSignature(flag);
  let patched = docContent;
  const todo = [];
  const summary = [];

  if (reason === "signature_changed") {
    if (!newSignature) return null;
    const result = replaceSignatureInPythonBlocks(patched, symbol, newSignature);
    if (result.count === 0) return null;
    patched = result.content;
    summary.push(
      `Updated signature for \`${symbol}\` in ${result.count} code block(s).`,
    );
  } else if (
    reason === "parameter_added" ||
    reason === "parameter_removed" ||
    reason === "parameter_renamed"
  ) {
    if (!newSignature) return null;
    const result = replaceSignatureInPythonBlocks(patched, symbol, newSignature);
    patched = result.content;
    if (result.count > 0) {
      summary.push(
        `Updated signature in ${result.count} code block(s) for \`${symbol}\`.`,
      );
    }
    if (reason === "parameter_removed" && flag.removed_param) {
      const annotated = annotateProseMentions(
        patched,
        flag.removed_param,
        `parameter \`${flag.removed_param}\` was removed from \`${symbol}\``,
      );
      patched = annotated.content;
      if (annotated.count > 0) {
        todo.push(
          `Annotated ${annotated.count} prose mention(s) of removed parameter \`${flag.removed_param}\`.`,
        );
      }
    }
    if (patched === docContent) return null;
  } else if (reason === "return_type_changed") {
    if (!newSignature) return null;
    const result = replaceSignatureInPythonBlocks(patched, symbol, newSignature);
    patched = result.content;
    if (result.count > 0) {
      summary.push(
        `Updated return type in ${result.count} code block(s) for \`${symbol}\`.`,
      );
    }
    if (flag.return_type) {
      const annotated = annotateProseMentions(
        patched,
        symbol,
        `return type for \`${symbol}\` is now \`${flag.return_type}\``,
      );
      patched = annotated.content;
      if (annotated.count > 0) {
        todo.push(
          `Annotated ${annotated.count} prose reference(s) describing the old return type.`,
        );
      }
    }
    if (patched === docContent) return null;
  } else if (reason === "symbol_removed") {
    const annotated = annotateProseMentions(
      patched,
      symbol,
      `removed symbol \`${symbol}\` — consider deleting this section`,
    );
    if (annotated.count === 0) return null;
    patched = annotated.content;
    todo.push(
      `Annotated ${annotated.count} prose reference(s) to removed symbol \`${symbol}\`.`,
    );
  } else {
    return null;
  }

  if (summary.length === 0) {
    summary.push(`Applied \`${reason}\` fix for \`${symbol}\`.`);
  }

  return {
    docPath,
    reason,
    symbol,
    originalContent: docContent,
    patchedContent: patched,
    summary: summary.join(" "),
    todoNotes: todo,
  };
}


// -------- GitHub REST helpers (token-scoped) -------------------------------


async function ghRequest(token, method, path, body) {
  const resp = await fetch(`${GH_API_ROOT}${path}`, {
    method,
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
      "User-Agent": "docrot-detector",
      "Content-Type": "application/json",
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  let parsed = null;
  const text = await resp.text();
  if (text) {
    try {
      parsed = JSON.parse(text);
    } catch (_) {
      parsed = { raw: text };
    }
  }
  return { status: resp.status, body: parsed };
}


async function ghGetDefaultBranch(token, repo) {
  const { status, body } = await ghRequest(token, "GET", `/repos/${repo}`);
  if (status !== 200) {
    throw new Error(`GET /repos/${repo} → ${status}: ${body && body.message}`);
  }
  return body.default_branch || "main";
}


async function ghGetRefSha(token, repo, branch) {
  const { status, body } = await ghRequest(
    token,
    "GET",
    `/repos/${repo}/git/ref/heads/${branch}`,
  );
  if (status !== 200) {
    throw new Error(
      `GET ref heads/${branch} → ${status}: ${body && body.message}`,
    );
  }
  return body.object.sha;
}


async function ghBranchExists(token, repo, branch) {
  const { status } = await ghRequest(
    token,
    "GET",
    `/repos/${repo}/git/ref/heads/${branch}`,
  );
  return status === 200;
}


async function ghEnsureBranch(token, repo, base, newBranch) {
  if (await ghBranchExists(token, repo, newBranch)) return;
  const baseSha = await ghGetRefSha(token, repo, base);
  const { status, body } = await ghRequest(token, "POST", `/repos/${repo}/git/refs`, {
    ref: `refs/heads/${newBranch}`,
    sha: baseSha,
  });
  if (status >= 300) {
    throw new Error(
      `create ref ${newBranch} → ${status}: ${body && body.message}`,
    );
  }
}


async function ghGetFile(token, repo, path, ref) {
  const { status, body } = await ghRequest(
    token,
    "GET",
    `/repos/${repo}/contents/${path}?ref=${encodeURIComponent(ref)}`,
  );
  if (status !== 200) {
    throw new Error(
      `GET contents/${path}@${ref} → ${status}: ${body && body.message}`,
    );
  }
  const decoded = Buffer.from(body.content || "", body.encoding || "base64").toString(
    "utf-8",
  );
  return { path: body.path, content: decoded, sha: body.sha };
}


async function ghUpdateFile(token, repo, path, content, branch, message, sha) {
  const encoded = Buffer.from(content, "utf-8").toString("base64");
  const { status, body } = await ghRequest(
    token,
    "PUT",
    `/repos/${repo}/contents/${path}`,
    { message, content: encoded, branch, sha },
  );
  if (status >= 300) {
    throw new Error(
      `PUT contents/${path}@${branch} → ${status}: ${body && body.message}`,
    );
  }
  return body;
}


async function ghFindOpenPr(token, repo, headBranch) {
  const owner = repo.split("/")[0];
  const { status, body } = await ghRequest(
    token,
    "GET",
    `/repos/${repo}/pulls?head=${encodeURIComponent(`${owner}:${headBranch}`)}&state=open`,
  );
  if (status !== 200) return null;
  if (Array.isArray(body) && body.length > 0) return body[0];
  return null;
}


async function ghCreatePr(token, repo, base, head, title, body) {
  const { status, body: resBody } = await ghRequest(
    token,
    "POST",
    `/repos/${repo}/pulls`,
    { base, head, title, body },
  );
  if (status >= 300) {
    throw new Error(
      `POST pulls → ${status}: ${resBody && resBody.message}`,
    );
  }
  return resBody;
}


function buildPrBody(patch, flag, commitHash) {
  const lines = [
    "This pull request was generated automatically by **Docrot Detector**.",
    "",
    "### Change detected",
    `- **Reason:** \`${patch.reason}\``,
    `- **Symbol:** \`${patch.symbol}\``,
    `- **Source file:** \`${flag.file_path || "(unknown)"}\``,
    `- **Doc file:** \`${patch.docPath}\``,
  ];
  if (commitHash) {
    lines.push(`- **Detected on commit:** \`${String(commitHash).slice(0, 8)}\``);
  }
  lines.push("", "### What changed", `- ${patch.summary}`, "");
  if (patch.todoNotes && patch.todoNotes.length) {
    lines.push("### Reviewer notes");
    for (const note of patch.todoNotes) lines.push(`- ${note}`);
    lines.push("");
  }
  lines.push(
    "### How to review",
    "- This patch was produced with deterministic rules on the structural diff of the flagged symbol.",
    "- AI was not used to generate the diff; edit the branch before merging if needed.",
  );
  return lines.join("\n");
}


exports.applyFix = onRequest({ cors: true }, async (req, res) => {
  if (req.method === "OPTIONS") {
    res.status(204).send("");
    return;
  }
  if (req.method !== "POST") {
    res.status(405).json({ error: "Use POST." });
    return;
  }

  const body = req.body || {};
  const { repo_id: repoId, scan_id: scanId, flag_id: flagId } = body;
  const userToken = body.user_token || "";
  const dryRun = body.dry_run === true;
  const requestedBase = body.base_branch || null;

  if (!repoId || !scanId || !flagId) {
    res.status(400).json({ error: "repo_id, scan_id, flag_id are required." });
    return;
  }
  if (!dryRun && !userToken) {
    res.status(401).json({
      error:
        "user_token is required. Ask the user to sign in with the `repo` scope.",
    });
    return;
  }

  try {
    const flagRef = db
      .collection("repos").doc(repoId)
      .collection("scan_runs").doc(scanId)
      .collection("flags").doc(flagId);
    const flagSnap = await flagRef.get();
    if (!flagSnap.exists) {
      res.status(404).json({ error: "Flag not found in Firestore." });
      return;
    }
    const flag = flagSnap.data();
    const docPath = flag.doc_file;
    if (!docPath) {
      res.status(422).json({
        error: "Flag has no doc_file; nothing to patch.",
      });
      return;
    }

    const scanSnap = await db
      .collection("repos").doc(repoId)
      .collection("scan_runs").doc(scanId)
      .get();
    const scan = scanSnap.exists ? scanSnap.data() : {};
    const repoFullName = (scan.repo_name || repoId.replace("_", "/"));
    const commitHash = scan.commit_hash || null;

    const baseBranch = requestedBase || (await ghGetDefaultBranch(userToken, repoFullName));
    const currentFile = await ghGetFile(userToken, repoFullName, docPath, baseBranch);

    const patch = generatePatch(flag, currentFile.content);
    if (!patch) {
      res.status(422).json({
        error:
          `Flag reason \`${flag.reason}\` is not handled by the deterministic patch generator.`,
      });
      return;
    }
    if (patch.patchedContent === patch.originalContent) {
      res.status(422).json({
        error: "Patch produced no changes against the current doc content.",
      });
      return;
    }

    if (dryRun) {
      res.status(200).json({
        success: true,
        dry_run: true,
        doc_path: patch.docPath,
        reason: patch.reason,
        summary: patch.summary,
        todo_notes: patch.todoNotes,
        patched_preview: patch.patchedContent,
      });
      return;
    }

    const branchName = buildBranchName(flagId, patch.symbol);
    await ghEnsureBranch(userToken, repoFullName, baseBranch, branchName);
    await ghUpdateFile(
      userToken,
      repoFullName,
      docPath,
      patch.patchedContent,
      branchName,
      `docrot: update \`${docPath}\` for \`${patch.symbol}\``,
      currentFile.sha,
    );

    const existing = await ghFindOpenPr(userToken, repoFullName, branchName);
    let pr;
    if (existing) {
      pr = existing;
    } else {
      pr = await ghCreatePr(
        userToken,
        repoFullName,
        baseBranch,
        branchName,
        `Docrot: update docs for \`${patch.symbol}\` (${patch.reason})`,
        buildPrBody(patch, flag, commitHash),
      );
    }

    await flagRef.update({
      auto_fix_status: "pr_opened",
      auto_fix_pr_url: pr.html_url || null,
      auto_fix_pr_number: pr.number || null,
      auto_fix_branch: branchName,
      auto_fix_applied_at: admin.firestore.FieldValue.serverTimestamp(),
    });

    // Targeted baseline update: replace the OLD (preserved) fingerprint for
    // THIS one function with the fresh one the scanner captured at flag
    // time. On the next scan, the function no longer drifts from baseline,
    // so the flag naturally clears — no blanket reset, no other entries
    // touched. CS4485-69's preservation logic is untouched for every other
    // function. Wrapped so any failure here does not fail the PR response.
    let baselineUpdated = false;
    let baselineSkipReason = null;
    try {
      const newFingerprint = flag.new_fingerprint;
      const stableId = flag.stable_id;
      const baselineFile = flag.file_path;
      const baselineBranch = scan.branch || baseBranch;
      if (!newFingerprint || !stableId || !baselineFile) {
        baselineSkipReason = "flag missing new_fingerprint/stable_id/file_path";
      } else if (!baselineBranch) {
        baselineSkipReason = "scan has no branch recorded";
      } else {
        const baselineRef = db
          .collection("repos").doc(repoId)
          .collection("fingerprint_baselines").doc(baselineBranch);
        const baselineSnap = await baselineRef.get();
        if (!baselineSnap.exists) {
          baselineSkipReason = `no baseline at fingerprint_baselines/${baselineBranch}`;
        } else {
          // FieldPath segments are treated literally — dots in baselineFile
          // (e.g. "src/task_manager.py") are NOT parsed as path separators.
          await baselineRef.update(
            new admin.firestore.FieldPath("fingerprints", baselineFile, stableId),
            newFingerprint,
            "updated_at",
            admin.firestore.FieldValue.serverTimestamp(),
          );
          await flagRef.update({ auto_fix_baseline_updated: true });
          baselineUpdated = true;
          console.log(
            `applyFix: baseline updated for ${baselineFile}::${stableId} ` +
            `on branch ${baselineBranch} (repo ${repoId})`,
          );
        }
      }
    } catch (baselineErr) {
      console.error("applyFix baseline update failed:", baselineErr);
      baselineSkipReason = baselineErr.message || "baseline update error";
    }
    if (!baselineUpdated && baselineSkipReason) {
      console.log(`applyFix: baseline not updated — ${baselineSkipReason}`);
    }

    res.status(200).json({
      success: true,
      pr_url: pr.html_url,
      pr_number: pr.number,
      branch: branchName,
      doc_path: patch.docPath,
      summary: patch.summary,
      todo_notes: patch.todoNotes,
      baseline_updated: baselineUpdated,
    });
  } catch (error) {
    console.error("applyFix error:", error);
    res.status(500).json({
      error: (error && error.message) || "Internal server error",
    });
  }
});
