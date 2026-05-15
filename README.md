# Anvil: Self-Healing DevSecOps Multi-Agent Platform

Anvil is a prototype platform that demonstrates autonomous CI/CD recovery. When a deployment or build fails (e.g., due to a dependency mismatch, broken CI configuration, or runtime import failure), Anvil dynamically spawns an intelligent swarm of AI agents to investigate, formulate a repair plan, test the fix in a shadow environment, and automatically push a pull request or merge the fix.

## Features

- **Autonomous Repair Pipeline**: Detects failures via GitHub webhooks and auto-resolves issues without human intervention.
- **Multi-Agent Architecture**: 
  - **Orchestrator Agent**: Manages the workflow graph and delegates tasks.
  - **Investigation Agents**: Specialized workers for log analysis, dependency inspection, code analysis, and config analysis.
  - **Coordinator Agent**: Aggregates findings and decides on the most confident repair strategy.
  - **Repair Agents**: Executes file changes (e.g., fixing imports, YAML manifests, Dockerfiles).
  - **Memory Agent**: Leverages `pgvector` and Neo4j to store past incidents and reuse known fixes.
- **Shadow Environment Validation**: Iterative feedback loop that compiles and tests the agents' proposed fixes in isolated Docker containers before promotion.
- **Live Dashboard**: A Next.js frontend featuring ReactFlow to visualize the agent spawn graph and live streaming logs of the repair iterations.

## Tech Stack

- **Backend**: Go (Services, Webhooks, Pipeline State, WebSocket Hub)
- **Agent Runtime**: Python (FastAPI, Langchain/Native LLM integrations)
- **Frontend**: Next.js, ReactFlow, Tailwind CSS, shadcn/ui
- **Infrastructure**: Docker, PostgreSQL (with pgvector), Redis, Neo4j
- **AI Models**: Gemini (Reasoning/Code Analysis), OpenAI (Embeddings/Repair)

## Setup and Quickstart

### Prerequisites

- Docker Desktop
- Go 1.21+
- Python 3.10+
- Node.js / npm

### 1. Environment Configuration

Copy the provided `.env.example` to `.env` in the root, `backend/`, `agents/`, and `frontend/` directories, and fill in your API keys.

*You will need a Supabase project, Gemini/OpenAI API keys, and a GitHub App for full functionality.*

### 2. Start Infrastructure

Start the databases (Postgres, Redis, Neo4j) using Docker Compose:

```bash
docker compose up -d
```

### 3. Start the Go Backend

The Go backend handles webhooks, state management, and WebSocket connections.

```bash
cd backend
go mod tidy
go run .
```

### 4. Start the Python Agent API

The Python runtime executes the multi-agent orchestration.

```bash
cd agents
python -m venv .venv

# On Windows:
.venv\Scripts\activate
# On Mac/Linux:
# source .venv/bin/activate

pip install -r requirements.txt
uvicorn main:app --reload --port 8001
```

### 5. Start the Frontend Dashboard

The frontend visualizes the pipeline recovery in real-time.

```bash
cd frontend
npm install
npm run dev --port 3000
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

## How to Demo

1. **Replicate Workflow**: Log into the dashboard and click the **+ (Plus)** button next to the Explorer sidebar. Add your GitHub repository details, App ID, and Private Key.
2. **Trigger a Failure**: Push a commit to your linked repository with an intentional error (e.g., a dependency conflict in `requirements.txt`).
3. **Watch it Heal**: The webhook will trigger Anvil. In the dashboard, you will see the Orchestrator spawn investigation agents, query memory, execute a fix in the shadow environment, and ultimately open a Pull Request with the working code.

## Project Structure

- `/backend`: Go application managing infrastructure, data, and WebSocket streaming.
- `/agents`: Python FastAPI application housing the BaseAgent abstractions, Orchestrator, Memory, Coordinator, and Dynamic Worker Agents.
- `/frontend`: Next.js React application providing the real-time observability dashboard.
- `docker-compose.yml`: Local database infrastructure setup.

## Note
This is a prototype meant to showcase the "North Star" vision of an LLM-driven, self-healing DevSecOps loop.
