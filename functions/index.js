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

      const scanRef = repoRef.collection("scan_runs").doc(payload.scan_id);
      batch.set(scanRef, {
        commit_hash: payload.commit_hash,
        branch: payload.branch || null,
        status: payload.status || "unknown",
        scanned_at: admin.firestore.FieldValue.serverTimestamp(),
        total_issues: payload.total_issues || 0,
        high_count: payload.high_count || 0,
        medium_count: payload.medium_count || 0,
        low_count: payload.low_count || 0,
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
