# Corrected Calcium Calculator

> **Domain:** Clinical Decision Support & Biomedical Computing  
> **Reference Guidelines & Standards:** `Standard Clinical Formulations & ISO/IEC Quality Frameworks`

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg?logo=fastapi&logoColor=white)
![Audit Trail](https://img.shields.io/badge/Audit-HMAC--SHA256_Tamper--Evident-brightgreen.svg)
![Zero-PHI Guard](https://img.shields.io/badge/Guard-Zero--PHI_Outbound-blue.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)

</div>

---

## 📖 What It Does

Corrected Calcium Calculator & Calcium-Phosphate Mineral Metabolism Engine
-------------------------------------------------------------------------
Implements Payne albumin-corrected calcium, Orrell/Figge total protein correction,
estimated free ionized calcium, calcium-phosphate product (calciphylaxis risk),
and emergency clinical management tiers for hypo/hypercalcemia.

Domain: Endocrinology / Clinical Chemistry / Nephrology
Standards: KDIGO Mineral & Bone Disorder (MBD) / Endocrine Society Clinical Guidelines

---

## ⚙️ Key Capabilities & Algorithmic Modules

### 🔬 Core Algorithmic & Evaluation Engines

- **`CalciumCalculationResult`**: Complete diagnostic panel for serum calcium adjustments.
- **`CorrectedCalciumEngine`**: Core mathematical engine for albumin, protein, and phosphate mineral metabolism.

---

## 📐 Mathematical Formulation & Logic

```text
  Payne formula (1973):
  Payne formula in SI units:
  Orrell / Parfitt formula for total protein-adjusted calcium:
  risk = "CRITICAL_CALCIPHYLAXIS_RISK"
  risk = "ELEVATED_CALCIFICATION_RISK"
```

---

## 💻 CLI Quickstart & Usage

### 1. Calculate Corrected Calcium
```bash
# Basic calculation (calcium + albumin)
python -m corrected_calcium calc --calcium 8.0 --albumin 2.5

# Full panel with protein and phosphate
python -m corrected_calcium calc --calcium 8.0 --albumin 2.5 --protein 7.0 --phosphate 4.5

# JSON output
python -m corrected_calcium calc --calcium 14.5 --albumin 4.0 --json
```

### 2. Batch Processing (CSV)
```bash
python -m corrected_calcium batch -i input.csv -o results.csv
```

**Expected CSV columns:** `calcium`, `albumin`, `protein` (optional), `phosphate` (optional)

### 3. Interactive Q&A
```bash
python -m corrected_calcium chat "What is the Payne formula?"
```

### 4. Enterprise Agent Supervisor (via cli.py)
```bash
python cli.py audit --task-id TASK-01
python cli.py chat "Explain calcium classification"
python cli.py verify-audit
python cli.py serve --host 127.0.0.1 --port 8000
```

---

## 🛡️ Security & Enterprise Architecture

* **Zero-PHI Outbound Interceptor:** Active AST and regex inspection blocking SSNs, MRNs, phone numbers, and patient identifiers.
* **Tamper-Evident HMAC-SHA256 Audit Trail:** Chained, cryptographically signed logs for every evaluation and state transition.
* **Air-Gapped LLM Reasoning Adapter:** Agnostic integration for local Ollama instances (`llama3`, `mistral`), Claude 3.5 Sonnet, GPT-4o, and deterministic test mocks.
* **Active Learning Bayesian Calibration:** Dynamic tracker updating worker reliability weights and monitoring Brier calibration drift.
* **FastAPI & Prometheus Telemetry:** Exposes OpenAPI 3.1 REST endpoints and operational Prometheus metrics (`/metrics`).

---

## 🧪 Testing & Verification

Run the automated test suite:

```bash
pytest -v
```

Execute high-throughput batch simulation benchmarks:

```bash
python simulator.py 1000
```

---

## 🐳 Container Deployment

```bash
docker build -t corrected-calcium-calculator .
docker run -p 8000:8000 corrected-calcium-calculator
```
