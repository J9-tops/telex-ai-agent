# Freelance Trends Agent 🚀

An AI agent that tracks the latest freelancing jobs from RemoteOK and identifies emerging trends in skills, roles, and technologies using the A2A (Agent-to-Agent) protocol.

## Features ✨

- **Automated Job Scraping**: Continuously fetches jobs from RemoteOK API
- **Trend Analysis**: Identifies trending skills, technologies, and job roles
- **A2A Protocol Support**: Full JSON-RPC 2.0 A2A protocol implementation
- **REST API**: Traditional REST endpoints for job search and statistics
- **Skill Clustering**: Discovers skills that often appear together
- **Growth Metrics**: Tracks skill and role popularity over time
- **Natural Language Interface**: Chat with the agent to get insights

## Architecture 🏗️

```
src/
├── db/                    # Database layer
│   ├── session.py         # SQLAlchemy session management
│   └── repository.py      # Data access repositories
├── models/                # Data models
│   ├── job.py            # SQLAlchemy models
│   └── a2a.py            # A2A protocol models
├── routers/               # API endpoints
│   ├── jobs.py           # Job-related endpoints
│   ├── trends.py         # Trend analysis endpoints
│   └── admin.py          # Admin operations
├── schemas/               # Pydantic schemas
│   └── job.py            # Request/response schemas
├── services/              # Business logic
│   ├── job_scraper.py    # RemoteOK API integration
│   ├── trend_analyzer.py # Trend analysis engine
│   └── freelance_agent.py # A2A agent implementation
├── tests/                 # Test suite
└── main.py               # FastAPI application
```

## Installation 📦

### Prerequisites

- Python 3.13+
- PostgreSQL (or SQLite for development)
- Redis (optional, for caching)

### Setup

1. **Clone the repository**
```bash
git clone <your-repo-url>
cd freelance-trends-agent
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -e .
```

4. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. **Initialize database**
```bash
python -c "from src.db.session import init_db; init_db()"
```

## Usage 🚀

### Start the Server

```bash
python src/main.py
```

The server will start on `http://localhost:5001`

### A2A Protocol Usage

Send A2A requests to `/a2a/freelance`:

```bash
curl -X POST http://localhost:5001/a2a/freelance \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "req-001",
    "method": "message/send",
    "params": {
      "message": {
        "kind": "message",
        "role": "user",
        "parts": [
          {
            "kind": "text",
            "text": "show trending skills"
          }
        ],
        "messageId": "msg-001"
      }
    }
  }'
```

### Available Commands

**Statistics**
- "show statistics" - Get overall job statistics
- "show stats"

**Trends**
- "show trending skills" - See top trending technologies
- "show trending roles" - See most popular job positions
- "latest analysis" - Get most recent trend analysis

**Search**
- "search jobs" - Find recent job postings
- "find jobs"

**Actions**
- "scrape jobs" - Fetch latest jobs from RemoteOK
- "analyze trends" - Run comprehensive trend analysis

### REST API Endpoints

**Jobs**
- `GET /api/jobs/` - List jobs with filters
- `GET /api/jobs/{job_id}` - Get specific job
- `GET /api/jobs/recent/list` - Get recent jobs
- `GET /api/jobs/stats/overview` - Get statistics

**Trends**
- `GET /api/trends/latest` - Get latest analysis
- `GET /api/trends/skills/trending` - Get trending skills
- `GET /api/trends/roles/trending` - Get trending roles
- `GET /api/trends/clusters` - Get skill clusters
- `POST /api/trends/analyze` - Trigger new analysis

**Admin**
- `POST /api/admin/scrape` - Manually trigger scraping
- `GET /api/admin/status` - Get system status

**Documentation**
- Visit `http://localhost:5001/docs` for interactive API documentation

## Configuration ⚙️

Key environment variables:

```bash
# Server
PORT=5001
HOST=0.0.0.0

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/freelance_trends

# Job Scraping
JOB_FETCH_INTERVAL_MINUTES=30
REMOTEOK_API_URL=https://remoteok.com/api

# Trend Analysis
TREND_ANALYSIS_WINDOW_DAYS=30
MIN_JOB_MENTIONS_FOR_TREND=5
```

## Development 🛠️

### Run Tests

```bash
pytest src/tests/ -v
```

### Code Formatting

```bash
black src/
ruff check src/
```

### Database Migrations

```bash
alembic revision --autogenerate -m "Description"
alembic upgrade head
```

## Background Jobs 📅

The agent automatically:
1. **Scrapes jobs** every 30 minutes (configurable)
2. **Tracks skills** from job postings
3. **Builds trend history** over time

## Data Sources 📊

- **RemoteOK API**: `https://remoteok.com/api`
- Real-time remote job postings
- Skills/tags extraction
- Company and location data

## A2A Protocol 🤖

This agent implements the A2A (Agent-to-Agent) protocol for standardized AI agent communication:

- **JSON-RPC 2.0** based
- **Message/Send** method for single interactions
- **Execute** method for multi-turn conversations
- **Task management** with status tracking
- **Artifact support** for structured data

## Example Responses

**Trending Skills Response:**
```json
{
  "jsonrpc": "2.0",
  "id": "req-001",
  "result": {
    "id": "task-123",
    "contextId": "ctx-456",
    "status": {
      "state": "completed",
      "message": {
        "role": "agent",
        "parts": [{
          "kind": "text",
          "text": "**Top Trending Skills (Last 30 Days)**\n\n1. **Python**: 450 mentions (+25.5%)\n2. **React**: 380 mentions (+18.2%)..."
        }]
      }
    },
    "artifacts": [{
      "name": "trending_skills",
      "parts": [{
        "kind": "data",
        "data": {
          "skills": [...]
        }
      }]
    }],
    "kind": "task"
  }
}
```

## Roadmap 🗺️

- [ ] AI-powered job recommendations
- [ ] Email alerts for trending skills
- [ ] Multi-platform job source integration
- [ ] Salary trend analysis
- [ ] Geographic trend analysis
- [ ] Skill learning path suggestions

## Contributing 🤝

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Submit a pull request

## License 📄

MIT License - see LICENSE file for details

## Support 💬

For issues and questions:
- GitHub Issues: <your-repo-url>/issues
- Documentation: See `/docs` endpoint

---

Built with ❤️ using FastAPI, SQLAlchemy, and the A2A Protocol