# Anvil: Self-Healing DevSecOps Multi-Agent Platform

Anvil is a production-grade autonomous CI/CD recovery platform. When a deployment or build fails (e.g., due to a dependency mismatch, broken CI configuration, or runtime import failure), Anvil dynamically spawns an intelligent swarm of AI agents to investigate, formulate a repair plan, validate the fix in a persistent shadow environment, and automatically promote the verified fix via Pull Request.

## 🚀 Features

- **Autonomous Repair Pipeline**: Full lifecycle recovery from webhook trigger to verified PR.
- **Multi-Agent Swarm**: 
  - **Orchestrator**: Central state machine managing the hierarchical execution tree.
  - **Coordinator**: Findings aggregator and repair strategist.
  - **Memory Agent**: Hybrid `pgvector` + Neo4j long-term memory for fix reuse.
  - **Specialized Workers**: Log Analysis, Dependency Inspection, Web Research, and Repair Agents.
- **Shadow Environment Validation**: Isolated Docker sandboxes for iterative build/test verification.
- **Real-Time Observability**: Next.js dashboard featuring live logs and ReactFlow agent graphs.
- **Distributed Coordination**: Go-based WebSocket hub and Python agent swarm synchronized via Redis.

## 🛠 Tech Stack

- **Backend**: Go 1.22+ (Services, Webhooks, WebSocket Hub, pgx/v5)
- **Agent Runtime**: Python 3.10+ (FastAPI, asyncio, Dynamic Module Spawning)
- **Frontend**: React (Vite, @tanstack/react-router), ReactFlow, Tailwind CSS
- **Infrastructure**: PostgreSQL 16 (pgvector), Neo4j 5 (APOC), Redis 7
- **AI Models**: Gemini 1.5 Pro (Investigation), GPT-4o (Repair), OpenAI Embeddings

## 📋 Prerequisites

- **Docker Desktop** (running)
- **Go 1.22+**
- **Python 3.10+**
- **Node.js 18+**
- **OpenAI API Key** (for embeddings and repair)
- **Gemini API Key** (for analysis)
- **GitHub PAT** (with repo scopes)

## 🏗 Setup & Startup

### 1. Environment Configuration

1. Create a root `.env` file (see `.env.example`):
   ```bash
   cp .env.example .env
   # Fill in your OPENAI_API_KEY, GEMINI_API_KEY, and GITHUB_TOKEN
   ```
2. The Go backend and Python agents will automatically read their respective configurations.

### 2. Launch Infrastructure

```bash
# Terminal 1
docker compose up -d
# Wait ~30s for health checks to pass
```

### 3. Start Backend Services

```bash
# Terminal 2 - Go Backend
cd backend
go run main.go

# Terminal 3 - Python Agent Runtime
cd agents
# Activate your virtual environment
pip install -r requirements.txt
python main.py
```

### 4. Start Frontend

```bash
# Terminal 4
cd frontend
npm install
npm run dev
```

### 5. Setup Webhook Tunnel (Local Only)

```bash
# Terminal 5
ngrok http 8080
```

## 🏁 Initializing for Demo

Run these once after the infrastructure is up:

1. **Seed Memory**: Prime the AI with known incidents to demonstrate instant reuse.
   ```bash
   python scripts/seed_memory.py
   ```

2. **Register Webhook**: Connect your target GitHub repository.
   ```bash
   python scripts/register_webhook.py \
     --token YOUR_PAT \
     --repo owner/repo \
     --url https://YOUR_NGROK_URL/webhook/github
   ```

3. **Verify Health**:
   ```bash
   bash scripts/verify.sh
   ```

## 🧪 Triggering the Demo

There are two ways to trigger the self-healing loop:

### Method 1: Local Mock Trigger (Recommended for UI Testing)
You can artificially simulate a failed pipeline run without needing ngrok or a real GitHub repository. This will push a mock event directly into the Orchestrator queue, allowing you to watch the agent swarm and ReactFlow graph in real-time.
```bash
python scripts/trigger_repair.py "owner/repo"
```

### Method 2: Real GitHub Webhook
If you've set up the webhook via ngrok, push a deterministic failure to your repository to initiate the real end-to-end flow:
```bash
python scripts/create_test_repo_commit.py --token YOUR_PAT --repo owner/repo
```

### 📺 Watch it Live
Once triggered, watch the **Anvil Dashboard** at `http://localhost:3000`. You will see:
- A dynamic **ReactFlow Graph** mapping out the hierarchy of spawned agents (e.g., Orchestrator -> Log Analyzer & Dependency Inspector) connected via glowing, animated flow lines.
- **Live Logs** streaming the thoughts, decisions, and actions of the Python Agent Swarm in real-time.
- Automatic updates as the swarm investigates the log, queries memory, creates a shadow environment, iterates on the fix, and opens a Pull Request.

---
*Anvil is built for the DevSecOps of the future — where pipelines don't just fail; they heal.*
