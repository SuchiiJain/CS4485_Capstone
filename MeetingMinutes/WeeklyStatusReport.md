# Weekly Individual Status Report

## Team #2 - Documentation Rot Detector

> This document is updated each week. Each team member logs their hours and contributions for the week. The most recent week appears at the top.

---

# Week 11 — April 27 - May 1, 2026

**Team Leader for Week 11: Suchi Jain**

**Total Hours Spent:**

---

### Marie Liske

- **Hours:** 4
- **Tasks Complete:**
  - Fixed bug where issues were not displaying for a given scan
  - Scans now populate depending on the context (all scans, scans for a specific repo, etc)
  - Added functionality for "Add Repo" button that displays steps to set up a new tracked repo
  - Fixed sidebar extending to the entire page length (UI)
  - **Upcoming Tasks:**
     - Start on final presentation slide deck
     - Polish Spec file
- **Issues:**
  - N/A

---

### Anusua Halder

- **Hours:**
- **Tasks Complete:**
- **Upcoming Tasks:**
- **Issues:**

---

### Suchi Jain

- **Hours: 7**
- **Tasks Complete:**
  - Refactored Issues page into expandable row layout
  - Reworked Scan History from split-view to row layout
  - Unified UI patterns across pages (cards, pills, stat strips)
  - Added copy-to-clipboard for repo setup command
- **Upcoming Tasks:**
  -  Enable notifications button
  -  Fix Cnnfiguration Page UI
- **Issues: None**

---

### Aaron Santhosh

- **Hours:**
- **Tasks Complete:**
- **Upcoming Tasks:**
- **Issues:**

---

### Samuel Say

- **Hours:** 4
- **Tasks Complete:**
  - Fixed sidebar footer not showing user profile/settings at bottom of screen
  - Added ErrorBoundary to prevent full-page crashes when a single page errors
  - Fixed Configuration page inline editing (replaced browser prompt dialogs with in-row inputs)
  - Fixed Apply Changes button (replaced browser alert with visual "✓ Saved" feedback)
  - Removed dead notification bell button
- **Upcoming Tasks:**
  - Fix Projects page blank state in local preview mode
  - Fix dead "Configuration" navigation link in Settings page
  - Fix API token Copy button
- **Issues:** None


---

### Portia Hamid

- **Hours: 3**
- **Tasks Complete:**
  - Reviewed and provided feedback on a teammate's frontend pull request
  - Implemented an environment-aware preview mode for local development: the frontend now detects the absence of valid environment variables at dev-server startup and falls back to a self-contained preview state, decoupling visual development from backend and database dependencies. Production builds retain strict environment validation and will error if credentials are missing, preserving deployment safety.
- **Upcoming Tasks:**
  - Continue to support frontend UI tweaks
  - Begin preparing for demo day and completing the project report
- **Issues:**
  - None

---

# Week 10 — April 20 - April 24, 2026

**Team Leader for Week 10: Suchi Jain**

**Total Hours Spent: 55**

---

### Marie Liske

- **Hours: 6**  
- **Tasks Complete:**
  - User tested for Suchi & Sammy integrfation branches
  - Resolved merge conflicts for UI and Rot Gauge PRs
  - Troubleshooted Github OAuth login error, ended up being a misconfigured env
- **Upcoming Tasks:**
  - Review polished UI changes and finalize demo product with team
- **Issues:**
  - Spent some time figuring out OAuth login issue, researched how firebase OAuth was implemented and debugged by logging to pinpoint exact fault point

---

### Anusua Halder

- **Hours: 6**  
- **Tasks Complete:**
  - Created and updated MOM
  - Reviewed open PRs
- **Upcoming Tasks:**
  - Set up MOMs, get back on track and try to help team finalize 
- **Issues:**
  - Double car accident and stomach bug health issues, emailed and discussed already

---

### Suchi Jain

- **Hours: 10**  
- **Tasks Complete:**
  - Built and fixed the rot gauge UI and integrated it properly on projects page
  - Cleaned up projects page by switching to a card + expandable view and showing issues inline instead of cluttered layouts
  - Restored and fixed key buttons (create project, navigation, actions) so flows actually work end-to-end
  - Improved scan history and data display to be more readable (less reliance on long scan IDs, better structure)
  - Fixed multiple TypeScript and data-mapping issues between frontend and Firestore/backend
  - Spent time debugging UI/layout problems, testing changes, and pushing a stable version for teammates to review
- **Upcoming Tasks:**
  - Finish fixing UI layout
- **Issues:**
  - UI zoomed in/out needs to be consistent

---

### Aaron Santhosh

- **Hours: 10**  
- **Tasks Complete:**
  - Fixed Firestore FieldPath bug causing auto-fixed flags to reappear on rescan
  - Fixed auto-fix button errors (wrong flag ID, unsupported reason types, doc path display)
  - Resolved merge conflicts with teammates' UI redesign
  - Fixed issues page showing flags from all scans instead of latest scan only
  - Merged auto-fix feature to main on both frontend and backend repos
  - Verified end-to-end auto-fix works: detects drift → opens PR → merges → flag clears on rescan
- **Upcoming Tasks:**
  - Implement auto-fix function for AI Suggestions as well
  - Add more auto-fix support
- **Issues:**
  - Firestore silently failing baseline updates due to dot-path parsing — took time to diagnose
  - Teammates' UI redesign caused merge conflicts across 4 files

---

### Samuel Say

- **Hours: 12**  
- **Tasks Complete:**
  - Prompted Claude Design to generate a full redesign prototype of the frontend UI
  - Implemented the redesigned UI across all major pages: Auth, Dashboard, Projects, Issues, Scan History, Configuration, and User Settings
  - Built a live Tweaks Panel (theme toggle, accent swatches, density, rot score visualization, typeface) backed by a persistent SettingsContext with localStorage
  - Added three rot score visualizations on the Dashboard: circular gauge, sparkline chart, and dot-colony grid
  - Redesigned User Settings into a 5-section tabbed layout (Profile, Appearance, Notifications, API Tokens, Billing)
  - Fixed sidebar collapse UX so the brand mark acts as the expand button when collapsed
  - Merged origin/main into auth-test, resolving conflicts across 5 files
  - Debugged and fixed 4 failed deployments caused by merge artifacts: duplicate import crash, missing GitHub username helpers, missing page state in ScanHistoryPage, and 6 TypeScript errors flagged by CI
  - Implemented incremental scanning in `src/run.py` — uses `git diff` to restrict fingerprinting to changed files only, falling back to full scan when git is unavailable
  - Parallelized file fingerprinting in `src/run.py` using `ThreadPoolExecutor` — all changed files are now parsed concurrently instead of sequentially
  - Fixed Firestore batch write limit in `functions/index.js` — replaced single `batch.commit()` with a chunked `commitBatches()` helper that splits writes into groups of 400 to stay under Firestore's 500-write hard limit
  - Parallelized LLM suggestion calls in `src/ai_suggestions.py` and `functions/index.js` — multiple flagged docs now call the AI provider concurrently instead of sequentially
- **Upcoming Tasks:**
- **Issues:**
  - Merge conflicts required manual resolution across multiple files due to structural differences between the old and new UI layouts
  - Several declarations lost during conflict resolution only surfaced post-merge on the CI runner, not locally

---

### Portia Hamid

- **Hours: 11**  
- **Tasks Complete:**
  - Led a comprehensive frontend UI redesign across all dashboard pages, establishing a new design language with improved typography hierarchy, dark theme consistency, and spatial density.
  - Redesigned the Dashboard to surface a prominent rot score visualization and contextual quick actions panel, replacing the previous card-based stat layout.
  - Redesigned Scan History with a master-detail split-panel layout, inline rot score progress bars, and a persistent detail drawer for inspecting individual scan runs without leaving the page.
  - Redesigned the Issues page with a severity-tagged master-detail layout, inline code-to-doc mismatch visualization, and structured detail drawer surfacing AI analysis, suggested fixes, function signatures, and detector metadata per issue.
  - Redesigned the Projects page with a repository health overview, per-project rot score progress bars, and Critical/Degrading/Healthy/Untracked filter tabs for at-a-glance triage
  - Created a Configuration page with a Doc Mappings table (glob pattern to documentation file, with a per-mapping sync status), an interactive detection sensitivity threshold slider, and a live Quick Summary sidebar
  - Created a User Settings page as a 5-section tabbed layout (Profile, Appearance, Notifications, API Tokens, Billing) with GitHub OAuth status display, linked account info, and a Danger Zone for account deletion.
  - Collaborated with teammates to gather design feedback and iterate across multiple rounds with Claude Design until the redesign direction was finalized and production-ready
  - Delivered fully coded component implementations ready for backend integration, which was subsequently completed by Samuel.
- **Upcoming Tasks:**
  - Continue debugging the frontend UI to resolve any remaining visual bugs or unimplemented features from the backend.
  - Implement any missing features in the frontend that we now have a visual component for but nothing to hook it up to yet (e.g. the config page).
- **Issues:**
  - Coordinated with Samuel to distribute Claude Design usage across accounts, maximizing AI-assisted iteration capacity throughout the redesign.

---

# Week 9 — April 13 - April 17, 2026

**Team Leader for Week 9: Aaron Santhosh** 

**Total Hours Spent: 40** 

---

### Marie Liske

- **Hours: 6** 
- **Tasks Complete:**
  - Created NPM package install wizard to allow end users to install required files using `npx github:SuchiiJain/CS4485_Capstone`
  - Troubleshooted yml file creation
- **Upcoming Tasks:**
  - Start drafting final presentation slide deck
  - make issues more intuitive/readable
- **Issues:**
  - AI suggestions were not working when using npx install wizard
  - issues setting flags that user could specify when installing, ended up making simplest so user would not have to indicate many flags in command
  - Wizard setup issues, errors when running command

---

### Anusua Halder

- **Hours: 5** 
- **Tasks Complete:**
  - Created and pushed a frontend PR for Issues page UI polish and readability improvements
  - Updated status labels to clearer wording (Flagged / Under Review / Resolved)
  - Improved severity label formatting for easier readability
  - Improved View button styling and overall Issues page usability
  - Updated detail panel wording for better clarity and consistency
  - Updated frontend README with cleaner formatting, current architecture details, setup instructions, project features, and recent development progress
  - Tested all frontend changes locally in the Vite localhost environment to confirm proper rendering
  - Drafted and updated MOM #9
  - Updated Week 9 and 10 weekly individual status content 
- **Upcoming Tasks:**
  - Assist with final frontend polish and responsiveness fixes
  - Help with final presentation/demo preparation
  - Support testing and PR review if needed
- **Issues:**
  - N/A

---

### Suchi Jain

- **Hours: 7**  
- **Tasks Complete:**
  - Finished GTM Strategy
- **Upcoming Tasks:**
  - Complete any UI Functionalities
- **Issues:**
---

### Aaron Santhosh

- **Hours: 8** 
- **Tasks Complete:**
  - Fixed FlagReason priority bug in scanner — `SIGNATURE_CHANGED` now correctly wins over `DOCSTRING_STALE` when multiple reasons match a change event (was breaking the patch generator)
  - Implemented baseline auto-update on successful auto-fix PR merge — `new_fingerprint` and `stable_id` now flow through the full pipeline (scanner → report → action entrypoint → Cloud Function) and write back to Firestore after PR is merged
  - Verified end-to-end auto-fix flow: dry run preview, PR creation against demo repo, merge, and idempotency check (re-scan after merge correctly shows no changes)
  - Identified Firestore dot-path key escaping bug in `applyFix` Cloud Function that silently no-ops the baseline update
- **Upcoming Tasks:**
  - Fix Firestore dot-path bug using `FieldPath` so baseline properly updates after auto-fix PR merge
  - Merge `auto-fix` branch into `main` once flag-clearing is verified end-to-end
- **Issues:**
  - Firestore update in `applyFix` treats `.` in key segments as path separators — baseline write no-ops, so resolved flags still reappear on rescan

---

### Samuel Say

- **Hours: 9**
- **Tasks Complete:**
  - Fixed closeIssue to use direct Firestore path lookup instead of scanning every repo — reduced reads from O(n repos) to a single write
  - Replaced sequential repo queries in getAllScanRuns with parallel Promise.all calls — load time now depends on the slowest single query instead of the sum of all queries
  - Added 25-row pagination to Issues, Scan History, and Projects tables — only a small slice of data is rendered at a time regardless of total record count
  - Added in-memory TTL cache for Firestore queries — getRepos, getAllScanRuns, getScanRunsForRepo, and getIssuesForScan are cached for 60 seconds so repeated page navigations skip Firestore reads entirely
  - Cache updates on issue close so closed status persists if you navigate away and back without waiting for TTL to expire
  - Cache clears on sign-in/out to prevent stale data across users
- **Upcoming Tasks:**
  - Address remaining scalability issues (getScanRunById sequential scan, getIssuesForScan repo loop)
- **Issues:**


---

### Portia Hamid

- **Hours: 5** 
- **Tasks Complete:**
  - Investigated a reported AI integration regression following the npm wrapper release. Unable to reproduce the failure in a fresh environment. Conducted exploratory testing across provider configurations and opened a follow-up with the reporting team member to gather reproduction steps.
  - Provisioned admin access to Firebase/Google Cloud for a teammate to unblock frontend deployment work
  - Validated the npm wrapper release end-to-end on a clean repository, confirmed correct behavior across the full install and setup flow, and merged the PR.
- **Upcoming Tasks:**
  - Implement backend endpoint to persist issue resolve/reopen status updates to Firestore, unlocking the frontend resolve functionality currently awaiting backend support.
- **Issues:**
  - Was unable to reproduce the issue with the AI integration, despite testing.

---

# Week 8 — April 6 - April 10, 2026

**Team Leader for Week 8: Aaron Santhosh** 

**Total Hours Spent: 48**

---

### Marie Liske

- **Hours: 7**  
- **Tasks Complete:**
  - Worked with Suchi on researching GTM strategy and Scalibility Plan for final presentation
  - Worked primarily on scalability, researching methods for expansion & handling high user count & activity
  - Fixed some branch deployment issues
  - User testing on new AI features
  - Update documentation on frontend & backend
- **Upcoming Tasks:**
  - Implement issue resolution
  - Implement rollbacks / scan history
  - Work on making configuration editable in dashboard?
- **Issues:**
  - Was not really sure how to accurately measure performance statistics

---

### Anusua Halder

- **Hours: 7** 
- **Tasks Complete:**
  - Pulled latest updates from both frontend and backend repositories and set up local development environment
  - Tested deployed frontend application and verified authentication and dashboard functionality
  - Investigated project creation and issue flow; identified that certain flows (e.g., project creation, issue generation) are not fully implemented yet
  - Located issue display logic in frontend and identified correct component (IssueTable.tsx) for implementing resolve functionality
  - Implemented frontend Resolve/Reopen button in the issue table using existing issue.status field
  - Created and pushed a new Git branch (anusua-resolve-issues) and opened a pull request for the feature
  - Updated and refined both frontend and backend README files for clarity and accuracy
  - Assisted with reviewing frontend deployment behavior and debugging inconsistencies with hosted version
- **Upcoming Tasks:**
  - Connect resolve/reopen functionality to backend/database for persistent issue state updates
  - Test resolve functionality once issue generation and scan flows are fully implemented
  - Assist with completing missing frontend flows (project creation, scan display, issue generation)
  - Support final demo preparation and system testing
- **Issues:**
  - Unable to fully test resolve functionality due to missing project creation and scan generation flows
  - Limited visibility of issues in UI since backend data pipeline is not fully connected
  - Some frontend features (e.g., project creation) are not yet implemented, limiting end-to-end testing

---

### Suchi Jain

- **Hours: 10**
- **Tasks Complete:**
  - Brainstormed GTM Strategy
  - Worked with Marie on GTM Strategy
  - Brainstormed UI Idea to add scale/spectrum feature and analytics
- **Upcoming Tasks:**
  - Finish GTM Strategy
  - Implement UI Feature
- **Issues: None** 

---

### Aaron Santhosh

- **Hours: 7** 
- **Tasks Complete:** 
  - Merged Portia's AI-integration branch into main
  - Added rot_score computation to Cloud Function and deployed to Firebase
  - Built AI suggestions display in Scan History detail panel with collapsible UI
  - Fixed Firestore subcollection mismatch (issues → flags) so issues actually show up on the web app
  - Fixed success rate calculation and project rot score
  - Reordered sidebar nav, styled sign out button, updated User Settings avatar to show GitHub profile photo
  - Conducted repo testing with varied code changes to test scan functionality
  - Reviewed deployed DocRot web app
- **Upcoming Tasks:** 
  - Get frontend redeployed to docrot-detector.web.app to display the latest changes
  - Continue testing and final demo prep
- **Issues:** 
  - Had to reset fingerprint baseline in Firestore manually to clear stale flags from previous scans

---

### Samuel Say


- **Hours: 9** 
- **Tasks Complete:**
  - Replaced localStorage JWT with Firebase ID tokens for API authorization
  - Rewrote AuthContext to use onAuthStateChanged for persistent login state
  - Added GitHub Actions CI/CD workflow to auto-deploy to Firebase on push to main
  - Pulled main into auth-test branch and resolved merge conflicts
  - Added issue closing functionality with a Close button next to View in the issues table
  - Implemented optimistic UI update with rollback for issue closing
  - Wired the topbar search bar to filter rows in real time on Projects, Issues, and Scan History pages
  - Implemented performance metrics utility (`src/utils/perf.ts`) with a `measure()` async timing helper and a React Profiler callback
  - Instrumented Firestore queries (`getRepos`, `getAllScanRuns`, `getIssuesForScan`, `getAISuggestionsForScan`) to log per-query latency via `console.debug`
  - Instrumented `useIssues` hook to measure total data load time per scan
  - Added React `Profiler` around page content to surface page renders exceeding 100ms
- **Upcoming Tasks:**
  - Merge auth-test PR into main
  - Continue testing issue closing with live Firestore data
  - Investigate serial waterfall in `getAllScanRuns` using perf logs and parallelize with `Promise.all`
  - Add server-side Firestore `where()` filtering to replace client-side repo scan in `getRepos`
- **Issues:**

---

### Portia Hamid

- **Hours: 8** 
- **Tasks Complete:**
  - Finished AI implementation on the AI-integration branch.
    - A Groq API key is set up by default without any setup involved from the user other than adding the relevant lines to their config file. No need to mess with any API keys or secrets.
    - LLM API calls are processed via Google Cloud backend so the Groq API key isn't exposed to the user.
    - When changes are pushed and the AST parser scans the code and flags any changes, the relevant code globs and documentation are sent to the LLM (llama-3.3-70b-versatile), which will return specific, targeted suggestions on what in the documentation needs to be changed to reflect the code changes
    - The LLM response is output in the GitHub Issue that is created when discrepancies are found, along with the changed functions and their severities
    - The LLM response is now also stored in the Firestore database and ready to be integrated into the frontend.
    - Support is in place for OpenAI and Anthropic API keys as well, but for the time being Groq is the easiest option for the user since it requires no additional setup.
- **Upcoming Tasks:** 
  - Fix the frontend to display the LLM suggestions if the user has them enabled
  - We still need a more user-friendly way to set up the repos. Maybe a wizard in the frontend that can either walk the user through the process, or let them directly download the necessary files. Need to discuss.
- **Issues:**
  - Encountered difficulties getting the environment variable set up for the Groq API key in Google Cloud, but it's working now.

---
  
# Week 7 — March 30 - April 3, 2026

**Team Leader for Week 7: Portia Hamid**

**Total Hours Spent: 64**

---

### Marie Liske

- **Hours: 14** 
- **Tasks Complete:**
  - Set up AWS Elastic Beanstalk server to host backend API server for the initial Supabase setup.
  - We did not end up needing AWS, so i undid the implementation, taking it as learning experience.
  - Once we decided the Supabase setup has security flaws, I brainstoned with Portia on how to best manage security so the Github action would not have direct write access to database
  - We decided Firebase has a lot of hosting and security tools built in, so I set up a Firebase Cloud Function to host our backend.
  - This used OIDC tokens and Workload Identity Federation to authorize GitHub worksflows without the need for long lived security tokens.
  - Set up backend to Authenticate with Google Cloud before writing data to our new Firestore DB that Portia set up
- **Upcoming Tasks:**
  - Test V1 web app for bugs
  - Assist with AI integration
  - Clean up dashboard if needed & set up any additonal features outside of MVP
- **Issues:**
  - Had never used AWS before, so setting up the API server took longer than anticipated as I navigated the platform
  - Encountered learning curves in both AWS and Firebase
  - After review with team, realized AWS server was too convoluted and using an outdated flask implementation.
  - Had issues getting action authorized to write to Firestore DB and other repos' actions to be able to write.

---

### Anusua Halder

- **Hours: 10** 
- **Tasks Complete:**
  - Set up and configured local development environment on Windows (Node.js, npm), including resolving execution policy issues to enable full project build and runtime support
  - Synced frontend and backend repositories with latest updates and verified compatibility with recent Firebase migration changes
  - Ran and tested the React frontend locally using Vite to validate current system behavior and UI functionality
  - Implemented a UI architecture improvement by refactoring sidebar navigation and relocating the User Settings component to the sidebar footer (bottom-left), aligning with standard dashboard UX patterns
  - Ensured seamless integration with existing navigation logic (`navigateToPage`) without modifying routing or backend dependencies
  - Verified that UI changes did not impact authentication flow, page rendering, or Firestore-driven data updates
  - Contributed to system-wide documentation updates by aligning proposal and spec files with the new Firebase-based architecture (Firestore, Firebase Auth, Cloud Functions, and CI/CD pipeline)
  - Ensured consistency between documented system design and actual deployed implementation
  - Debugged and resolved a Firebase configuration issue (invalid API key) by correctly setting up local environment variables using `.env`
  - Prepared and updated meeting documentation (MOM #6 and draft of MOM #7) to reflect current project progress and architectural changes 
- **Upcoming Tasks:**
  - Continue assisting with frontend polish and UI consistency improvements
  - Support final documentation updates and alignment across all project materials
  - Assist with testing demo flow and identifying UI/UX issues before final presentation
  - Help verify integration across frontend, backend, and database for final deployment
- **Issues:**
  - Initial environment setup challenges with npm and execution policy on Windows, resolved successfully
  - Required time to understand frontend structure and navigation logic before implementing UI changes
  - Needed to stay aligned with rapidly evolving backend and database changes during Firebase migration
---

### Suchi Jain

- **Hours: 8** 
- **Tasks Complete:**
    - Researched AWS and different options we could use
    - Tested Frontend to ensure successful deployment
    - Reviewed Supabase issues
    - Verified full pipeline: GitHub Action → Firestore → frontend dashboard
    - Attended team meetings and understood Firebase/NoSQL syntax with Marie and Portia
- **Upcoming Tasks:**
    - Work with Aaron to finalize Frontend and fix scanning issues
- **Issues:**
    - I was initially very lost with all the changes so it took me a while to adapt to them (and I have still not understood them fully)
---

### Aaron Santhosh

- **Hours: 12** 
- **Tasks Complete:** 
  - Connected the entire frontend to Firebase/Firestore, replacing old API layer
  - Rewired Dashboard, Projects, Scan History, and Issues pages to read from Firestore
  - Replaced mock/Supabase data hooks (useReports, useScanEvents) with live Firestore queries
  - Rebuilt auth flow to GitHub-only (removed email/password sign-up)
  - Added function to filter and display only repos made by the GitHub user
  - Rewired UserSettingsWireframePage to read/write user preferences from Firestore
  - Updated ProjectsPage to pull scan data from Firestore subcollections
  - Fixed scan history success rate metric
  - Migrated backend action entrypoint from Supabase to Firestore
  - Created a repo called "docrot-demo" with intentional doc rot for end-to-end testing
  - Verified full pipeline: GitHub Action → Firestore → frontend dashboard
  - Implemented rot score calculation and connected it to frontend
- **Upcoming Tasks:** 
  - Bug fix rot score calculation
  - Improve login/signup UI
  - Continue testing web app for more bugs/issues
  - Assist other team members
- **Issues:** 
  - I was hitting my max Claude Code limits because I made a lot of changes in short periods of time rather than spreading it throughout the week. 

---

### Samuel Say

- **Hours: 10** 
- **Tasks Complete:**
  - Implemented Firebase Authentication (email/password + GitHub OAuth)
  - Created `src/firebase.ts` with Firebase app initialization
  - Rewrote `src/auth/AuthContext.tsx` to use Firebase `onAuthStateChanged`, replacing custom JWT/localStorage auth
  - Updated `src/api/client.ts` to attach Firebase ID tokens to API requests
  - Wired up `src/pages/AuthPage.tsx` with real form state, error handling, and loading states
  - Refactored `src/App.tsx` to use Firebase user state, removing the old `LoginPage` and redundant `isSignedIn` gate
  - Configured Firebase env vars in `.env` and `.env.example`
  - Enabled Email/Password and GitHub sign-in in Firebase Console
  - Set up GitHub OAuth App
  - Deployed frontend to Firebase Hosting
- **Upcoming Tasks:** 
- **Issues:** 


---

### Portia Hamid

- **Hours: 12** 
- **Tasks Complete:**
  - Fixed security flaw in database integration. User no longer needs to set up a github secret that permits them access to the private DB connection string + password.
  - Added more tables and rows to make querying more robust. Previously there were no rows for stale docs, params, return types, etc., so querying detailed scan information from the frontend would have been impossible. There should be much more versatility now.
  - Also added a table for repos, which will make it easier to query specific information for each repo/branch.
  - Properly connected the database to the scanner so the scanner will actually read the fingerprint baseline from the DB rather than relying on the JSON file. Added a fingerprints_baseline table for this purpose. This makes it so the user no longer needs to grant write permission to the action runner, which should bring peace of mind to the user. Read permissions are sufficient.
  - Due to some security concerns that were flagged by Supabase following the previous updates, we decided to redo how our backend is hosted and have begun the process of switching to Firebase/Firestore. Marie and I started working to get the project set up on Firebase.
  - Decided on using OIDC and WIF to authenticate the GitHub Action and allow it to write the scan results to Firebase. Spent several hours with Marie, trying to work out how to get that set up.
  - Began adding infrastructure in the AI-implementation branch to support Groq as the default LLM suggestion provider (with options for the user to use an OpenAI or Anthropic API key if they prefer)
- **Upcoming Tasks:** 
  - Finish AI implementation and start planning on where to place it on the frontend.
- **Issues:** 
  - Removing mentions of the private database information from the code and switching everything to use Supabase's public API. I've never used Supabase before, so this took some trial and error to figure out.
  - Had difficulty with the DB perms required for the repos table, which required some debugging.
  - Even with the old security flaws on Supabase fixed, our current architecture still left a huge security hole in the pipeline: the GitHub Action needed to write to the Supabase directly, which required us to have read/write access to anon users on Supabase, which created another inherent security flaw. We spent some time brainstorming and decided that switching everything over to Firebase would let us take care of those vulnerabilities easier, since Firebase will be able to host the database, the backend API, and the frontend, as well as already have oauth baked in. It will take some time to set up, but ultimately we think it will be the path of least resistance.

---

# Week 6 — March 23-27, 2026

**Team Leader for Week 6: Portia Hamid**

**Total Hours Spent: 63**

---

### Marie Liske
- **Hours: 12** 
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
- **Hours: 7**
- **Tasks Complete:**
  - Attended team meetings to sort out tasks and follow up with project.
  - Updated the project specification to reflect current Phase 3 implementation progress
  - Added a “Current Implementation Status” section outlining database migration, frontend integration, authentication progress, and deployment research
  - Updated persistence section to reflect transition from SQLite to PostgreSQL (Supabase)
  - Updated frontend environment variables in spec to match actual implementation
  - Uploaded updated spec file to frontend repository and replaced outdated version
  - Completed MOM #6 and updated weekly team progress documentation
- **Upcoming Tasks:**
  - Continue refining spec file as implementation evolves
  - Research and document hosting/deployment strategy options
- **Issues:**
  - N/A
---

### Suchi Jain
- **Hours: 14**
- **Tasks Complete:**
  - Worked on migrating the database from SQLite to Postgres (Supabase) and configured Postgres connection using DATABASE_URL and psycopg2
  - Created and updated DB schema for scan_runs and flags tables
  - Moved database files into backend/database for better structure and removed SQLite file from repo; updated .gitignore
  - Worked with the team to troubleshoot DNS and connection issues
  - Watched videos to understand authentication systems
- **Upcoming Tasks:**
  - Finalize Backend Structure
  - Work with Sammy to build authentication system
- **Issues:**
  - SQLite caused file-locking and update problems
  - DNS issues when connecting to Supabase
  - Database was not initially connected to production pipeline
  - Had to adjust imports and project structure after migration

---

### Aaron Santhosh
- **Hours: 10** 
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
- **Hours: 11**
- **Tasks Complete:**
  - Implemented GitHub OAuth authentication on the backend (authentication branch)
    - Created backend/auth.py with OAuth login/callback routes and JWT middleware
    - Protected /api/scan endpoint with JWT authentication
    - Added PyJWT dependency to requirements.txt
  - Implemented frontend authentication on the auth-test branch
    - Created AuthContext.tsx for token storage and OAuth callback handling
    - Created LoginPage.tsx with "Login with GitHub" button
    - Updated client.ts to read JWT from localStorage instead of a static env var
    - Updated App.tsx to show login page when unauthenticated and real user info in sidebar
  - Successfully tested full OAuth login/logout flow locally
- **Upcoming Tasks:**
  - Deploy the backend to a server 
  - Deploy the frontend to a hosting service 
  - Update the GitHub OAuth App callback URL to real domain
  - Set the env vars on your hosting platform instead of a local .env file
- **Issues:**
  - N/A


---

### Portia Hamid
- **Hours: 9** 
- **Tasks Complete:**
  - Brainstormed how to add the AI features to the current pipeline
  - Started implementing AI features (LLM API key, prompting, etc.) on a new branch called AI-integration
  - Assisted with testing for the database integration and Supabase migration
- **Upcoming Tasks:**
  - Finish implementing AI features
  - Help get the database up and running
- **Issues:**
  - N/A

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
