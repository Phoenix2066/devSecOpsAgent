#!/bin/bash
# scripts/verify.sh
# Run this before the demo to verify all systems are go.
# Usage: bash scripts/verify.sh

set -e
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

pass() { echo -e "${GREEN}✓ $1${NC}"; }
fail() { echo -e "${RED}✗ $1${NC}"; exit 1; }

echo "=== DevSecOps Platform Pre-Demo Verification ==="

# 1. Docker services
docker ps | grep devsecops-postgres  && pass "PostgreSQL running" || fail "PostgreSQL not running"
docker ps | grep devsecops-neo4j     && pass "Neo4j running"     || fail "Neo4j not running"
docker ps | grep devsecops-redis     && pass "Redis running"     || fail "Redis not running"

# 2. Go backend
curl -sf http://localhost:8080/health | grep "ok" \
  && pass "Go backend healthy" || fail "Go backend not responding"

# 3. Python agents
curl -sf http://localhost:8001/health | grep "ok" \
  && pass "Python agents healthy" || fail "Python agents not responding"

# 4. PostgreSQL schema
docker exec devsecops-postgres psql -U devsecops -d devsecops \
  -c "SELECT COUNT(*) FROM incidents;" \
  && pass "PostgreSQL schema ready" || fail "PostgreSQL schema not initialized"

# 5. pgvector extension
docker exec devsecops-postgres psql -U devsecops -d devsecops \
  -c "SELECT extname FROM pg_extension WHERE extname='vector';" | grep "vector" \
  && pass "pgvector extension active" || fail "pgvector not installed"

# 6. Memory pre-seeded
docker exec devsecops-postgres psql -U devsecops -d devsecops \
  -c "SELECT COUNT(*) FROM incidents;" | grep -E "[1-9][0-9]*" \
  && pass "Memory pre-seeded" || fail "Memory empty — run scripts/seed_memory.py"

# 7. Redis connectivity
# Default to localhost if REDIS_URL not set
URL=${REDIS_URL:-"redis://localhost:6379"}
redis-cli -u "$URL" ping | grep "PONG" \
  && pass "Redis responding" || fail "Redis not responding"

# 8. Neo4j connectivity
curl -sf http://localhost:7474 \
  && pass "Neo4j browser accessible" || fail "Neo4j not accessible"

# 9. Frontend
# Frontend usually runs on 3000 for Next.js, but check 5173 if using Vite as in some files
curl -sf http://localhost:3000 \
  && pass "Frontend running" || fail "Frontend not running — run: cd frontend && npm run dev"

# 10. ngrok (if using for webhook)
curl -sf http://localhost:4040/api/tunnels | grep "public_url" \
  && pass "ngrok tunnel active" || fail "ngrok not running — start ngrok before demo"

echo ""
echo "=== All systems go. Ready for demo. ==="
echo ""
echo "Demo trigger command:"
echo "  python scripts/create_test_repo_commit.py --token YOUR_PAT --repo owner/repo"
