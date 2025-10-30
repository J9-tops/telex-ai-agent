# Quick Start Guide 🚀

Get your Freelance Trends Agent up and running in 5 minutes!

## Option 1: Local Development (SQLite)

### 1. Setup

```bash
# Create project structure
mkdir freelance-trends-agent
cd freelance-trends-agent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -e .
```

### 2. Configure Environment

Create `.env` file:

```bash
PORT=5001
HOST=0.0.0.0
DATABASE_URL=sqlite:///./freelance_trends.db
REDIS_URL=redis://localhost:6379/0
REMOTEOK_API_URL=https://remoteok.com/api
JOB_FETCH_INTERVAL_MINUTES=30
LOG_LEVEL=INFO
```

### 3. Initialize Database

```bash
python -c "from src.db.session import init_db; init_db()"
```

### 4. Run the Server

```bash
python src/main.py
```

Visit: `http://localhost:5001/docs` for API documentation

### 5. Test the A2A Endpoint

```bash
curl -X POST http://localhost:5001/a2a/freelance \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "1",
    "method": "message/send",
    "params": {
      "message": {
        "kind": "message",
        "role": "user",
        "parts": [{"kind": "text", "text": "help"}],
        "messageId": "msg-1"
      }
    }
  }'
```

## Option 2: Docker Compose (Recommended for Production)

### 1. Setup

```bash
# Clone or create project
cd freelance-trends-agent

# Copy environment file
cp .env.example .env
# Edit .env as needed
```

### 2. Start Services

```bash
docker-compose up -d
```

This starts:
- FastAPI application (port 5001)
- PostgreSQL database (port 5432)
- Redis cache (port 6379)

### 3. Initialize Database

```bash
docker-compose exec app python -c "from src.db.session import init_db; init_db()"
```

### 4. View Logs

```bash
docker-compose logs -f app
```

### 5. Stop Services

```bash
docker-compose down
```

## First Steps After Setup

### 1. Scrape Initial Jobs

```bash
curl -X POST http://localhost:5001/api/admin/scrape
```

Wait a few seconds for jobs to be fetched.

### 2. Check Statistics

```bash
curl http://localhost:5001/api/jobs/stats/overview
```

### 3. Run Trend Analysis

```bash
curl -X POST http://localhost:5001/api/trends/analyze?window_days=30
```

### 4. Get Trending Skills

```bash
curl http://localhost:5001/api/trends/skills/trending
```

### 5. Chat with the Agent (A2A)

```bash
curl -X POST http://localhost:5001/a2a/freelance \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "2",
    "method": "message/send",
    "params": {
      "message": {
        "kind": "message",
        "role": "user",
        "parts": [{"kind": "text", "text": "show trending skills"}],
        "messageId": "msg-2"
      }
    }
  }'
```

## Common Commands

### Manual Job Scraping
```bash
curl -X POST http://localhost:5001/api/admin/scrape
```

### Get Recent Jobs
```bash
curl "http://localhost:5001/api/jobs/recent/list?days=7&limit=20"
```

### Search Jobs by Company
```bash
curl "http://localhost:5001/api/jobs/?company=google&limit=10"
```

### Get Trending Roles
```bash
curl http://localhost:5001/api/trends/roles/trending
```

### Get Skill Clusters
```bash
curl http://localhost:5001/api/trends/clusters
```

## Testing the A2A Protocol

### Example 1: Get Help
```bash
curl -X POST http://localhost:5001/a2a/freelance \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "help-1",
    "method": "message/send",
    "params": {
      "message": {
        "kind": "message",
        "role": "user",
        "parts": [{"kind": "text", "text": "help"}],
        "messageId": "msg-help-1"
      }
    }
  }'
```

### Example 2: Get Statistics
```bash
curl -X POST http://localhost:5001/a2a/freelance \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "stats-1",
    "method": "message/send",
    "params": {
      "message": {
        "kind": "message",
        "role": "user",
        "parts": [{"kind": "text", "text": "show stats"}],
        "messageId": "msg-stats-1"
      }
    }
  }'
```

### Example 3: Multi-turn Conversation
```bash
# First message
curl -X POST http://localhost:5001/a2a/freelance \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "conv-1",
    "method": "execute",
    "params": {
      "contextId": "conversation-123",
      "taskId": "task-1",
      "messages": [
        {
          "kind": "message",
          "role": "user",
          "parts": [{"kind": "text", "text": "what are the trending skills?"}],
          "messageId": "msg-1"
        }
      ]
    }
  }'

# Follow-up message
curl -X POST http://localhost:5001/a2a/freelance \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "conv-2",
    "method": "execute",
    "params": {
      "contextId": "conversation-123",
      "taskId": "task-2",
      "messages": [
        {
          "kind": "message",
          "role": "user",
          "parts": [{"kind": "text", "text": "what are the trending skills?"}],
          "messageId": "msg-1"
        },
        {
          "kind": "message",
          "role": "agent",
          "parts": [{"kind": "text", "text": "Here are the trending skills..."}],
          "messageId": "msg-2"
        },
        {
          "kind": "message",
          "role": "user",
          "parts": [{"kind": "text", "text": "now show me trending roles"}],
          "messageId": "msg-3"
        }
      ]
    }
  }'
```

## Troubleshooting

### Database Connection Issues
```bash
# Check if database exists
python -c "from src.db.session import engine; print(engine.url)"

# Recreate database
python -c "from src.db.session import init_db; init_db()"
```

### No Jobs Found
```bash
# Manually trigger scraping
curl -X POST http://localhost:5001/api/admin/scrape

# Check system status
curl http://localhost:5001/api/admin/status
```

### Import Errors
```bash
# Reinstall dependencies
pip install -e . --force-reinstall
```

### Port Already in Use
```bash
# Change port in .env
PORT=5002

# Or kill process using port
lsof -ti:5001 | xargs kill -9  # macOS/Linux
```

## Next Steps

1. **Customize Scraping**: Adjust `JOB_FETCH_INTERVAL_MINUTES` in `.env`
2. **Add More Sources**: Extend `JobScraper` to fetch from other APIs
3. **Enhance AI**: Integrate LLM for better insights (configure `AI_PROVIDER`)
4. **Setup Monitoring**: Add logging and monitoring tools
5. **Deploy**: Deploy to cloud (AWS, GCP, Heroku, etc.)

## API Documentation

Visit `http://localhost:5001/docs` for complete interactive API documentation powered by Swagger UI.

## Support

- Check logs: `docker-compose logs -f` (Docker) or terminal output (local)
- Test health: `curl http://localhost:5001/health`
- System status: `curl http://localhost:5001/api/admin/status`

Happy tracking! 🚀