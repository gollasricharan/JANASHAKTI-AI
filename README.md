
# JANASHAKTI AI
### Multi-Agent AI-Powered Community Grievance Management System

JANASHAKTI AI is an intelligent community grievance management platform designed to help residents report public issues and enable administrators to analyse, monitor, and prioritize complaints using Artificial Intelligence.

The system combines a Multi-Agent Architecture, Large Language Model (LLM), and Retrieval-Augmented Generation (RAG) to support intelligent complaint analysis and decision-making.

## Problem Statement

Community issues such as water shortages, damaged roads, poor waste management, drainage problems, and electricity disruptions are often difficult to organize, monitor, and prioritize.

JANASHAKTI AI aims to provide a centralized platform that analyses public complaints, evaluates their reported impact, and helps administrators identify issues that require attention.

## Key Features

- Resident complaint submission portal
- Separate administrator dashboard
- AI-powered complaint classification
- Complaint urgency and impact assessment
- Evidence assessment using RAG
- AI-generated complaint summaries and recommendations
- Rule-based complaint priority scoring
- Interactive complaint location map
- Complaint status tracking and administrator review
- SQLite-based complaint storage

## AI Architecture

The project uses four main agents coordinated by an Agent Orchestrator:

1. Classification Agent
2. Evidence Agent
3. Impact Agent
4. Priority Assessment Agent

The system integrates Qwen 2.5 (0.5B) through Ollama for natural-language generation.

RAG retrieves relevant information from local reference documents and provides contextual information to the language model.

## Technology Stack

### Programming Language
- Python

### Artificial Intelligence
- Qwen 2.5 (0.5B)
- Ollama
- Sentence Transformers
- all-MiniLM-L6-v2
- Retrieval-Augmented Generation (RAG)
- Multi-Agent Architecture

### Frontend
- Streamlit

### Database
- SQLite

### Data Processing
- Pandas

### Maps and Geolocation
- Folium
- OpenStreetMap
- Geopy
- Nominatim
- Streamlit-Folium

## Project Structure

```text
JANASHAKTI-AI/
│
├── agents/
│   ├── agent_orchestrator.py
│   ├── classification_agent.py
│   ├── evidence_agent.py
│   └── impact_agent.py
│
├── admin_portal/
│   ├── admin_app.py
│   └── admin_dashboard.py
│
├── database/
│   └── connection.py
│
├── pages/
│   ├── 1_Report_an_Issue.py
│   ├── 2_Explore_Issues.py
│   └── 3_AI_Insights.py
│
├── rag/
│   ├── rag_service.py
│   ├── vector_store.py
│   ├── document_loader.py
│   └── answer_generator.py
│
├── services/
│   ├── llm_service.py
│   ├── priority_service.py
│   ├── report_service.py
│   └── map_service.py
│
├── app.py
├── requirements.txt
└── README.md
```

## How It Works

1. Residents submit community complaints.
2. The Classification Agent identifies the complaint category.
3. The Evidence Agent evaluates supporting information from reference documents.
4. The Impact Agent assesses the reported community impact.
5. The priority service calculates the complaint priority.
6. Qwen 2.5 generates summaries and recommendations using available context.
7. Administrators review complaints through a separate dashboard.

## Maps and Location Intelligence

The application uses Folium and OpenStreetMap to display complaint locations.

Geopy and Nominatim are used to convert locality names into geographical coordinates.

## Installation

Clone the repository:

```bash
git clone https://github.com/gollasricharan/JANASHAKTI-AI.git
cd JANASHAKTI-AI
```

Create a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Install and start Ollama separately, and download the Qwen model used by the application.

## Running the Application

Resident Portal:

```bash
streamlit run app.py --server.port 8503
```

Administrator Portal (in another terminal):

```bash
streamlit run admin_portal/admin_app.py --server.port 8504
```

## Important Notes

- The project uses local reference documents for RAG.
- Evidence assessment does not establish whether a real-world complaint is genuine.
- Priority scoring includes rule-based logic.
- Administrator review is required before action is taken.

## Project Objective

To improve community grievance management through AI-powered complaint analysis, impact assessment, prioritization, and administrator decision support.
