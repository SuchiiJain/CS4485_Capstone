# Weekly Individual Status Report
## Team #2 - Documentation Rot Detector

> This document is updated each week. Each team member logs their hours and contributions for the week. The most recent week appears at the top.

---

# Week 3 — February 23-27, 2026

**Team Leader for Week 3: Samuel Say**

**Total Hours Spent: 36**

---

### Marie Liske
- **Hours:** 6
- **Tasks Complete:**
  - Implemented config-driven documentation mapping so code file patterns (code_glob) map to related docs and trigger doc-review alerts when mapped code changes.
  - Strengthened threshold handling by validating config values, applying safe defaults, and normalizing thresholds before scoring.
  - Expanded fingerprint baseline updates with a dedicated updater that reports file/function deltas (added, removed, changed, unchanged) each run.
  - Improved persistence reliability by using atomic baseline writes (temp file + replace) and updated README documentation to reflect all new behavior.
- **Upcoming Tasks:**
  - Ensure changes in branch are compatable with main before merging
  - Resolve any potential merge conflicts
  - Test on created sample repositories
- **Issues:**
  - N/A

---

### Anusua Halder
- **Hours: 7**
- **Tasks Complete:**
  - Attended Meeting #2 (February 20) and reviewed all action items from MOM #1
  - Wrote up MOM #2 with all the discussion notes, action items, and technical decisions from the meeting
  - Created and maintained the weekly meeting tracking file and set up the MeetingMinutes folder in the GitHub repository
  - Attended in-person team meetup on Monday to align on priorities and delegate tasks on Jira
  - Wrote/finalized flagging_threshold.py — includes all core data structures, enums, severity mapping, and detection logic functions
  - Wrote/finalized report_generation.py — handles both .txt and .json report output formats for the scanner
  - Added comments throughout both files to make them easier to follow
  - Updated the README to include both files in the folder structure and module table
  - Pushed files to src/ on GitHub
- **Upcoming Tasks:**
  - Review pseudocode.py and provide feedback
  - Begin Figma wireframes
- **Issues:**
  - N/A 

---

### Suchi Jain
- **Hours: 7**
- **Tasks Complete:**
  - Attended Meeting #2 (February 20) and reviewed all action items from MOM #1
  - Attended in-person team meetup on Monday to align on priorities and delegate tasks on Jira
  - Created Postgres DB on Local Machine and pushed SQL file to main branch
  - Reviewed Pseudocode.py and provided feedback
- **Upcoming Tasks:**
  - Finish creating test datasets and repos to train the model
- **Issues:**
  - Switching AI tools in between
---

### Aaron Santhosh
- **Hours:**
- **Tasks Complete:**
- **Upcoming Tasks:**
- **Issues:**

---

### Samuel Say
- **Hours: 8**
- **Tasks Complete:**
  - Implemented run.py, the main entry point for the Documentation Rot Detector that ties together all existing modules into a complete working pipeline
  - Integrated the flagging_threshold.py severity model (HIGH/MEDIUM/LOW) with the comparator/alerts pipeline via a bridging layer
  - Connected report_generation.py to produce both .docrot-report.txt and .docrot-report.json output files on each scan
  - Added CLI argument support including optional commit hash embedding in reports
- **Upcoming Tasks:**
  - Testing the full pipeline end-to-end on a real or sample repository
  - Verifying report output accuracy against known code changes
  - Any remaining integration work (GitHub hook, dashboard, AI suggestions)
- **Issues:**
  - The two detection pipelines (alerts.py and flagging_threshold.py) have some conceptual overlap that may need to be reconciled as the project matures
  - Doc-file alerting requires manual configuration of doc_mappings in .docrot-config.json — no auto-discovery yet

---

### Portia Hamid
- **Hours: 8**
- **Tasks Complete:**
  - Finalized the weight-based mismatch detection pseudocode (`pseudocode.py`), incorporating team feedback and validating logic with Claude Opus 4.6
  - Authored the system architecture document (`Architecture.md`), mapping out the full 4-layer pipeline from change detection through AST parsing, comparison/scoring, and alerting
  - Implemented `ast_parser.py` — the core AST parsing module that handles source-to-tree parsing, function/method node extraction, parent-class annotation, stable cross-version function ID generation, docstring stripping (so cosmetic edits don't trigger false positives), and public/private API visibility detection
  - Implemented `fingerprint.py` — the semantic fingerprint builder (~520 lines) that extracts multi-dimensional features from each function (signature, control flow, conditions, calls, side effects, exceptions, returns) used by the scoring model
  - Created hands-on example scripts (`example_basic_ast.py`, `example_fingerprinting.py`) demonstrating AST parsing and fingerprint extraction to validate module correctness and serve as developer documentation
- **Upcoming Tasks:**
  - Expand testing to larger repositories to validate fingerprint stability and scoring accuracy at scale
  - Begin GitHub webhook integration so the parser triggers automatically on push events instead of requiring manual invocation
- **Issues:**
  - Parser does not yet run automatically, currently requires manual activation. GitHub hook integration will resolve this in the next sprint

---

# Week 2 — February 16-20, 2026

**Team Leader for Week 2: Marie Liske**

**Total Hours Spent: 8**

---

### Marie Liske
- **Hours:** 2
- **Tasks Complete:**
  - Set up Jira board and organized Sprint 2 tasks
  - Set up Figma workspace for UI planning
  - Led hash function design discussion and defined hashing approach for mismatch detection
  - Contributed to API contract design (Scans, Reports, Mismatches, Config, Hashes objects)
- **Upcoming Tasks:**
  - Define and document the hash function specification precisely (ensure cosmetic changes do not affect hash output)
  - Finalize API contract documentation and push to GitHub
  - Begin Figma wireframes once development start is confirmed
  - Confirm documentation-currency detection approach (timestamp-based vs. reverse detection)
- **Issues:**
  - Hash function definition requires careful scoping — if too broad, cosmetic changes may incorrectly trigger documentation flags
  - Wireframing is blocked until Phase 1 development officially begins

---

### Anusua Halder
- **Hours:** 1
- **Tasks Complete:**
  - Prepared and documented Minutes of Meeting (MOM #1 and MOM #2)
  - Created MeetingMinutes folder on GitHub and uploaded all MOM documents
  - Maintained weekly progress documentation
- **Upcoming Tasks:**
  - Update Weekly Status Report after each meeting
  - Add Week 3 MOM once February 27 meeting is complete
  - Review `pseudocode.py` and provide feedback or suggestions
- **Issues:** N/A

---

### Suchi Jain
- **Hours:** 1
- **Tasks Complete:**
  - Set up the GitHub repository (CS4485_Capstone)
  - Granted TA access to the repository
  - Pushed project proposal and supporting documents to GitHub for TA review
- **Upcoming Tasks:**
  - Begin Phase 1 development: CLI scanner skeleton in Python
  - Review and provide feedback on `pseudocode.py`
  - Confirm documentation-currency detection approach with the team
- **Issues:**
  - CLI scanner development cannot fully begin until hash function specification is finalized

---

### Aaron Santhosh
- **Hours:** 1
- **Tasks Complete:**
  - Attended and participated in weekly team meeting (February 20, 2026)
  - Contributed to API contract discussion during the MOM meeting
  - Reviewed project proposal and Sprint 2 task breakdown on Jira
- **Upcoming Tasks:**
  - Review `pseudocode.py` and provide feedback on ML/algorithm logic
  - Research AST parsing approach for code change detection
  - Assist with Phase 1 CLI scanner development
- **Issues:**
  - Needs to confirm specific Phase 1 task assignments before development begins

---

### Samuel Say
- **Hours:** 1
- **Tasks Complete:**
  - Researched and finalized AI development tools for the team (GitHub Copilot, VS Code, Cursor)
  - Documented tool selection decisions for team reference
- **Upcoming Tasks:**
  - Review `pseudocode.py` and provide feedback or suggestions
  - Support QA test repository setup for Phase 1 (intentional documentation mismatches)
- **Issues:**
  - QA test repository setup depends on CLI scanner skeleton being in place first

---

### Portia Hamid
- **Hours:** 2
- **Tasks Complete:**
  - Led pseudocode development for the weight-based mismatch detection algorithm
  - Pushed `brainstorming.txt` and `pseudocode.py` to GitHub
  - Used Claude 4.6 to validate pseudocode logic and identify gaps in the detection approach
- **Upcoming Tasks:**
  - Refine `pseudocode.py` based on team feedback
  - Assist with defining the hash function specification
  - Begin translating pseudocode into working Python code for Phase 1
- **Issues:**
  - Weight thresholds for mismatch scoring are not yet finalized — team needs to agree on what score triggers a documentation flag

---

# Week 1 — February 9-13, 2026

**Team Leader for Week 1: Marie Liske**

**Total Hours Spent: N/A**

> *Note: Individual hour tracking began Week 2. Week 1 consisted of the initial team meeting, role assignments, and project proposal finalization.*

---

### Marie Liske
- **Hours:** N/A
- **Tasks Complete:** N/A
- **Upcoming Tasks:** N/A
- **Issues:** N/A

---

### Anusua Halder
- **Hours:** N/A
- **Tasks Complete:** N/A
- **Upcoming Tasks:** N/A
- **Issues:** N/A

---

### Suchi Jain
- **Hours:** N/A
- **Tasks Complete:** N/A
- **Upcoming Tasks:** N/A
- **Issues:** N/A

---

### Aaron Santhosh
- **Hours:** N/A
- **Tasks Complete:** N/A
- **Upcoming Tasks:** N/A
- **Issues:** N/A

---

### Samuel Say
- **Hours:** N/A
- **Tasks Complete:** N/A
- **Upcoming Tasks:** N/A
- **Issues:** N/A

---

### Portia Hamid
- **Hours:** N/A
- **Tasks Complete:** N/A
- **Upcoming Tasks:** N/A
- **Issues:** N/A
