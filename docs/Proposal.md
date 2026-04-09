**Documentation Rot Detector**
==============================

**Project Overview**
--------------------

Our Documentation Rot Detector is a software tool designed to automatically identify when project documentation becomes outdated as source code changes over time. As features are modified, renamed, or removed, documentation can fail to be updated, leading to confusion, slower onboarding, and lost productivity. Currently most teams do manual reviews to maintain documentation, which can be unreliable as code is changed frequently across many teams.

Our system solves this problem by continuously analyzing both code and documentation using static analysis and abstract syntax tree (AST) parsing. It assigns change hashes to code components and links them to related documentation. When code is updated, the system detects mismatches and flags affected documentation automatically. For advanced use, the tool can selectively apply lightweight AI models to generate update suggestions only where needed. We integrate directly into development workflows using GitHub Actions, where scans are automatically triggered on commits and results are sent to a cloud-based ingestion pipeline. The Documentation Rot Detector turns documentation maintenance into an automated process rather than a manual task.

**Project Scope**
-----------------

**Core Functionalities**

*   Repository scanning
*   Code structure extraction using AST
*   Code reference detection
*   Hashing to detect changess
*   Error throwing when changes detected
*   Easy to understand mismatch detection messaging
*   Local and CLI functionality
*   Integration with GitHub using a git hook

**Nice to Have**

*   Visual Dashboard
*   Clean UI
*   Pull request integration
*   Support multiple languages & documentation formats
*   AI - assisted suggestions
*   Historical tracking
*   Multiple output formats (HTML, markdown, etc)

**Project Objectives**
----------------------

1.  **Primary Objectives**

    *   Design and implement an automated system that detects and reports outdated or inconsistent documentation in software repositories.
    *   Accurately link code elements to corresponding documentation references.
    *   Provide clear, understandable reports for developers.

2.  **Measurable Goals**

    *   Successfully scan and analyze at least one full medium-sized repository.
    *   Support one primary programming language and one documentation format for a MVP.
    *   Complete full repository analysis in under 60 seconds for medium-sized projects.
    *   Generate reports in under 2 seconds after analysis.
    *   Achieve at least 85-90% precision in detecting true documentation mismatches.
    *   Enable setup and execution in under 15 minutes for new users.
    *   Ensure reports are understandable without additional explanation.

3.  **Success Metrics**

    *   Detection Accuracy: >= 90% on benchmark test repositories.
    *   Analysis Time: <= 60 seconds for full scans, <= 10 seconds for incremental scans.
    *   Report Generation Time: <= 2 seconds.
    *   Successful deployment in at least 2 real or open-source projects.
    *   AI generated suggestions accepted in at least 70% of cases.
    *   Average AI response time <= 5 seconds per flagged section.
    *   Reduction in manual documentation update time by at least 30%.

**Specifications**
------------------

#### **User Interface (UI) Design**

*   Web
*   Command Line Interface (CLI)
*   Login, Dashboard overview, issues section, issue detail section, history, settings, select project
*   Buttons for scanning, resolve, ignore, create ticket
*   Search bar for functions, file name, API endpoint, general keywords

#### **Backend & APIs**

*   Scanner service to parse, hash and find mismatches
*   Backend dashboard API serves web UI results

*   Database Structure

    *   Projects (id, repo_destination, language(s)
    *   Scans (is, project_id, commit, timestamp, status
    *   CodeElements (id, scan_id, type, name, signature, hash)
    *   DocumentationRefs (is, scan_id, file_path, reference, linked_code)
    *   Issues (id, scan_id, issue_type, severity, element_id, description, status, documentation_file_path)

*   API Structure

    *   POST /api/project(create project)
    *   POST /api/scans (scan repo)
    *   GET /api/scans(scan history report)
    *   GET /api/issues(get all issues)
    *   GET /api/issues/:id (get info on specific issue)

*   MVP authentication: simple admin login or token-based access
*   JWT for dashboard sessions?
*   GitHub integration: GitHub App or OAuth token

*   Updated API & Data Flow (MVP Adjustment)

    *   In the current implementation, scan results are not exclusively processed through traditional REST API endpoints.
    *   GitHub Actions send scan data directly to a Google Cloud Function (ingestScan), which persists results into Firebase Firestore.
    *   This approach simplifies the ingestion pipeline and enables real-time updates for the frontend dashboard.
    *   The original REST API structure remains part of the design for future expansion.

#### **Data & AI Model (Dataset source and Model architecture).**

Model Functionality

*   AI is not required for detection. The deterministic analyzer flags likely mismatches first.
*   AI is used for post-processing, specifically:

    *   Validation: confirm flagged mismatches
    *   Suggestion generation: propose updated wording, updated parameters, and corrected examples
    *   Output formatting: return structured recommendations for the dashboard

Dataset Source

*   No large curated dataset is required for the MVP.
*   Primary “data” inputs come from the repository itself (code & docs) and synthetic test repositories where mismatches are intentionally introduced

Preprocessing Steps

*   Extract code structure with AST and static analysis
*   Extract documentation references via regex/pattern matching for symbols (e.g., foo(), ClassName, endpoints), code-fence detection for code snippets, and linking references to code elements using name matching + file proximity

**Tech Stack**
--------------

●        **Frontend:** React (Vite), Figma  
●        **Backend:** Hybrid approach using FastAPI (planned) and Google Cloud Functions for scan ingestion  
●        **Database:** Firebase Firestore (replacing PostgreSQL for real-time data storage and simplified integration)  
●        **Authentication:** Firebase Authentication with GitHub OAuth integration  
●        **AI/ML (if applicable):** Local model or hosted (OpenAI/Gemini)  
●        **Cloud & Hosting:** Firebase Hosting (frontend) + Google Cloud Functions (backend ingestion)  
●        **CI/CD:** GitHub Actions with secure authentication using Workload Identity Federation (OIDC)  
●        **AI Development Tools:** Copilot & Cursor  

**Hardware Requirements**
-------------------------

N/A

**Software Requirements**
-------------------------

### **Development Tools**

*   Git + GitHub
*   Visual Studio Code
*   Docker Desktop

### **Runtime Environments and SDKs**

*   Node.js + npm
*   Python 3.10+
*   npm for frontend dependencies
*   pip for Python dependency management

### **Core Frameworks and Libraries**

#### **Frontend**

*   React
*   Figma (UI for dashboards)
*   Firebase SDK / Fetch API

#### **Backend & Scanner**

*   FastAPI
*   Python CLI Scanner
*   AST & Parsing Libraries
*   Text Processing Libraries

### **Database and Storage**

*   Firebase Firestore

### **CI/CD and Automation**

*   GitHub Actions

### **AI / ML**

*   Ollama or llama.cpp (optional)
*   OpenAI or Google Gemini APIs

### **Cloud, Hosting, and Deployment**

*   Firebase Hosting
*   Google Cloud Functions

**Project Timeline**
--------------------
### Phase 1: Planning & Design (2/20)
- [ ] Finalize MVP features
- [ ] Choose language and documentation format
- [ ] Define system architecture
- [ ] Create architecture diagram
- [ ] Define mismatch rules
- [ ] Prepare test datasets
- [ ] Create test repositories
- [ ] Write technical design document

### Phase 2: Core Scanner MVP (3/13)
- [ ] Implement AST parsing
- [ ] Implement documentation reference extractor
- [ ] Implement hashing system
- [ ] Add mismatch detection logic
- [ ] Generate TXT reports
- [ ] Generate JSON reports
- [ ] Build working CLI scanner

### Phase 3: Backend & Database (3/27)
- [ ] Design database schema
- [ ] Build FastAPI backend
- [ ] Store scan results
- [ ] Implement core APIs
- [ ] Create scan and issue endpoints
- [ ] Deploy running API service

### Phase 4: Web Dashboard (4/10)
- [ ] Build React dashboard
- [ ] Implement issue list view
- [ ] Add filtering and search
- [ ] Implement scan history
- [ ] Connect frontend to backend
- [ ] Polish UI/UX

### Phase 5: CI/CD Integration & Automation (4/17)
- [ ] Configure GitHub Actions
- [ ] Enable scan on commit
- [ ] Implement automatic feedback
- [ ] Build CI pipeline
- [ ] Test automated workflows

### Phase 6: AI + Refinement (5/1)
- [ ] Integrate AI suggestions
- [ ] Optimize performance
- [ ] Handle edge cases
- [ ] Complete documentation
- [ ] Prepare demo
- [ ] Write final report
- [ ] Deploy web-hosted demo system

**Team Leader Rotation**
------------------------

- **2/9 - 2/20**: Marie Liske  
- **2/21 - 3/6**: Samuel Say  
- **3/7 - 3/20**: Anusua Halder  
- **3/21 - 4/3**: Portia Hamid  
- **4/4 - 4/17**: Aaron Santhosh  
- **4/18 - 5/1**: Suchi Jain

**Project Team**
----------------

### Frontend Developer
- Marie Liske
- Anusua Halder  
**Responsibilities:** UI development

### Backend Developer
- Marie Liske
- Samuel Say
- Aaron Santhosh
- Portia Hamid
- Suchi Jain  
**Responsibilities:** API & Database

### ML Engineer
- Aaron Santhosh
- Portia Hamid
- Suchi Jain  
**Responsibilities:** AI/ML models

### QA Tester
- Anusua Halder
- Samuel Say
- Portia Hamid  
**Responsibilities:** Testing & validation

**Links**
---------

● **GitHub Backend Repository:** https://github.com/SuchiiJain/CS4485_Capstone  
● **GitHub Frontend Repository:** https://github.com/marieliske/CS4485_Capstone_Frontend  
● **Jira:** https://cs4485-team2.atlassian.net/jira/software/projects/SCRUM/summary  
● **Design Document:** https://www.figma.com/buzz/mL6QjBH9IeETv4zAOJ3g94/CS4485-Project  
● **Spec File:** https://docs.google.com/document/d/1SyV_tq7JigWuA7d5Yr3JC47hMbE_rXriLL92Z8l2z6Q/edit

