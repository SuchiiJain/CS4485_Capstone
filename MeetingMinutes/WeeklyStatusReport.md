# Weekly Individual Status Report

## Team #2 - Documentation Rot Detector

> This document is updated each week. Each team member logs their hours and contributions for the week. The most recent week appears at the top.

---
# Week 6 — March 23-27, 2026

**Team Leader for Week 6: Portia Hamid**

**Total Hours Spent:**

---

### Marie Liske
- **Hours:** 12
- **Tasks Complete:**
  - Worked with Suchi to configure databse to store JSON reports
  - Worked with SQLite to effectively display data from scans
  - Troubleshooted issued with SQLite, helped brainstorm Postgres & Supabase solutions w/ Suchi
  - Met with team to agree on assigned tasks and milestones for the week
  - Watched videos on Supabase as I was unfamiliar with using
- **Upcoming Tasks:**
  - Confirm DB schema structure & API calls
  - Assist in connecting to user's Github, adding multiple projects/repos
- **Issues:**
  - SQLite had issues with updating on every scan, as the database was contingent on API server running
  - In order to update, the server must be disconnected, changes pulled, and then frontend & backend must be restarted
  - SQLite would not work in production, found that Postgres was necesasary
  - Issues using tokens for auth, spent time working this out

---

### Anusua Halder
- **Hours:**
- **Tasks Complete:**
- **Upcoming Tasks:**
- **Issues:**

---

### Suchi Jain
- **Hours:**
- **Tasks Complete:**
- **Upcoming Tasks:**
- **Issues:**

---

### Aaron Santhosh
- **Hours:** 10
- **Tasks Complete:**
  - Reviewed team weekly meeting and task assignments
  - Updated the frontend auth UI with cleaner login/sign-up design
  - Removed unused placeholder pages from the side navigation and cleaned up routing
  - Made dashboard components interactive and added drill-down navigation to detail screens
  - Enhanced the Issues, Projects, and Scan History pages with more interactive detail views
- **Upcoming Tasks:**
  - Bug fix frontend behavior once the updated backend/database version is finalized
- **Issues:**
  - Confusion around the current state of the backend/database
---

### Samuel Say
- **Hours:**
- **Tasks Complete:**
- **Upcoming Tasks:**
- **Issues:**

---

### Portia Hamid
- **Hours:** 6
- **Tasks Complete:**
  - Brainstormed how to add the AI features to the current pipeline
  - Started implementing AI features (LLM API key, prompting, etc.) on a new branch called AI-integration
- **Upcoming Tasks:**
- **Issues:**

---

# Week 5 — March 9-13, 2026

**Team Leader for Week 5: Anusua Halder**

**Total Hours Spent: 47**

---

### Marie Liske

- **Hours: 10** 
- **Tasks Complete:**
  - Created additional wireframes in Google Stitch/Figma for additional views ans screens, building on the ones created last week
  - Updated frontend to create corresponding React web pages
    - Using static data
  - Refreshed knowledge on how to use use APIs in React (2 hrs)
- **Upcoming Tasks:**
  - Assist team in conecting frontend to backend
  - Start researching how to integrate AI powered suggestions
- **Issues:**
  - Was not sure how to best set up frontend dashboards to be easily integratable with backend APIs, had to research.

---

### Anusua Halder

- **Hours: 8**
- **Tasks Complete:**
  - Served as Team Leader for Week 5
  - Attended team meeting (MOM #5) and discussed task assignments
  - Updated MOM #4 and MOM #5 to GitHub MeetingMinutes folder
  - Reviewed and validated full spec file (Sections 1–14) for cohesion, completeness, and alignment with repo structure
  - Updated Weekly Status Report
  - Reviewed frontend and backend progress updates from teammates
  - Updated and upgraded frontend README
- **Upcoming Tasks:**
  - Upload MOM #5 to GitHub after meeting
  - Update any weekly changes
  - Pick up future Jira tasks
- **Issues:**
  - I have to research more on how to use React

---

### Suchi Jain

- **Hours: 7**
- **Tasks Complete:**
  - Added db/schema.sql to repository
  - Designed schema to support future analytics and dashboard features
  - Created backend/storage.py
  - Implemented init_db() for table initialization and save_scan() for persisting scan metadata and flags
- **Upcoming Tasks:**
  - Debug and resolve backend integration issues
  - Assist in frontend and backend integration
- **Issues:**
  - N/A
---

### Aaron Santhosh

- **Hours: 7**
- **Tasks Complete:**
  - Reviewed new Figma wireframes and current Frontend UI
  - Updated Frontend with more screens from the wireframes (Login, User Settings, Empty State, Issue Drawer)
    - Static 
- **Upcoming Tasks:**
  - Assist team in conecting frontend to backend
- **Issues:**
  - N/A

---

### Samuel Say

- **Hours: 5**
- **Tasks Complete:**
  - Looked into current frontend to see how to contribute
  - Set up Claude with spec to prepare for upcoming weeks work
- **Upcoming Tasks:**
  - Contribute to frontend wireframes
- **Issues:**
  - N/A
---

### Portia Hamid
- **Hours: 10** 
- **Tasks Complete:**
  - Researched FastAPI and how it's used to connect the frontend to the backend
  - Tested the frontend that Marie has been working on, which seems to currently be using hardcoded test data since we don't have a database set up to connect an API to
  - While the database is being worked on, I created a branch on the backend for implementing a FastAPI app that will read the json files and create a connection point for the frontend so we can do further frontend testing even without a database. Once it's ready, the database queries can replace the json in the API.
  - Began brainstorming and research into a possible VSCode extension. Used Claude Sonnet to help brainstorm and plan.
  - Got a rough idea of how a VSCode extension could be implemented, what its functionality could be, and what role it would play in the whole of the program
  - Fixed the problem where the docrot report wasn't being included in the body of the issue that was created, necessitating that the user check the actions log to see the full report. The full report is now included in the GitHub issue itself.
  - Fixed the detector not comparing against the baseline on every push after the database was added. fingerprints.json is now being pushed to the repo, pending the completion of the database implementation.
- **Upcoming Tasks:**
  - Get the frontend actually connected to the backend so we can see it working in action
  - Begin implementing a VSCode extension
  - Full database implementation
- **Issues:**
  - Needed to research how to get an API set up without having a database yet that can store the information
  - Issue arose from database integration that cause the program to create a baseline on every push instead of comparing against the old one. Created a temporary fix to restore functionality, pending the database being fully wired into the code logic.

---

# Week 4 — March 2-6, 2026

**Team Leader for Week 4: Samuel Say**

**Total Hours Spent: 54**

---

### Marie Liske

- **Hours: 10**
- **Tasks Complete:**
  - Created sections 1-4 & 12-14 of Project Spec File
  - Created Frontend GitHub repo
  - Created sample dashboard using Figma wireframes designed by team
  - Created a sample repo to test webhook implementation
  - Worked to test and debug with team
  - Met with team a collective 2-3 hours to work together on project
- **Upcoming Tasks:**
  - Connect frontend to display backend data
  - Create additional test repos
- **Issues:**
  - N/A

---

### Anusua Halder

- **Hours: 10**
- **Tasks Complete:**
  - Attended team meeting to discuss MOM#3 and then followed up with team to discuss weekly tasks
  - Reviewed existing spec sections 1-4 and 9-11 written by teammates
  - Wrote Sections 5-7 of Project Spec File
  - Reviewed Figma wireframe designed by team and sample dashboard
  - Met with team a collective 2-3 hours to work together on project
  - Set up `.github/workflows/docrot.yml` for GitHub Actions CI integration and `.docrot-config.json`
  - Reviewed and cleaned up unnecessary documentation in the repo
  - Set up Week 5 Status Report Outline
- **Upcoming Tasks:**
  - Upload completed spec file to GitHub repo after team completes it
  - Begin writing MOM for Week 4 meeting notes and upload it to GitHub
  - Begin Figma wireframes for dashboard UI
- **Issues:**
  - N/A

---

### Suchi Jain

- **Hours: N/A**
- **Tasks Complete:**
  - N/A
- **Upcoming Tasks:**
  - Create database
  - Begin working on Figma wireframes
- **Issues:**
  - Car accident
  - Laptop issues

---

### Aaron Santhosh

- **Hours: 10**
- **Tasks Complete:**
  - Attended team meeting and followed up with team to discuss weekly tasks
  - Created Initial Figma Wireframes to visualize the layout of the Docrot Detector including Dashboard, Alerts, and Config Setup
  - Met with team a collective 2-3 hours to work together on project
  - Reviewed Project Spec File
- **Upcoming Tasks:**
  - Finalize UI Design and assist frontend development
  - Begin testing
- **Issues:**
  - Google Stitch collaboration

---

### Samuel Say

- **Hours: 10**
- **Tasks Complete:**
  - Created test repositories to test the code on
  - Created sections 9-11 of the spec file
  - Met with team a collective 2-3 hours to work together on project
- **Upcoming Tasks:**
  - Integrate db
- **Issues:**
  - N/A

---

### Portia Hamid

- **Hours: 14**
- **Tasks Complete:**
  - Team meeting to divvy up tasks
  - Researched GitHub webhooks, flask servers, tunnels, and how everything fits together
  - Tested and found that webhooks weren't sufficient, pivoted to researching GitHub actions instead
  - Decided on integrating via a GitHub action that creates an issue on GitHub when it detects potentially stale documentation
  - Completed GitHub integration
- **Upcoming Tasks:**
  - Still waiting on more repos to do more robust testing, a database to replace the current .JSON, and a frontend to hook everything up to.
- **Issues:**
  - Started with figuring out how to do it via a webhook, hosting a flask server and an ngrok tunnel on my personal machine. Ultimately discovered that this method was fundamentally flawed because it required too many permissions. Ended up scrapping all of it and going with a github action instead. Left the webhook code in place just in case the user wants to ever host it completely locally, I guess.

---

# Week 3 — February 23-27, 2026

**Team Leader for Week 3: Samuel Say**

**Total Hours Spent: 43**

---

### Marie Liske

- **Hours: 6**
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
  - Start working on UI
- **Issues:**
  - Switching AI tools in between

---

### Aaron Santhosh

- **Hours: 7**
- **Tasks Complete:**
  - Helped to implement comparator.py, the core semantic diff engine that compares old vs. new function fingerprints to determine whether code changes are significant enough to make documentation stale
  - Implemented compare_file_functions() to evaluate file-level function changes (added/removed/modified) with hash-based fast-path skipping for unchanged functions and public-API-aware add/remove alerts.
- **Upcoming Tasks:**
  - Reconcile conceptual overlap between comparator.py/alerts.py and flagging_threshold.py detection pipelines
  - Test comparator output against sample repositories once test datasets are ready
- **Issues:**
  - N/A

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

> _Note: Individual hour tracking began Week 2. Week 1 consisted of the initial team meeting, role assignments, and project proposal finalization._

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
