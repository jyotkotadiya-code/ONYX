# Local Model & Hardware Discovery Report

**Generated:** 2026-10-07  
**Workspace:** `c:\Users\devik\Desktop\rag`

---

## 1. Executive Summary (`LOCAL AI ENVIRONMENT FOUND`)

```text
LOCAL AI ENVIRONMENT FOUND

LLM Runtime:               Ollama (Previously installed; binary currently uninstalled, installer found at C:\Users\devik\Downloads\OllamaSetup.exe)
Model:                     hf.co/bartowski/Llama-3.1-8B-Lexi-Uncensored-V2-GGUF:Q4_K_M
Model Size:                ~4.9 GB (8B parameters)
Quantization:              Q4_K_M (4-bit K-quantization, Medium)
Endpoint:                  http://localhost:11434 (Native Ollama API) / http://localhost:11434/v1 (OpenAI-Compatible API)
GPU:                       NVIDIA GeForce RTX 3050 Laptop GPU + Intel UHD Graphics
VRAM:                      4,096 MiB (4 GB Dedicated GDDR6)
RAM:                       8.0 GB System RAM (8,315,162,624 bytes)
CPU:                       11th Gen Intel(R) Core(TM) i5-11400H @ 2.70GHz (6 Cores / 12 Logical Processors)
OS:                        Windows 11 (x64)
Embedding Recommendation:  intfloat/multilingual-e5-small (118M params, ~470 MB, CPU execution to preserve 4GB GPU VRAM for Llama)
Vector DB Recommendation:  ChromaDB (Persistent local storage at ./data/vector_db)
OCR Recommendation:        RapidOCR (ONNX Runtime CPU) + Tesseract OCR fallback (for English, Hindi, Gujarati)
Audio Recommendation:      faster-whisper (base/small int8 on CPU) — Optional Phase 2
```

---

## 2. Detailed Hardware Inspection

| Component | Detected Specification | Architectural Impact |
| :--- | :--- | :--- |
| **CPU** | 11th Gen Intel Core i5-11400H @ 2.70GHz (6C / 12T) | Strong multi-threaded CPU performance for document parsing, ONNX/CPU embeddings, and OCR. |
| **System RAM** | 8.0 GB (~7.74 GiB usable) | **Critical constraint.** Must avoid loading bloated models in Python while Ollama runs. |
| **Discrete GPU** | NVIDIA GeForce RTX 3050 Laptop GPU | Supports CUDA (Driver 610.62, CUDA 13.3). |
| **VRAM** | 4,096 MiB (4.0 GB) | **Critical constraint.** An 8B Q4_K_M model (~4.9 GB) uses partial GPU offloading in Ollama (filling ~3.5 GB VRAM + ~1.5 GB system RAM). Therefore, **embedding and OCR models MUST run on CPU** so they never compete with Ollama for the 4 GB VRAM. |
| **Storage** | `C:\` (185 GB free of 451 GB NVMe), `D:\` (28.5 GB free of 64 GB) | Ample NVMe SSD storage on `C:\` for local vector DB, uploads, and model caches. |
| **Python** | Python 3.12.1 (`C:\Users\devik\AppData\Local\Programs\Python\Python312`) | `torch 2.12.1+cpu`, `transformers 5.12.1`, `pdfplumber`, `pypdfium2`, `python-docx`, `lxml`, `defusedxml`, `argon2-cffi` already installed globally. |
| **Node.js** | v24.13.0 | Ready for frontend build and dev server. |

---

## 3. Local LLM Runtime & Model Discovery Findings

### What Was Found on Your PC

1. **Previous Model Reference (`C:\Users\devik\Desktop\lexi.txt` & Assistant Project):**
   - Exact command recorded on Desktop:
     ```powershell
     ollama run hf.co/bartowski/Llama-3.1-8B-Lexi-Uncensored-V2-GGUF:Q4_K_M
     ```
   - Model Architecture: **Llama 3.1 8B** (`Llama-3.1-8B-Lexi-Uncensored-V2-GGUF`)
   - Quantization: **`Q4_K_M`** (~4.92 GB GGUF)
   - Endpoints used by your existing projects (`Vibhu` / `GeMi`):
     - Native Ollama Chat API: `http://localhost:11434/api/chat`
     - OpenAI-Compatible API: `http://localhost:11434/v1`

2. **Current State of Ollama on Disk:**
   - **Installer Present:** `C:\Users\devik\Downloads\OllamaSetup.exe` (1.17 GB, downloaded March 12, 2026).
   - **Config & Keys Present:** `C:\Users\devik\.ollama\id_ed25519` and `C:\Users\devik\.ollama\models` (last modified April 9, 2026).
   - **WebView Cache Present:** `C:\Users\devik\AppData\Roaming\ollama app.exe`.
   - **PATH Entry Present:** `C:\Users\devik\AppData\Local\Programs\Ollama` is in your User `PATH`.
   - **Current Status:** The `C:\Users\devik\AppData\Local\Programs\Ollama` binary directory was uninstalled/cleaned, and `C:\Users\devik\.ollama\models` is currently empty (0 bytes—no `.gguf` blobs are currently on `C:\` or `D:\`), so port `11434` is not currently listening.

3. **Other Runtimes Checked:**
   - **LM Studio (`localhost:1234`)**: Not installed, not running.
   - **llama.cpp (`llama-server`, `llama-cli`)**: Not installed, no `.gguf` files currently on `C:\` or `D:\`.
   - **LocalAI / vLLM / KoboldCpp / text-generation-webui**: Not installed.

### How the RAG Application Connects to Your Model

- The RAG backend connects via environment variables in `.env`:
  ```env
  LLM_PROVIDER=ollama
  LLM_MODEL=hf.co/bartowski/Llama-3.1-8B-Lexi-Uncensored-V2-GGUF:Q4_K_M
  LLM_BASE_URL=http://localhost:11434/v1
  OLLAMA_NATIVE_URL=http://localhost:11434
  ```
- **Dynamic Auto-Detection:** On startup and in `/api/models` & `/api/system/status`, the backend queries `http://127.0.0.1:11434/api/tags` (and `http://127.0.0.1:1234/v1/models` as fallback).
  - If `hf.co/bartowski/Llama-3.1-8B-Lexi-Uncensored-V2-GGUF:Q4_K_M` is present, it uses it automatically.
  - If another Llama model is loaded in Ollama, it automatically adapts to the available model without modifying or replacing your setup.
  - If Ollama is offline or needs to be re-installed from `C:\Users\devik\Downloads\OllamaSetup.exe`, the System Health dashboard and `scripts/check_environment.ps1` clearly report the status and exact one-line command to restore it.

---

## 4. Hardware-Aware Model & Component Selection

Because your system has **8 GB RAM** and **4 GB VRAM** (RTX 3050 Laptop GPU):

1. **Generation LLM (GPU + System RAM via Ollama):**
   - Model: `hf.co/bartowski/Llama-3.1-8B-Lexi-Uncensored-V2-GGUF:Q4_K_M` (or if you need to re-pull and want faster 100% VRAM fit on 4GB VRAM, `llama3.2:3b` is also supported seamlessly).
   - Runs in Ollama's isolated process (`127.0.0.1:11434`).

2. **Embedding Model (Dedicated CPU execution):**
   - Selected Model: **`intfloat/multilingual-e5-small`** (384 dimensions, ~118M parameters).
   - **Why:**
     - Supports **English, Hindi, and Gujarati** natively (unlike `bge-small-en-v1.5` which is English-only).
     - Extremely fast on your 6-core i5-11400H CPU.
     - Uses `< 450 MB` RAM and **0 MB GPU VRAM**, preventing CUDA Out-Of-Memory (OOM) errors while Ollama runs your 8B Llama model.

3. **Vector Database:**
   - **ChromaDB** (`PersistentClient` stored at `./data/vector_db`).
   - Runs embedded inside the Python backend process—zero extra Docker/server RAM overhead.

4. **OCR Engine:**
   - Primary: **`rapidocr-onnxruntime`** (100% local PaddleOCR models converted to lightweight ONNX Runtime on CPU—works out-of-the-box without external Windows binary installers) + **`pytesseract` (Tesseract OCR)** integration when the Windows Tesseract binary (`C:\Program Files\Tesseract-OCR\tesseract.exe`) is installed for Hindi/Gujarati (`eng+hin+guj`).
   - PDF Rendering: **`pypdfium2` / `PyMuPDF (fitz)`** for fast native PDF text extraction, table extraction (`pdfplumber`), and page-to-image rendering for scanned PDFs.

5. **Audio Transcription (Optional Phase 2):**
   - **`faster-whisper`** (`tiny` or `base` model with `int8` quantization on CPU). Lazy-loaded only when an audio file is uploaded and `AUDIO_ENABLED=true`, then unloaded after transcription to free RAM.
