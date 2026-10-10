# ONYX — Enterprise Local Multimodal RAG Platform
## Master Technical Documentation & System Specification

---

## 1. Executive Overview & Problem Statement

### 1.1 Executive Summary
**ONYX** is an enterprise-grade, 100% air-gapped, privacy-first Multimodal Retrieval-Augmented Generation (RAG) platform. Engineered for highly regulated organizations—including banking, legal, defence, healthcare, and enterprise HR—ONYX enables teams to query complex unstructured and structured data without transmitting a single byte outside local premises.

Unlike public cloud AI solutions (OpenAI, Anthropic, Gemini) that present significant compliance risks, ONYX operates entirely on-premise:
- **Zero cloud API calls** (`OFFLINE_MODE = True`).
- **Zero telemetry or external tracking**.
- **100% local embedding and LLM inference**.
- **Multi-tenant cryptographic workspace isolation**.
- **Structured generative artifacts** (interactive tables, KPI cards, charts) instead of ungrounded walls of text.

### 1.2 Enterprise Pain Points Solved
1. **Data Sovereignty & Legal Compliance (GDPR, HIPAA, IT Act)**:
   Enterprises cannot legally transmit non-public intellectual property, employee compensation records, or financial balance sheets to third-party cloud servers. ONYX ensures complete physical data custody.
2. **Elimination of Critical LLM Hallucinations**:
   Standard LLM chat applications summarize tabular figures unpredictably and frequently mislabel financial categories (such as mistaking general revenue for employee payroll). ONYX enforces strict query grounding and domain verification before rendering any structured data.
3. **The "Wall of Text" Usability Barrier**:
   Corporate decision-makers require actionable artifacts—filterable data tables, dynamic charts, and verifiable citations—not 500-word conversational narratives.
4. **Lack of Tenant & Role Isolation in Traditional RAG**:
   Standard vector databases retrieve chunks based purely on mathematical cosine similarity, risking critical security breaches where an employee or intern accidentally retrieves executive compensation or board minutes. ONYX enforces multi-tenant workspace filtering at the database layer.

---

## 2. High-Level Architecture & Technical Stack

```
                              ┌──────────────────────────────────────────────┐
                              │            CLIENT / USER INTERFACE           │
                              │     React 18 + TypeScript + Tailwind CSS     │
                              │   Admin Console | Chat | Artifact Inspector  │
                              └──────────────────────┬───────────────────────┘
                                                     │ HTTP REST / Bearer JWT
                              ┌──────────────────────▼───────────────────────┐
                              │           FASTAPI BACKEND RUNTIME            │
                              ├──────────────────────────────────────────────┤
                              │ 1. Security & Identity Layer:                │
                              │    - JWT Auth with Token Versioning (tv)     │
                              │    - Role-Based Access Control (RBAC)        │
                              │    - Workspace Isolation Middleware          │
                              │    - Tamper-Evident Audit Logging            │
                              ├──────────────────────────────────────────────┤
                              │ 2. Multimodal Ingestion Pipeline:            │
                              │    - PDF Parser (PyMuPDF / Table Extractor)  │
                              │    - OCR Engine (Tesseract: eng+hin+guj)     │
                              │    - Relational DB Parser (SQLite Inspector) │
                              │    - Document & Text Chunker (800/120 split) │
                              ├──────────────────────────────────────────────┤
                              │ 3. Hybrid Retrieval & Search:                │
                              │    - Dense Vector Search (ChromaDB)          │
                              │    - Sparse Lexical Search (BM25)            │
                              │    - Reciprocal Rank Fusion (RRF)            │
                              ├──────────────────────────────────────────────┤
                              │ 4. Response Planning & Safety Guardrails:    │
                              │    - Query Intent & Domain Classifier        │
                              │    - Anti-Hallucination Grounding Validator  │
                              │    - Universal Raw Table Extractor           │
                              │    - Deterministic Arithmetic Calculator     │
                              └──────────────────────┬───────────────────────┘
                                                     │ Local Inference (127.0.0.1:11434)
                              ┌──────────────────────▼───────────────────────┐
                              │            LOCAL AI & STORAGE ENGINE         │
                              │  - Ollama (Llama-3.1-8B-Q4_K_M)              │
                              │  - multilingual-e5-small Embeddings (CPU)    │
                              │  - ChromaDB Persistent Vector Storage        │
                              │  - SQLite Relational Metadata Store (WAL)    │
                              └──────────────────────────────────────────────┘
```

### Complete Component Stack
| Component | Implementation | Version / Specification | Key Functionality |
| :--- | :--- | :--- | :--- |
| **Frontend Framework** | React + Vite | React 18.x, TypeScript 5.x | High-performance SPA with enterprise design system. |
| **Styling & Icons** | Tailwind CSS + Lucide React | Tailwind 3.x, Lucide 0.3x | Dark-mode interface, responsive grids, and accessible UI controls. |
| **Backend Framework** | FastAPI + Uvicorn | Python 3.12, ASGI Uvicorn | Asynchronous, non-blocking REST API with auto-generated OpenAPI docs. |
| **Validation Layer** | Pydantic v2 | Pydantic 2.x | Strict schema enforcement on all API requests and JSON response blocks. |
| **Dense Embeddings** | SentenceTransformers | `intfloat/multilingual-e5-small` | 384-dimensional dense vectors supporting multilingual semantics (English, Hindi, Gujarati). |
| **Vector Database** | ChromaDB | Chroma 0.4+ Persistent | Embeddings stored on disk at `./data/vector_db`, filtered by `workspace_id`. |
| **Relational Database**| SQLite with WAL mode | Python standard `sqlite3` | Users, roles, workspace memberships, document metadata, audit logs at `./data/metadata/app.db`. |
| **Local LLM Engine** | Ollama / GGUF | `Llama-3.1-8B-Lexi-Uncensored-V2-GGUF:Q4_K_M` | Local 4-bit quantized generative model running locally without cloud dependence. |
| **OCR Subsystem** | Tesseract OCR | Tesseract 5.x (`eng+hin+guj`) | Multilingual text recognition for scanned receipts, invoices, and documents. |
| **PDF Extraction** | PyMuPDF (`fitz`) | PyMuPDF 1.23+ | Rapid parsing of native vector text, formatting hierarchy, and table rows. |
| **Testing Suite** | Pytest + AnyIO + AsyncIO | Pytest 9.x | 23 comprehensive tests ensuring 100% passing status across auth, RAG, and isolation. |

---

## 3. Multimodal Ingestion Pipeline (The 4 Active Modalities)

To deliver high-reliability performance and prevent parser fragility, ONYX eliminates non-essential converters and focuses strictly on **4 universal enterprise modalities**:

```
                         Uploaded Document
                                 │
           ┌─────────────────────┼─────────────────────┬─────────────────────┐
           ▼                     ▼                     ▼                     ▼
        [ PDF ]             [ Images ]            [ Database ]          [ Text / Docs ]
   (PyMuPDF / Tables)    (OCR / Tesseract)    (SQLite Schema & Rows)   (Markdown, CSV, TXT)
           │                     │                     │                     │
           └─────────────────────┼─────────────────────┴─────────────────────┘
                                 ▼
                     Structure-Aware Chunker
               (800 chars / 120 chars overlap)
                                 │
                                 ▼
                   SentenceTransformer Embedder
                  (multilingual-e5-small, 384-D)
                                 │
                                 ▼
                   ChromaDB Vector Storage + SQLite
              (Scoped with workspace_id & document_id)
```

### 3.1 PDF Parser (`backend/ingestion/pdf_parser.py`)
- **Native Text & Hierarchy Extraction**: Parses headings, paragraphs, and numbered clauses via `fitz.open()`.
- **Table Detection**: Analyzes table grid structures and formats row-column relationships into standardized markdown tables.
- **Page Metadata Preservation**: Every generated chunk retains `page_number` and `document_id` metadata to enable verifiable source citations.

### 3.2 OCR Image Parser (`backend/ingestion/ocr.py` & `image_parser.py`)
- **Supported Formats**: `.png`, `.jpg`, `.jpeg`, `.tiff`, `.bmp`.
- **Pre-processing**: Uses Pillow for grayscale conversion, adaptive contrast enhancement, and noise reduction prior to OCR.
- **Multilingual Support**: Invokes Tesseract with `-l eng+hin+guj` to parse invoices, receipts, and forms written in English and regional Indian languages.

### 3.3 Database Parser (`backend/ingestion/database_parser.py`)
- **Supported Databases**: SQLite databases (`.db`, `.sqlite`).
- **Schema Extraction**: Reads `sqlite_master` to catalog table names, column data types, primary keys, and foreign key relations.
- **Row Serialization**: Serializes individual database records into structured text blocks while preserving relational integrity.
- **Security Guardrail**: Integrates `sql_validator.py` to prevent arbitrary SQL execution or injection vulnerabilities.

### 3.4 Structured Text & Document Parser (`backend/ingestion/doc_parser.py`)
- **Supported Formats**: `.txt`, `.md`, `.csv`, `.tsv`.
- **Boundary Preservation**: Chunks text at natural paragraph and table boundaries using an 800-character window with a 120-character sliding overlap (`chunker.py`).

---

## 4. Hybrid Retrieval & Search Architecture

ONYX does not rely exclusively on vector embeddings, as semantic vectors alone struggle with exact numeric IDs, employee numbers, and financial invoice codes.

```
                           User Query
                               │
               ┌───────────────┴───────────────┐
               ▼                               ▼
       Dense Vector Search            Sparse Lexical Search
    (Cosine similarity via            (BM25 keyword matching
     multilingual-e5-small)             on indexed tokens)
               │                               │
               └───────────────┬───────────────┘
                               ▼
                   Reciprocal Rank Fusion (RRF)
                     Score Blending Algorithm
                               │
                               ▼
                   Top-K Grounded Chunks
             (Enforced: where workspace_id = user_wid)
```

### 4.1 Dense Vector Search
- The query string is passed through `multilingual-e5-small` to generate a 384-dimensional query vector.
- ChromaDB performs cosine similarity retrieval over all chunks matching the user's active `workspace_id`.

### 4.2 Sparse Lexical Search (BM25)
- An in-memory BM25 index scores documents based on exact keyword frequencies.
- Essential for retrieving specific invoice numbers (e.g. `INV-2026-8831`), employee IDs (`EMP-501`), or monetary values (`₹42,000`).

### 4.3 Reciprocal Rank Fusion (RRF)
- Combines ranked results from dense and sparse retrievers using the standard RRF formula:
  $$\text{RRF Score} = \sum \frac{1}{60 + \text{Rank}}$$
- Ensures that documents with exact keyword matches and high semantic relevance receive top priority.

---

## 5. Anti-Hallucination, Deterministic Math & Response Planning

The response engine is located in `backend/response/` and consists of 4 specialized layers:

### 5.1 Query Intent Classification (`planner.py`)
Incoming queries are classified into specific operational categories:
- **Informational**: Conceptual questions requiring direct narrative synthesis.
- **Tabular / Breakdown**: Queries requesting structured lists or breakdowns.
- **Quantitative / Calculation**: Questions asking for sums, percentages, or margins.
- **Restricted Domain (e.g. Salary / Payroll)**: Queries requesting sensitive compensation information.

### 5.2 Anti-Hallucination & Salary Grounding Guardrail
- **Problem Solved**: Standard RAG models commonly take any numerical table (e.g., monthly company revenue) and present it as employee salary data when asked a payroll query.
- **ONYX Solution**: When a query pertains to salaries (`is_salary_query`), the planner validates whether the retrieved chunks contain genuine employee compensation fields (`salary`, `compensation`, `payroll`, `stipend`, employee names).
- **Fallback Action**: If no genuine salary data exists in the workspace, the planner outputs a clear, truthful response:
  > *"I couldn't find any employee salary or payroll records in the uploaded knowledge base."*
  It explicitly rejects attaching unrelated financial tables.

### 5.3 Universal Raw Table Extractor (`Pattern H` in `renderer_data.py`)
- Standard systems force tables into rigid, pre-defined templates.
- ONYX dynamically inspects the raw markdown tables extracted from uploaded PDFs and spreadsheets. It extracts the **exact column headers as authored in the source document** (e.g., `Month | Revenue (INR) | Expenses (INR) | Profit (INR)`), ensuring authentic representation without hallucinated column names.

### 5.4 Deterministic Calculator (`calculator.py`)
- LLMs are notoriously prone to arithmetic errors.
- When queries require sums, differences, profit margins, or averages, ONYX runs the calculation through a deterministic Python arithmetic engine rather than relying on LLM-generated math.

---

## 6. Generative UI Artifacts & Component Architecture

ONYX replaces traditional chatbot text responses with structured generative blocks:

```json
{
  "summary": "In January 2024, total revenue was ₹42,000 against expenses of ₹28,000.",
  "components": [
    {
      "type": "stat_card",
      "data": { "label": "January 2024 Revenue", "value": "₹42,000", "trend": "+12.5%" }
    },
    {
      "type": "data_table",
      "title": "Monthly Financial Performance (2024)",
      "data": {
        "headers": ["Month", "Revenue (INR)", "Expenses (INR)", "Profit (INR)"],
        "rows": [["Jan 2024", "₹42,000", "₹28,000", "₹14,000"]]
      }
    },
    {
      "type": "chart",
      "chart_type": "bar",
      "title": "Monthly Revenue vs Expenses",
      "data": { "labels": ["Jan 2024"], "datasets": [...] }
    },
    {
      "type": "source_card",
      "data": { "document_name": "Annual_Report_2024.pdf", "page": 4, "score": 0.94 }
    }
  ]
}
```

### Supported Component Types
1. **StatCard (`StatCard.tsx`)**: Prominent KPI cards displaying key metrics, currency amounts, and percentage changes.
2. **DataTable (`DataTable.tsx`)**: Responsive, paginated data grid with column sorting and export capability.
3. **Artifact View Button & Modal**: Embedded directly within messages. Clicking **View Artifact** opens a full-screen interactive modal allowing users to inspect complex tables and charts.
4. **ChartRenderer (`ChartRenderer.tsx`)**: Renders dynamic Bar charts, Line charts, and Pie charts directly from structured JSON datasets.
5. **Comparison (`Comparison.tsx`)**: Side-by-side comparative matrices for evaluating multiple options, periods, or vendors.
6. **Timeline (`Timeline.tsx`)**: Chronological event streams for audit logs or project milestones.
7. **SourceCard (`SourceCard.tsx`)**: Verifiable citation card showing the source document, page number, and similarity confidence score.

---

## 7. Enterprise Security, Multi-Tenancy & RBAC

```
                    Role-Based Access Control (RBAC) Matrix
┌─────────────┬─────────────────┬────────────────┬─────────────────┬────────────────┐
│ Capability  │ Admin           │ Manager        │ Employee        │ Viewer         │
├─────────────┼─────────────────┼────────────────┼─────────────────┼────────────────┤
│ Manage Users│ Full (Add/Revoke│ None           │ None            │ None           │
│ Manage Work │ Full (CRUD)     │ Workspace Only │ None            │ None           │
│ Upload Docs │ All Workspaces  │ Permitted Only │ Permitted Only  │ None           │
│ Delete Docs │ All Workspaces  │ Permitted Only │ Own Docs Only   │ None           │
│ Query RAG   │ All Workspaces  │ Permitted Only │ Permitted Only  │ Permitted Only │
│ View Audit  │ Global Logs     │ Workspace Only │ None            │ None           │
└─────────────┴─────────────────┴────────────────┴─────────────────┴────────────────┘
```

### 7.1 Zero-Trust Token Invalidation
- Authentication tokens are HMAC-SHA256 signed JWTs containing user ID, role, workspace ID, and a **Token Version (`tv`)**.
- When an administrator modifies a user's role or revokes access, the `tv` integer in the database is incremented.
- Existing tokens immediately fail validation on subsequent requests with `HTTP 401 Unauthorized`, guaranteeing instantaneous access revocation.

### 7.2 Multi-Tenant Workspace Isolation
- Every document chunk in ChromaDB is indexed with metadata: `{"workspace_id": "<uuid>"}`.
- All RAG queries automatically inject `where={"workspace_id": user.workspace_id}` at the vector database level.
- Cross-tenant data leakage is mathematically impossible at the database query layer.

### 7.3 Tamper-Evident Audit Logging (`backend/auth/audit.py`)
- Every sensitive event (logins, uploads, deletions, workspace changes, and queries) is logged to the SQLite database and persistent log files.
- Log entries capture: `timestamp`, `user_id`, `role`, `workspace_id`, `action`, `resource`, `status`, and `ip_address`.

### 7.4 Protection Against Common Attacks
- **Path Traversal**: Filenames are sanitized via SHA-256 content hashing. Directory traversal sequences (`../`, `..\\`) are rejected.
- **Direct File Download Prevention**: Frontend static asset routing explicitly blocks requests matching `uploads/*` or `secure_uploads/*` with `HTTP 403 Forbidden`. Documents can only be downloaded via authenticated API endpoints with document-level ownership checks.
- **SQL Injection**: All SQLite queries use parameterized queries (`?`). User inputs are never concatenated into SQL strings.

---

## 8. Database Schema Specification (`data/metadata/app.db`)

```sql
-- Workspaces (Tenant Isolation)
CREATE TABLE workspaces (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Users & Credentials
CREATE TABLE users (
    id TEXT PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'employee', -- admin, manager, employee, viewer
    workspace_id TEXT REFERENCES workspaces(id),
    token_version INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Document Metadata Registry
CREATE TABLE documents (
    id TEXT PRIMARY KEY,
    workspace_id TEXT REFERENCES workspaces(id),
    filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_hash TEXT NOT NULL,
    file_size_bytes INTEGER NOT NULL,
    modality TEXT NOT NULL, -- pdf, ocr_image, database, text
    chunk_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'Ready',
    uploaded_by TEXT REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Audit Trails
CREATE TABLE audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id TEXT,
    role TEXT,
    workspace_id TEXT,
    action TEXT NOT NULL,
    resource TEXT,
    success BOOLEAN NOT NULL,
    ip_address TEXT,
    severity TEXT DEFAULT 'INFO'
);
```

---

## 9. Operations, Installation & Verification Guide

### 9.1 Prerequisites
- **Operating System**: Windows 10/11, Linux, or macOS.
- **Python**: Python 3.12+ (64-bit).
- **Node.js**: v18.x or v20.x with npm.
- **OCR Engine**: Tesseract OCR installed locally (default Windows path: `C:\Program Files\Tesseract-OCR\tesseract.exe`).
- **Local LLM Engine**: Ollama running locally at `http://127.0.0.1:11434` with model `Llama-3.1-8B-Lexi-Uncensored-V2-GGUF:Q4_K_M`.

### 9.2 Starting the Backend Server
```bash
# Navigate to project root
cd c:\Users\devik\Desktop\rag

# Launch FastAPI ASGI server
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```
- API Base URL: `http://localhost:8000`
- Interactive OpenAPI Documentation: `http://localhost:8000/docs`

### 9.3 Starting the Frontend Server
```bash
# In a separate terminal
cd c:\Users\devik\Desktop\rag\frontend

# Start Vite dev server
npm run dev
```
- Web Application URL: `http://localhost:5173`

### 9.4 Running the Automated Test Suite
```bash
# Execute full backend test suite
python -m pytest
```
- **Test Results**: 23 tests collected, **23 passed (100% pass rate)**.
- Validates: JWT authentication, boot health checks, PDF/Image/DB ingestion, RBAC access policies, structured workspace routing, and multi-tenant vector isolation.

### 9.5 Default Credentials
- **System Administrator**: Username: `admin` | Default Password: `admin` (or configured admin secret).
- Full permissions to create/delete workspaces, manage organization members, review audit logs, and ingest documents.

---

## 10. Avenue Hackathon Live Presentation Script & Demo Playbook

### Step-by-Step 3-Minute Demo Playbook

| Minute | Stage | Action to Perform | Pitch Narrative to Judges |
| :---: | :--- | :--- | :--- |
| **0:00 - 0:45** | **The Air-Gap Proof** | Disconnect the laptop from Wi-Fi or activate Airplane Mode. | *"Judges, before we start: watch us cut our internet connection completely. Many enterprise solutions claim data privacy while secretly sending prompt tokens to OpenAI or Claude. ONYX runs 100% locally. Not one byte of your confidential data leaves this machine."* |
| **0:45 - 1:30** | **Enterprise Multi-Tenancy & RBAC** | Log into the portal as `admin`. Navigate to the Admin Workspace Console. | *"Enterprises aren't single-user. ONYX provides zero-trust RBAC and multi-tenant isolation. Admins can create isolated workspaces (Finance, Engineering, Legal) and grant granular permissions. If an employee is revoked, our token-versioning mechanism invalidates their active session immediately."* |
| **1:30 - 2:15** | **Multimodal Ingestion** | Upload a financial PDF containing monthly tabular data and an image receipt. | *"Notice our ingestion: we don't just read plain text. ONYX ingests complex PDFs with nested tables, scanned image invoices using multilingual Tesseract OCR in English and regional Indian languages, and relational database dumps."* |
| **2:15 - 2:45** | **Precision Query & Artifact View** | Ask: *'What was our revenue in January 2024 and show the financial breakdown?'* | *"Notice two critical differentiators: First, numerical precision down to the exact rupee (`₹42,000`). Second, instead of a wall of text, ONYX generates structured enterprise artifacts—KPI stat cards, and an interactive Artifact View button that reveals the full financial grid table."* |
| **2:45 - 3:00** | **The Anti-Hallucination Guardrail** | In a workspace containing only revenue data, query: *'What is our employee salary data?'* | *"Watch how ONYX handles out-of-domain queries: It truthfully reports that no employee salary records exist. It refuses to hallucinate, and it never mislabels revenue as salary. That is the definition of industry-grade reliability."* |

---

## 11. FAQ & Judges Defense Strategy

**Q: "Why didn't you just use cloud models with zero-retention agreements?"**
> **A:** *"In high-security defence, banking, and confidential M&A legal advisory, zero-retention promises are legally insufficient. Physical data custody is a strict compliance requirement. Furthermore, cloud APIs incur substantial recurring operational costs, latency, and dependency on external internet availability."*

**Q: "How do you achieve high retrieval accuracy without fine-tuning?"**
> **A:** *"We combine dense semantic retrieval (`multilingual-e5-small`) with sparse lexical matching (BM25) using Reciprocal Rank Fusion (RRF). Semantic vectors catch intent and context, while BM25 guarantees exact matching for invoice codes, employee IDs, and financial numbers."*

**Q: "How do you prevent hallucinations in calculations?"**
> **A:** *"We remove calculation responsibility from the LLM entirely. Our response planner routes arithmetic requests to an internal deterministic Python calculator engine, guaranteeing mathematical accuracy."*

**Q: "Can this system scale to hundreds of concurrent users in a large enterprise?"**
> **A:** *"Yes. FastAPI is fully asynchronous and stateless. For large-scale production deployments, the backend containerizes seamlessly via Docker, with ChromaDB backed by distributed storage and LLM inference routed through high-throughput on-premise GPU clusters (e.g., vLLM or Ollama instances)."*
