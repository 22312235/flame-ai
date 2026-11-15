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
  <img src="https://img.shields.io/badge/Vite-646CFF?style=flat-square&logo=vite&logoColor=white"/>
  <img src="https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white"/>
  <img src="https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white"/>
  <img src="https://img.shields.io/badge/Ollama-000000?style=flat-square&logo=ollama&logoColor=white"/>
  <img src="https://img.shields.io/badge/Supabase-3ECF8E?style=flat-square&logo=supabase&logoColor=white"/>
</p>

---

## 🌌 Overview

**FLAME AI** is an AI-powered research exploration and analytics platform designed to make microgravity combustion research more accessible, searchable, and understandable.

Developed for **NASA Space Apps Challenge 2026 — Challenge 07: Flame in Freefall**, the project addresses the difficulty of exploring extensive scientific documents and experiment records related to combustion in microgravity environments.

By combining an interactive research dashboard, scientific data exploration, analytics, and Retrieval-Augmented Generation (RAG), FLAME AI helps users:

- Discover relevant combustion investigations.
- Explore NASA research programs and experiment records.
- Analyze available research metadata.
- Compare investigations and their documented characteristics.
- Ask natural-language questions about scientific documents.
- Retrieve evidence and source references.
- Explore documented findings relevant to spacecraft fire safety.

Our mission is to transform complex scientific information into accessible, evidence-based research insights.

## 🚀 The Problem

Combustion behaves differently in microgravity than it does under Earth's gravity.

Understanding these differences is important for spacecraft fire safety and future human space exploration.

NASA has accumulated extensive research on microgravity combustion, including experiment records, technical reports, measurements, and supporting documentation.

However, navigating large collections of heterogeneous scientific information can be challenging.

Researchers need an accessible way to:

- Discover relevant combustion experiments.
- Search through scientific documents.
- Understand experimental objectives and conditions.
- Compare investigations across research programs.
- Identify documented observations and research gaps.
- Retrieve relevant information without manually reading large collections of reports.

## 💡 Our Solution

FLAME AI brings research exploration, metadata analytics, investigation comparison, and AI-assisted scientific document search into one platform.

Instead of manually navigating multiple research documents and datasets, users can explore available investigations through an interactive dashboard and ask the AI assistant questions using natural language.

The platform is designed to connect scientific information with its original sources, making research exploration more efficient and transparent.

## ✨ Core Features

| Feature | Description |
|---|---|
| 🌍 Mission Dashboard | Overview of research investigations, programs, and available data. |
| 🔬 Research Explorer | Search, browse, sort, and filter combustion investigations using available metadata. |
| 📊 Research Analytics | Interactive visualizations of research metadata, including program distribution, investigation years, categories, and data availability. |
| ⚖️ Comparison Lab | Compare selected investigations and their available metadata. |
| 🤖 AI Research Assistant | Ask natural-language questions and retrieve relevant evidence from indexed scientific documents. |
| 🔥 Fire Safety Insights | Explore documented combustion findings and their potential relevance to spacecraft fire safety. |
| 🧪 Data Quality Insights | Understand dataset availability, missing information, and processing limitations. |

### 🔬 Research Explorer

The Research Explorer provides a searchable catalogue of combustion investigations.

Users can:

- Search investigations by title and available information.
- Filter by research program.
- Filter by data availability and investigation type.
- Explore investigation years.
- Sort the available records.
- Select investigations for comparison.
- Open individual investigation details.

### 📊 Research Analytics

The Research Analytics section transforms catalogue metadata into interactive visualizations.

Available analytical views include:

- Research distribution by program.
- Investigation distribution by year.
- Data availability and indexing status.
- Investigation categories and types.
- Program versus investigation-type distribution.

Charts are connected to the research catalogue and can be used to explore or filter records.

**Scientific note:** These visualizations describe the available research catalogue metadata. They must not be interpreted as experimental combustion measurements or physical trends.

### ⚖️ Comparison Lab

The Comparison Lab helps users examine multiple investigations side by side.

The comparison experience is intended to highlight available information such as:

- Research program.
- Investigation year.
- Experiment type.
- Research objectives.
- Available documentation.
- Recorded metadata and source references.

Comparisons involving actual experimental measurements require validated and compatible measurement data.

### 🤖 AI Research Assistant

The AI Research Assistant allows users to ask questions about indexed scientific documents.

Instead of relying only on general model knowledge, the assistant retrieves relevant document passages and uses them to generate evidence-grounded responses.

Its objective is to make technical research easier to understand while maintaining links to supporting documents.

## 🧠 AI-Powered Research: RAG Architecture

FLAME AI uses **Retrieval-Augmented Generation (RAG)** to connect natural-language questions with relevant scientific documents.

### How it works

```text
        NASA Scientific Documents
                   |
                   v
             PDF Extraction
                   |
                   v
              Text Chunking
                   |
                   v
             Text Embeddings
                   |
                   v
             Vector Storage
                   |
                   v
              User Question
                   |
                   v
              Semantic Search
                   |
                   v
          Relevant Research Evidence
                   |
                   v
             Local Language Model
                   |
                   v
          Evidence-Based AI Answer
                   |
                   v
          Supporting Source References
```

### RAG Components

| Component | Technology | Purpose |
|---|---|---|
| Document extraction | Python | Extract text from scientific PDF documents. |
| Text chunking | Python | Divide documents into smaller searchable sections. |
| Embeddings | `nomic-embed-text` | Convert text into numerical vector representations. |
| Vector storage | JSON-based vector store | Store document chunks and their embeddings. |
| Retrieval | Semantic similarity search | Find relevant document passages. |
| Language model | `qwen3.5:4b` through Ollama | Generate natural-language responses using retrieved context. |
| API | FastAPI | Expose the research assistant to the frontend. |

The assistant is designed to distinguish between:

1. Findings explicitly documented in original research.
2. Conclusions reported by scientific authors.
3. AI-generated interpretations based on retrieved evidence.

When the indexed evidence is insufficient, the system should communicate that limitation rather than inventing an answer.

## 🏗️ System Architecture

FLAME AI consists of a React frontend and a Python-based AI backend.

```text
                  NASA RESEARCH SOURCES
                           |
              +------------+------------+
              |                         |
          NASA PSI                  NASA NTRS
              |                         |
              +------------+------------+
                           |
                           v
                  RESEARCH DOCUMENTS
                           |
                           v
                  PYTHON DATA PROCESSING
                           |
             +-------------+-------------+
             |                           |
       Research Catalogue           PDF Ingestion
             |                           |
             |                      Text Chunking
             |                           |
             |                      Embeddings
             |                           |
             |                      Vector Store
             |                           |
             |                      RAG Retrieval
             |                           |
             |                     Local LLM
             |                           |
             +-------------+-------------+
                           |
                       FASTAPI
                           |
                           v
                    REACT FRONTEND
                           |
          +----------------+----------------+
          |                |                |
       Dashboard        Explorer        AI Assistant
          |                |                |
       Analytics       Comparison      Source Evidence
          |                |                |
          +----------------+----------------+
                           |
                       FLAME AI
```

## 🛠️ Technology Stack

### Frontend

- **React.js** — Component-based user interface.
- **Vite** — Frontend development and build tooling.
- **JavaScript / JSX** — Frontend application logic.
- **CSS** — Custom styling and responsive layouts.
- **Lucide React** — Interface icons.

### Backend and API

- **Python** — Core backend and AI processing language.
- **FastAPI** — REST API development.
- **Pydantic** — Data validation and API schemas.

### Artificial Intelligence

- **Ollama** — Local model execution.
- **Qwen 3.5 4B** — Local language model for AI-generated responses.
- **nomic-embed-text** — Text embedding model.
- **Retrieval-Augmented Generation (RAG)** — Evidence-grounded question answering.
- **Semantic Similarity Search** — Retrieval of relevant research passages.
- **JSON Vector Store** — Current local storage for indexed document chunks and embeddings.

### Data and Research Processing

- **Python** — Document processing and data analysis.
- **Pandas** — Data manipulation and analysis where applicable.
- **PostgreSQL / Supabase** — Database and backend services where configured and integrated.

> The technology list reflects the current project implementation and intended integrations. Components that are still being integrated should not be considered fully operational.

## 📂 Repository Structure

The project is organized into two main application directories:

```text
flame-ai/
│
├── AI/
│   ├── api/
│   ├── analysis/
│   ├── catalog/
│   ├── ingestion/
│   ├── orchestration/
│   ├── rag/
│   ├── repositories/
│   ├── schemas/
│   ├── services/
│   ├── storage/
│   │
│   ├── main.py
│   ├── build_index.py
│   └── requirements.txt
│
├── frontend/
│   ├── public/
│   │
│   └── src/
│       ├── components/
│       ├── data/
│       ├── pages/
│       ├── App.jsx
│       └── index.css
│
├── .gitignore
└── README.md
```

**Note:** This is a high-level representation of the current project organization. Additional files and modules may exist within the directories.

## 📡 NASA Data Sources

FLAME AI is designed around NASA scientific research and supporting documentation.

| Source | Purpose |
|---|---|
| [NASA Physical Sciences Informatics (PSI)](https://psi.nasa.gov/physci/repo/) | Research records and datasets related to physical sciences investigations. |
| [NASA Technical Reports Server (NTRS)](https://ntrs.nasa.gov/) | Scientific reports, technical publications, and supporting research. |
| [NASA Science Data Resources](https://science.nasa.gov/learn/entry-points-to-nasa-data/) | Additional entry points to NASA scientific datasets. |

Relevant combustion research programs represented in the catalogue include:

- ACME
- SAFFIRE
- FLEX
- BASS
- CFI
- Smoke & Aerosols
- SPICE
- SLICE
- Other combustion investigations

The availability and completeness of information depend on the source records and documents included in the project.

## 📊 Scientific Data Integrity

Scientific accuracy is central to FLAME AI.

Our data-handling principles include:

- Preserve original NASA documents and source references.
- Retain original measurement values and units when available.
- Distinguish missing values from measured zero values.
- Avoid comparisons between incompatible experimental conditions.
- Clearly identify metadata-based analysis.
- Distinguish documented scientific findings from AI-generated interpretations.
- Link AI responses to supporting sources whenever available.
- Avoid presenting unsupported conclusions as established scientific facts.

**Important:** Catalogue metadata is not a substitute for validated experimental measurements. Temperature, pressure, oxygen concentration, flame dimensions, and other physical measurements should only be visualized when the corresponding validated data are available.

## ⚙️ Getting Started

### Prerequisites

- Python 3.10 or newer.
- Node.js and npm.
- Git.
- Ollama.
- Sufficient system resources to run the selected local AI models.

### 1. Clone the Repository

```powershell
git clone https://github.com/22312235/flame-ai.git
cd flame-ai
```

### 2. Frontend Setup

Open a terminal in the project directory:

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

The frontend will normally be available at:

```text
http://localhost:5173
```

### 3. AI Backend Setup

Open another terminal in the project root:

```powershell
cd AI
python -m venv .venv
```

On Windows, install dependencies using the virtual environment's Python executable:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 4. Install the Local AI Models

Make sure Ollama is installed and running.

Pull the language model:

```powershell
ollama pull qwen3.5:4b
```

Pull the embedding model:

```powershell
ollama pull nomic-embed-text
```

### 5. Build the Research Index

From the `AI` directory:

```powershell
.\.venv\Scripts\python.exe build_index.py
```

This process prepares the document index used by the RAG pipeline.

The required source documents and their paths must be configured according to the ingestion setup.

### 6. Start the FastAPI Backend

From the `AI` directory:

```powershell
.\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

The backend will normally be available at:

```text
http://127.0.0.1:8000
```

API documentation:

```text
http://127.0.0.1:8000/docs
```

### 7. Check Backend Health

Open:

```text
http://127.0.0.1:8000/health
```

The health endpoint reports the backend status and document index information.

### Current AI Assistant Endpoint

**POST** `/ask`

Example request:

```json
{
  "question": "What are the main findings documented in the combustion investigation?"
}
```

The endpoint returns an AI-generated answer and available source references, including document information and page details where provided.

> Additional catalogue and analytics API modules may be present in the repository. Their live availability should be checked through the FastAPI documentation at `/docs`.

## 🗺️ Development Roadmap

| Area | Development Status |
|---|---|
| React dashboard and navigation | Implemented |
| Research catalogue and filtering | Implemented |
| Research metadata analytics | Implemented / In development |
| Investigation comparison interface | In development |
| AI research assistant interface | Implemented |
| FastAPI AI endpoint | Implemented |
| Local embedding and language models | Integrated |
| Initial NASA document indexing | Implemented |
| Catalogue API integration | In progress |
| Validated structured experimental datasets | Pending |
| Measurement-based scientific visualizations | Pending validated data |
| Expanded testing and deployment | Planned |

The roadmap reflects the development stage of the project and will evolve as additional modules are completed and validated.

## 👥 Meet the Team

Built with curiosity, collaboration, and a passion for space technology.

### 👩‍💻 Hana Shaimi — UI/UX Designer & Frontend Developer

- Designed and developed the FLAME AI frontend using React and Vite.
- Improved the platform's layout, styling, reusable components, and overall user experience.
- Contributed to refining the AI assistant's retrieval and response behavior.

### ⚙️ Majdoline Elbennadi — Backend & API Developer

- Contributed to backend architecture and API development.
- Worked on server-side application logic and data handling.
- Contributed to connecting backend services with the frontend.

### 🤖 Abdallah Aboudrari — AI Assistant Engineer

- Contributed to the AI research assistant.
- Worked on Retrieval-Augmented Generation (RAG) and AI integration.
- Contributed to document retrieval and embedding workflows.

### 📊 Adam Elboudali Zahid — Data Analyst

- Contributed to NASA research data exploration.
- Worked on data preparation, cleaning, and analysis.
- Contributed to organizing scientific information for the platform.

## 🌠 Our Mission

We believe that making scientific knowledge more accessible can help accelerate research and support safer human exploration of space.

By connecting NASA's microgravity combustion research with AI-assisted discovery and interactive analytics, FLAME AI aims to make scientific exploration more intuitive, transparent, and useful.

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
