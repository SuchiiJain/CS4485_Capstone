**Documentation Rot Detector**
==============================

**Project Overview**
--------------------

Our Documentation Rot Detector is a software tool designed to automatically identify when project documentation becomes outdated as source code changes over time. As features are modified, renamed, or removed, documentation can fail to be updated, leading to confusion, slower onboarding, and lost productivity. Currently most teams do manual reviews to maintain documentation, which can be unreliable as code is changed frequently across many teams.

Our system solves this problem by continuously analyzing both code and documentation using static analysis and abstract syntax tree (AST) parsing. It assigns change hashes to code components and links them to related documentation. When code is updated, the system detects mismatches and flags affected documentation automatically. For advanced use, the tool can selectively apply lightweight AI models to generate update suggestions only where needed. We plan to integrate into development workflows and run this on every commit. The Documentation Rot Detector turns documentation maintenance into an automated process rather than a manual task.

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
    

1.  **Measurable Goals**
    

    *   Successfully scan and analyze at least one full medium-sized repository.
    
    *   Support one primary programming language and one documentation format for a MVP.
    
    *   Complete full repository analysis in under 60 seconds for medium-sized projects.
    
    *   Generate reports in under 2 seconds after analysis.
    
    *   Achieve at least 85-90% precision in detecting true documentation mismatches.
    
    *   Enable setup and execution in under 15 minutes for new users.
    
    *   Ensure reports are understandable without additional explanation.
    

1.  **Success Metrics**
    

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
    
    *   Projects (id, repo\_destination, language(s)
        
    *   Scans (is, project\_id, commit, timestamp, status
        
    *   CodeElements (id, scan\_id, type, name, signature, hash)
        
    *   DocumentationRefs (is, scan\_id, file\_path, reference, linked\_code)
        
    *   Issues (id, scan\_id, issue\_type, severity, element\_id, description, status, documentation\_file\_path)
        
*   API Structure
    
    *   POST /api/project(create project)
        
    *   POST /api/scans (scan repo)
        
    *   GET /api/scans(scan history report)
        
    *   GET /api/issues(get all issues)
        
    *   GET /api/issues/:id (get info on specific issue)
        

*    MVP authentication**:** simple admin login or token-based access
    
*   JWT for dashboard sessions?
    
*   GitHub integration**:** GitHub App or OAuth token
    

#### **Data & AI Model (Dataset source and Model architecture).**

●       Describe the ML model’s functionality.

●       Mention any data sources and preprocessing steps.

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

*   Extract code structure with AST and static analysis:
    
*   function/class signatures, parameters, return type (if available), visibility
    
*   Extract documentation references via regex/pattern matching for symbols (e.g., foo(), ClassName, endpoints), code-fence detection for code snippets, and linking references to code elements using name matching + file proximity
    

**Tech Stack**
--------------

●       **Frontend:** React, Figma

●       **Backend:** FastAPI + CLI scanner

●       **Database:** PostgreSQL

●       **AI/ML (if applicable):** Local model or hosted (OpenAI/Gemini)

●       **Cloud & Hosting:** GitHub Actions, AWS + Docker

●       **AI Development Tools:** Copilot & Cursor


**Hardware Requirements**
-------------------------

N/A

**Software Requirements**
-------------------------

### **Development Tools**

*   Git + GitHub
    
    *   Version control, collaboration, and CI/CD integration.
        
*   Visual Studio Code
    
    *   Primary development environment for frontend, backend, and scanner development.
        
*   Docker Desktop
    
    *   Used for containerizing backend services and ensuring consistent deployment environments.
        

### **Runtime Environments and SDKs**

*   Node.js + npm
    
    *    Required for building and running the React frontend.
        
*   Python 3.10+
    
    *   Required for FastAPI backend services and the CLI scanner
        
*   Package Managers
    
    *   npm for frontend dependencies
        
    *   pip for Python dependency management
        

### **Core Frameworks and Libraries**

#### **Frontend**

*   React
    
*   Figma (UI for dashboards)
    
*   Axios / Fetch API
    
    *   For communication with the FastAPI backend.
        

#### **Backend & Scanner**

*   FastAPI
    
*   Python CLI Scanner
    
*   AST & Parsing Libraries
    
*   Text Processing Libraries
    

### **Database and Storage**

*   PostgreSQL
    

### **CI/CD and Automation**

*   GitHub Actions
    
    *   Runs automated scans and tests on commits and pull requests.
        
    *   Publishes scan reports and triggers backend workflows
        

### **AI / ML**

*   Ollama or llama.cpp for hosting lightweight LLMs locally.
    
*   OpenAI or Google Gemini APIs for cloud-based inference.
    
*   Prompt Management Tools
    
    *   Structured prompt templates and JSON-based response validation.
        

### **Cloud, Hosting, and Deployment**

*   Amazon Web Services (AWS)
    
*   Docker
    

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

●       **GitHub Repository:** [https://github.com/SuchiiJain/CS4485\_Capstone](https://github.com/SuchiiJain/CS4485_Capstone)

●       **Jira**: [https://cs4485-team2.atlassian.net/jira/software/projects/SCRUM/summary](https://cs4485-team2.atlassian.net/jira/software/projects/SCRUM/summary)

●       **Design Document:**  https://www.figma.com/buzz/mL6QjBH9IeETv4zAOJ3g94/CS4485-Project?t=oaZD6SpJSEi8n9Ey-1
