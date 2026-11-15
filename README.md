# 🔥 FLAME AI
### Fire Learning and Analysis for Microgravity Experiments

<p align="center">
  <strong>Making NASA microgravity combustion research easier to discover, explore, compare, and understand.</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/NASA-Space_Apps_Challenge_2026-0B3D91?style=for-the-badge&logo=nasa&logoColor=white" alt="NASA Space Apps Challenge 2026"/>
  <img src="https://img.shields.io/badge/Challenge-07%20%7C%20Flame%20in%20Freefall-FF6B35?style=for-the-badge" alt="Flame in Freefall"/>
  <img src="https://img.shields.io/badge/Status-In%20Development-orange?style=for-the-badge" alt="In Development"/>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/React-20232A?style=flat-square&logo=react&logoColor=61DAFB"/>
  <img src="https://img.shields.io/badge/Vite-646CFF?style=flat-square&logo=vite&logoColor=white"/>
  <img src="https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white"/>
  <img src="https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white"/>
  <img src="https://img.shields.io/badge/PostgreSQL-4169E1?style=flat-square&logo=postgresql&logoColor=white"/>
  <img src="https://img.shields.io/badge/Ollama-Local%20AI-black?style=flat-square"/>
</p>

---

## 🌌 Overview

**FLAME AI** is an AI-powered research exploration platform developed for **NASA Space Apps Challenge 2026 — Challenge 07: Flame in Freefall**.

The platform aims to make NASA's microgravity combustion research more accessible by bringing together a searchable investigation catalogue, research visualizations, experiment comparison, and an AI research assistant.

The AI assistant uses Retrieval-Augmented Generation (RAG) to retrieve relevant passages from indexed research documents and generate answers with source and page references.

Our mission is to transform complex scientific information into accessible, evidence-based research insights.

## 🚀 The Problem

Fire behaves differently in microgravity. Reduced buoyancy-driven convection can change flame shape, transport, and combustion-product behavior. Understanding these differences is important for spacecraft fire safety and future space exploration.

NASA research includes experiment records, technical reports, publications, and datasets. Finding relevant information across these sources and distinguishing measured observations from hypotheses or interpretations can be difficult.

Researchers need ways to:

- Discover relevant combustion investigations.
- Search research records and documents.
- Understand the context and conditions of experiments.
- Compare investigations without mixing incompatible conditions.
- Trace answers back to original sources.
- Identify gaps and limitations in available information.

## 💡 Our Solution

FLAME AI brings experiment exploration, research visualization, comparison, and AI-assisted research into one interface.

### ✨ Core Features

| Feature | Description |
|---|---|
| 🌍 Mission Overview | Explore the platform and its research collection. |
| 🔬 Research Explorer | Search, filter, and sort combustion investigation records using available metadata. |
| 📊 Research Analytics | Visualize catalogue distributions by research program, year, type, and status. |
| 🤖 AI Research Assistant | Ask natural-language questions and retrieve relevant passages from indexed research documents. |
| 🔍 Comparison | Select investigations and compare their available metadata and documented information. |
| 🔥 Fire Safety Insights | Explore research themes and navigate to related investigations. |
| 🧪 Data Quality | Examine record availability and processing status. |

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
          Embedding Generation
                  |
                  v
              Vector Store
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
           Sources and Pages
```

### Current AI components

- **FastAPI** — exposes the research assistant through HTTP endpoints.
- **Ollama** — runs local language and embedding models.
- **Qwen 3.5 4B** — configured local generation model in the development environment.
- **nomic-embed-text** — embedding model.
- **RAG** — retrieval-grounded question answering.
- **JSON vector store** — stores the current indexed research chunks.

The assistant is designed to distinguish between documented experimental observations, original research conclusions, and AI-generated interpretations. It should also communicate when available evidence is insufficient.

## 🏗️ System Architecture

```text
                NASA RESEARCH SOURCES
                         |
                         v
             DOCUMENTS & CATALOGUE DATA
                         |
           +-------------+-------------+
           |                           |
           v                           v
    CATALOGUE / API              DOCUMENT INGESTION
           |                           |
           v                           v
    Structured Records              Text Chunks
           |                           |
           v                           v
    Research Explorer              Embeddings
    Catalogue Analytics                |
    Comparison                         v
                                  Vector Store
                                       |
                                       v
                                  RAG Retrieval
                                       |
                                       v
                                   Local LLM
                                       |
                                       v
                                 AI Responses
           |                           |
           +-------------+-------------+
                         |
                         v
                   REACT FRONTEND
                         |
       +-----------------+-----------------+
       |                 |                 |
       v                 v                 v
    Explorer          Analytics       AI Assistant
       |                 |                 |
       +-----------------+-----------------+
                         |
                         v
                     FLAME AI
```

The catalogue API and AI assistant are separate backend responsibilities within the repository. Their final integration with the frontend is an ongoing team task.

## 🛠️ Technology Stack

### Frontend
- **React** — component-based user interface.
- **Vite** — frontend development and build tooling.
- **JavaScript / JSX** — application logic.
- **CSS** — custom interface styling.
- **Lucide React** — interface icons.

### Backend and APIs
- **Python** — backend and data processing.
- **FastAPI** — REST API development.
- **Pydantic** — request and data validation.
- **PostgreSQL** — relational database technology used by the project database components.

### Artificial Intelligence
- **Ollama** — local model runtime.
- **Qwen 3.5 4B** — local answer-generation model in the development setup.
- **nomic-embed-text** — text embedding model.
- **RAG** — evidence-grounded question answering.
- **JSON vector store** — persistence for indexed document chunks.

> The project is evolving. This list describes the technologies identified in the current implementation; it does not imply that every planned integration is complete or deployed.

## 📂 Repository Structure

```text
flame-ai/
│
├── AI/
│   ├── api/                    # Catalogue and other API modules
│   ├── analysis/               # Analysis utilities
│   ├── catalog/                # Investigation catalogue logic
│   ├── ingestion/              # Document ingestion
│   ├── orchestration/          # Processing orchestration
│   ├── rag/                    # Chunking, embeddings, retrieval, generation
│   ├── repositories/           # Data access components
│   ├── schemas/                # Data schemas
│   ├── services/               # Backend services
│   ├── storage/                # Local generated index
│   ├── build_index.py          # Build document index
│   ├── main.py                 # FastAPI application
│   └── requirements.txt        # Python dependencies
│
├── frontend/
│   ├── public/
│   └── src/
│       ├── components/         # Shared UI components
│       ├── data/               # Frontend catalogue data
│       ├── pages/              # Home, Explorer, Insights, Assistant, etc.
│       ├── App.jsx             # Application navigation
│       └── index.css           # Global styling
│
├── Database/                   # Database-related files
├── tests/                      # Backend tests
├── pytest.ini
└── README.md
```

## 📡 NASA Data Sources

The project is designed around NASA scientific research and supporting documentation.

| Source | Purpose |
|---|---|
| [NASA Physical Sciences Informatics (PSI)](https://psi.nasa.gov/physci/repo/) | Physical-science investigation records and research datasets. |
| [NASA Technical Reports Server (NTRS)](https://ntrs.nasa.gov/) | Scientific reports and publications. |
| [NASA Science Data Resources](https://science.nasa.gov/learn/entry-points-to-nasa-data/) | Additional NASA scientific data resources. |

Relevant research programs represented in the current catalogue include **ACME, SAFFIRE, FLEX, BASS, CFI**, and other combustion-related collections.

## 📊 Scientific Data Integrity

Scientific accuracy is central to FLAME AI.

Our principles include:

- Preserve original NASA files and source references.
- Retain original measurement values and units.
- Track transformations during data processing.
- Distinguish missing values from measured zero values.
- Avoid comparing measurements with incompatible units or experimental conditions.
- Clearly identify AI-generated interpretations.
- Link research answers to supporting sources whenever available.

**Important:** Current catalogue analytics describe investigation metadata. They must not be interpreted as measured flame temperature, pressure, oxygen concentration, or other experimental results unless validated measurement data is available.

FLAME AI is a research exploration prototype, not a certified spacecraft fire-risk assessment tool.

## ⚙️ Getting Started

### Prerequisites

- Git
- Node.js and npm
- Python 3.11 recommended for the current development environment
- Ollama, if running the local RAG generation and embedding pipeline

### 1. Clone the repository

```powershell
git clone https://github.com/22312235/flame-ai.git
cd flame-ai
```

### 2. Start the frontend

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

Open the Vite URL printed in the terminal, normally:

```text
http://localhost:5173
```

On Windows PowerShell, use `npm.cmd` if the execution policy blocks `npm.ps1`.

### 3. Set up the AI backend

Open a second terminal at the repository root:

```powershell
cd AI
python -m venv .venv
```

Install dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

If using the local Ollama models, make sure Ollama is installed and running:

```powershell
ollama pull qwen3.5:4b
ollama pull nomic-embed-text
```

Start the API:

```powershell
.\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

The API should be available at:

```text
http://127.0.0.1:8000
```

Interactive API documentation:

```text
http://127.0.0.1:8000/docs
```

### 4. Build the document index

The RAG assistant requires an indexed document store. Place authorized source documents in the location expected by the ingestion workflow, then follow the project's indexing script:

```powershell
.\.venv\Scripts\python.exe build_index.py
```

Check `AI/build_index.py` and the ingestion modules for the current input-document configuration before building the index.

The generated vector store is local application data and should not be committed to Git.

## 📡 API Overview

The AI application includes these core endpoints:

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/` | Basic API status. |
| `GET` | `/health` | Reports backend and RAG index availability. |
| `POST` | `/ask` | Retrieves research passages and generates an answer. |

### Example question request

```http
POST /ask
Content-Type: application/json
```

```json
{
  "question": "Under what conditions were spherical gas-fueled cool diffusion flames observed?"
}
```

The response includes the submitted question, generated answer, and retrieved source information such as document name and page number.

Catalogue, filtering, and analysis API modules are present in the repository and are being integrated and tested by the backend team. Refer to the live API documentation at `/docs` for the routes currently registered by the running application.

## 👥 Meet the Team

Built with curiosity, collaboration, and a passion for space technology.

| Team member | Main contribution |
|---|---|
| **Hana Shaimi** | Frontend development, dashboard, user experience |
| **Majdoline Elbennadi** | Backend and API development |
| **Abdallah Aboudrari** | AI assistant and RAG development |
| **Adam Elboudali Zahid** | Data analysis and research data |

Responsibilities may overlap as features are integrated and tested.

## 🛣️ Development Roadmap

- [x] React application and navigation.
- [x] Investigation catalogue interface.
- [x] Catalogue metadata visualizations.
- [x] Initial FastAPI RAG endpoint.
- [x] Local embedding and generation workflow.
- [x] Initial catalogue API modules added to the repository.
- [ ] Complete catalogue and analysis API integration.
- [ ] Connect frontend pages to live backend endpoints.
- [ ] Expand validated structured experimental datasets.
- [ ] Add measurement-based scientific visualizations where source data supports them.
- [ ] Improve automated tests and end-to-end validation.
- [ ] Deploy a stable demonstration environment.

## 🌠 Our Mission

We believe that making scientific knowledge more accessible can help accelerate research and support safer human exploration of space.

**FLAME AI — Bringing clarity to combustion research, one investigation at a time.**

---

<p align="center">
  <strong>🔥 FLAME AI</strong><br/>
  NASA Space Apps Challenge 2026<br/>
  Challenge 07 — Flame in Freefall
</p>

<p align="center">
  <sub>Built by our team with a passion for AI, science, and space exploration. 🚀</sub>
</p>
