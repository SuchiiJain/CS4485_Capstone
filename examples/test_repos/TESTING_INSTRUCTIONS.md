# Docrot Detector — Test Repository Instructions

These two repos let you verify the full two-run pipeline end-to-end.
Each repo ships with a baseline version of the source code and a
pre-written "v2" version that you swap in for the second run.

---

## Prerequisites

Your project files must be on the Python path. Run all commands from
the folder that contains `run.py` (your project root).

```
your-project/
├── run.py
├── src/
│   ├── alerts.py
│   ├── ast_parser.py
│   ├── comparator.py
│   ├── config.py
│   ├── fingerprint.py
│   ├── flagging_threshold.py
│   ├── models.py
│   ├── persistence.py
│   └── report_generation.py
```

---

## REPO 1 — repo_basic  (Beginner-friendly)

### What it contains

| File              | Purpose                              |
|-------------------|--------------------------------------|
| `src/auth.py`     | Login / logout / get_user functions  |
| `src/utils.py`    | format_name / clamp utilities        |
| `README.md`       | The "doc" that gets flagged          |
| `.docrot-config.json` | Maps src/ → README.md           |

### Expected changes (run 2)

| Function         | Change type                   | Severity  |
|------------------|-------------------------------|-----------|
| `login()`        | New `remember_me` param       | CRITICAL  |
| `logout()`       | Now raises ValueError         | CRITICAL  |
| `get_user()`     | Removed entirely              | CRITICAL  |
| `hash_password()`| New public function added     | CRITICAL  |
| `format_name()`  | New `separator` param added   | CRITICAL  |
| `clamp()`        | Loop logic changed            | Medium    |

---

### RUN 1 — Create baseline

```bash
python run.py path/to/repo_basic
```

**Expected output:**
```
[docrot] First run detected. Baseline fingerprints generated. No alerts emitted.
```

A `.docrot-fingerprints.json` file will appear inside `repo_basic/`.

---

### Swap in the v2 files

```bash
# Windows PowerShell
Copy-Item repo_basic\src\auth_v2.py   repo_basic\src\auth.py
Copy-Item repo_basic\src\utils_v2.py  repo_basic\src\utils.py

# macOS / Linux
cp repo_basic/src/auth_v2.py   repo_basic/src/auth.py
cp repo_basic/src/utils_v2.py  repo_basic/src/utils.py
```

---

### RUN 2 — Detect changes

```bash
python run.py path/to/repo_basic
```

**Expected output (summary):**
- 5–6 functions flagged as changed
- `README.md` flagged under DOCUMENTATION FILES FLAGGED
- `.docrot-report.json` and `.docrot-report.txt` written to `repo_basic/`
- Severity summary: multiple HIGH, at least 1 MEDIUM

---

## REPO 2 — repo_advanced  (Full pipeline with multiple doc files)

### What it contains

| File                     | Purpose                                     |
|--------------------------|---------------------------------------------|
| `src/payments.py`        | charge_card / refund / get_balance          |
| `src/database.py`        | fetch_user / insert_record / delete_record  |
| `docs/payments.md`       | Payments documentation                      |
| `docs/database.md`       | Database documentation                      |
| `docs/api-reference.md`  | Combined API reference (mapped to both)     |
| `.docrot-config.json`    | Maps src/ → multiple docs each              |

### Expected changes (run 2)

| Function            | Change type                          | Severity |
|---------------------|--------------------------------------|----------|
| `charge_card()`     | New `currency` param + auth check    | CRITICAL |
| `refund()`          | Now raises RuntimeError (exception)  | CRITICAL |
| `get_balance()`     | Removed entirely                     | CRITICAL |
| `apply_discount()`  | New public function added            | CRITICAL |
| `fetch_user()`      | New `include_deleted` param          | CRITICAL |
| `insert_record()`   | Now calls commit() (side-effect)     | CRITICAL |
| `delete_record()`   | No change — should NOT appear        | —        |

---

### RUN 1 — Create baseline

```bash
python run.py path/to/repo_advanced
```

**Expected output:**
```
[docrot] First run detected. Baseline fingerprints generated. No alerts emitted.
```

---

### Swap in the v2 files

```bash
# Windows PowerShell
Copy-Item repo_advanced\src\payments_v2.py  repo_advanced\src\payments.py
Copy-Item repo_advanced\src\database_v2.py  repo_advanced\src\database.py

# macOS / Linux
cp repo_advanced/src/payments_v2.py  repo_advanced/src/payments.py
cp repo_advanced/src/database_v2.py  repo_advanced/src/database.py
```

---

### RUN 2 — Detect changes

```bash
python run.py path/to/repo_advanced
```

**Expected output (summary):**
- 6 functions flagged (delete_record should NOT appear)
- Multiple doc files flagged:
  - `docs/payments.md`
  - `docs/database.md`
  - `docs/api-reference.md` (mapped to BOTH modules — cumulative score will be highest)
- `.docrot-report.json` and `.docrot-report.txt` written to `repo_advanced/`

---

## Verify the Report Files

After Run 2, check inside each repo folder for:

```
.docrot-fingerprints.json   ← updated baseline (auto-generated)
.docrot-report.json         ← machine-readable report
.docrot-report.txt          ← human-readable report
```

Open `.docrot-report.txt` for a clean summary. Open `.docrot-report.json`
to inspect individual flag objects with severity, reason, and suggestion fields.

---

## Resetting a Repo (to re-run from scratch)

```bash
# Windows PowerShell
Remove-Item repo_basic\.docrot-fingerprints.json
Remove-Item repo_basic\.docrot-report.json
Remove-Item repo_basic\.docrot-report.txt

# macOS / Linux
rm repo_basic/.docrot-fingerprints.json repo_basic/.docrot-report.json repo_basic/.docrot-report.txt
```

Then restore the original source files and repeat from Run 1.
