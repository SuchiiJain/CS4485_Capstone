const { onRequest } = require("firebase-functions/v2/https");
const admin = require("firebase-admin");

admin.initializeApp();
const db = admin.firestore();

exports.ingestScan = onRequest(
  {
    region: "us-central1",
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
          const flagRef = scanRef.collection("flags").doc(flag.id);
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
      });
    } catch (error) {
      console.error("ingestScan error:", error);
      res.status(500).json({ error: "Internal server error" });
    }
  }
);
