# 🔥 FLAME AI
### Fire Learning and Analysis for Microgravity Experiments

<p align="center">
  <strong>Turning NASA's Microgravity Combustion Research into Actionable Scientific Insights.</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/NASA-Space_Apps_Challenge_2026-0B3D91?style=for-the-badge&logo=nasa&logoColor=white" alt="NASA Space Apps Challenge 2026"/>
  <img src="https://img.shields.io/badge/Challenge-07%20%7C%20Flame%20in%20Freefall-FF6B35?style=for-the-badge" alt="Flame in Freefall"/>
  <img src="https://img.shields.io/badge/Status-In%20Development-orange?style=for-the-badge" alt="In Development"/>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/React-20232A?style=flat-square&logo=react&logoColor=61DAFB"/>
  <img src="https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white"/>
  <img src="https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white"/>
  <img src="https://img.shields.io/badge/MySQL-4479A1?style=flat-square&logo=mysql&logoColor=white"/>
  <img src="https://img.shields.io/badge/Tailwind_CSS-06B6D4?style=flat-square&logo=tailwindcss&logoColor=white"/>
  <img src="https://img.shields.io/badge/FAISS-Vector_Search-7B61FF?style=flat-square"/>
</p>

---

## 🌌 Overview

**FLAME AI** is an AI-powered research and analytics platform designed to make microgravity combustion research more accessible, searchable, and understandable.

Developed for **NASA Space Apps Challenge 2026 — Challenge 07: Flame in Freefall**, the project addresses the challenge of exploring extensive scientific datasets and research documents related to combustion in microgravity environments.

By combining data engineering, scientific visualization, and Retrieval-Augmented Generation (RAG), FLAME AI aims to help researchers explore experiments, compare combustion conditions, discover documented findings, and investigate their implications for spacecraft fire safety.

Our mission is to transform complex scientific information into accessible, evidence-based research insights.

## 🚀 The Problem

Combustion behaves differently in microgravity than it does under Earth's gravity. Understanding these differences is important for spacecraft fire safety and future space exploration.

NASA has accumulated extensive microgravity combustion research data, including experiment records, measurements, technical reports, and supporting documentation.

However, navigating large collections of heterogeneous scientific information can be challenging.

Researchers need an accessible way to:

- Discover relevant combustion experiments.
- Explore experimental conditions and measurements.
- Compare results across investigations.
- Retrieve relevant information from scientific documents.
- Understand documented observations and research gaps.

## 💡 Our Solution

FLAME AI brings experiment exploration, scientific data analysis, and AI-assisted research into one integrated platform.

### ✨ Core Features

| Feature | Description |
|---|---|
| 🌍 Mission Overview | Explore indexed experiments, research programs, and data availability through an interactive dashboard. |
| 🔬 Experiment Explorer | Search and filter combustion experiments using available metadata and experimental conditions. |
| 🤖 AI Research Assistant | Ask natural-language questions and retrieve evidence-based answers from indexed NASA research documents. |
| 📊 Comparison Lab | Compare experiment conditions, measurements, and documented observations. |
| 🔥 Fire Safety Insights | Explore scientific observations, research patterns, and potential implications for spacecraft fire safety. |
| 🧪 Data Quality Monitor | Identify missing values, processing status, and limitations in the available datasets. |

## 🧠 AI-Powered Research

FLAME AI uses a Retrieval-Augmented Generation (RAG) approach to ground AI responses in relevant scientific documents.

### How it works

```text
         NASA Research Documents
                    |
                    v
             Text Extraction
                    |
                    v
              Text Chunking
                    |
                    v
             Embedding Model
                    |
                    v
             FAISS Vector Index
                    |
                    v
              Semantic Search
                    |
                    v
          Relevant Research Evidence
                    |
                    v
              Language Model
                    |
                    v
          Evidence-Based AI Answer
                    |
                    v
          Sources and Citations
```

The assistant is designed to distinguish between documented experimental observations, conclusions from original research, and AI-generated interpretations.

It should also communicate when available evidence is insufficient to answer a question.

## 🏗️ System Architecture

```text
                 NASA DATA SOURCES
                         |
          +--------------+--------------+
          |              |              |
       NASA PSI       NASA NTRS     Supplied NASA
      Repository     Publications    Data Archive
          |              |              |
          +--------------+--------------+
                         |
                  DATA ENGINEERING
                         |
             Python Extraction & Cleaning
                         |
          +--------------+--------------+
          |              |              |
        MySQL         Parquet       File Storage
      Metadata       Datasets      Original Files
          |              |              |
          +--------------+--------------+
                         |
                   AI ENGINE
                         |
              Embeddings + FAISS
                         |
                  RAG Pipeline
                         |
                   FastAPI
                         |
                  React Frontend
                         |
          +--------------+--------------+
          |              |              |
       Explorer      AI Assistant    Analytics
          |              |              |
          +--------------+--------------+
                         |
                  FLAME AI DASHBOARD
```

## 🛠️ Technology Stack

### Frontend
- **React.js** — Component-based user interface.
- **Vite** — Frontend development and build tooling.
- **Tailwind CSS** — Responsive interface styling.
- **Plotly.js** — Interactive scientific visualizations.

### Backend
- **Python** — Core backend and data processing language.
- **FastAPI** — REST API development.
- **MySQL 8** — Relational database for experiment metadata and structured records.

### Data Engineering
- **Pandas** — Data extraction, transformation, and cleaning.
- **PyArrow** — Efficient columnar data processing.
- **Parquet** — Storage format for processed datasets.

### Artificial Intelligence
- **Sentence Transformers** — Text embeddings.
- **FAISS** — Vector similarity search.
- **RAG** — Evidence-grounded question answering.
- **LLM API or local model** — Natural-language research assistance.

## 📂 Repository Structure

```text
flame-ai/
│
├── frontend/                 # React dashboard
│   ├── public/
│   └── src/
│       ├── assets/
│       ├── components/
│       ├── layouts/
│       ├── pages/
│       ├── services/
│       └── App.jsx
│
├── backend/                  # FastAPI application
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── database/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── main.py
│   └── tests/
│
├── data-engine/              # NASA data processing
│   ├── scripts/
│   ├── extract/
│   ├── cleaning/
│   └── validation/
│
├── ai-engine/                # AI and RAG pipeline
│   ├── embeddings/
│   ├── retrieval/
│   ├── vector_store/
│   └── assistant/
│
├── sample-data/              # Authorized demo samples
│
├── docs/                     # Technical documentation
│   ├── architecture/
│   ├── database/
│   └── api/
│
├── .github/                  # GitHub workflows and templates
│
├── .env.example
├── .gitignore
├── LICENSE
└── README.md
```

## 📡 NASA Data Sources

Our project is designed around NASA scientific research and supporting documentation.

| Source | Purpose |
|---|---|
| [NASA Physical Sciences Informatics (PSI)](https://psi.nasa.gov/physci/repo/) | Primary source for physical-science experiment records and datasets. |
| [NASA Technical Reports Server (NTRS)](https://ntrs.nasa.gov/) | Scientific reports, publications, and supporting research. |
| [NASA Science Data Resources](https://science.nasa.gov/learn/entry-points-to-nasa-data/) | Additional entry points to NASA scientific data. |

Relevant combustion research programs may include **SAFFIRE, FLEX, BASS, and ACME**, subject to the experiment records available in the supplied datasets and NASA repositories.

## 📊 Scientific Data Integrity

Scientific accuracy is central to FLAME AI.

Our data-handling principles include:

- Preserve original NASA files and source references.
- Retain original measurement values and units.
- Track transformations during data cleaning.
- Distinguish missing values from measured zero values.
- Avoid comparing measurements with incompatible units or experimental conditions.
- Clearly identify AI-generated interpretations.
- Link research answers to their supporting sources whenever available.

## ⚙️ Getting Started

### Prerequisites

- Python 3.10+
- Node.js and npm
- MySQL 8+
- Git

### Clone the repository

```bash
git clone https://github.com/YOUR-USERNAME/flame-ai.git
cd flame-ai
```

### Backend setup

```bash
cd backend

python -m venv venv
```

Activate the environment:

**Windows**
```bash
venv\Scripts\activate
```

**macOS / Linux**
```bash
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the API:

```bash
uvicorn app.main:app --reload
```

API documentation:

```text
http://127.0.0.1:8000/docs
```

### Frontend setup

```bash
cd frontend
npm install
npm run dev
```

### Environment Configuration

Create a local `.env` file using `.env.example`.

Never commit API keys, database passwords, credentials, or private NASA datasets.

> Full setup instructions will be expanded as the project implementation progresses.

## 👥 Meet the Team

Built with curiosity, collaboration, and a passion for space technology.

<table>
  <tr>
    <td align="center">
      <strong>👩‍💻 Hana Shaimi</strong><br/>
      <sub>Frontend Developer</sub><br/>
      <sub>React UI · Dashboard · User Experience</sub>
    </td>
    <td align="center">
      <strong>⚙️ Majdoline Elbennadi</strong><br/>
      <sub>Backend & API Developer</sub><br/>
      <sub>FastAPI · MySQL · REST APIs</sub>
    </td>
  </tr>
  <tr>
    <td align="center">
      <strong>🤖 Abdallah Aboudrari</strong><br/>
      <sub>AI Assistant Engineer</sub><br/>
      <sub>RAG · Embeddings · FAISS · AI Integration</sub>
    </td>
    <td align="center">
      <strong>📊 Adam Elboudali Zahid</strong><br/>
      <sub>Data Analyst</sub><br/>
      <sub>NASA Data · Data Cleaning · Analysis</sub>
    </td>
  </tr>
</table>

## 🌠 Our Mission

We believe that making scientific knowledge more accessible can help accelerate research and support safer human exploration of space.

**FLAME AI — Bringing clarity to combustion research, one experiment at a time.**

---

<p align="center">
  <strong>🔥 FLAME AI</strong><br/>
  NASA Space Apps Challenge 2026<br/>
  Challenge 07 — Flame in Freefall
</p>

<p align="center">
  <sub>Built by our team with a passion for AI, science, and space exploration. 🚀</sub>
</p>
