from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import os
import logging
import asyncio
import httpx
import json

from src.models.a2a import JSONRPCRequest, JSONRPCResponse, A2AMessage, MessagePart
from src.services.freelance_agent import FreelanceAgent
from src.services.job_scraper import JobScraper, run_scheduled_scraping
from src.services.rss_scraper import RSSFeedScraper, run_scheduled_rss_scraping
from src.db.session import init_db, get_db
from src.routers import job, trends, admin, ai
from sqlalchemy.orm import Session

load_dotenv()


logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

freelance_agent = None
scraper_task = None
rss_scraper_task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown"""
    global freelance_agent, scraper_task, rss_scraper_task

    logger.info("Starting Freelance Trends Agent...")

    init_db()
    logger.info("Database initialized")

    rss_scraper = RSSFeedScraper(rate_limit=int(os.getenv("RATE_LIMIT", 1440)))

    scraper = JobScraper(
        api_url=os.getenv("API_URL"), rate_limit=int(os.getenv("RATE_LIMIT", 1400))
    )

    freelance_agent = FreelanceAgent(scraper=scraper, rss_scraper=rss_scraper)
    logger.info("Freelance agent initialized")

    logger.info("Performing initial job scrape...")
    try:
        initial_result = await rss_scraper.scrape_and_store()
        logger.info(f"Initial job scrape completed: {initial_result}")
    except Exception as e:
        logger.error(f"Initial job scrape failed: {e}")

    if os.getenv("API_URL"):
        logger.info("Performing initial API scrape...")
        try:
            initial_api_result = await scraper.scrape_and_store()
            logger.info(f"Initial API scrape completed: {initial_api_result}")
        except Exception as e:
            logger.error(f"Initial API scrape failed: {e}")

    rss_scrape_interval = int(os.getenv("RSS_SCRAPE_INTERVAL_MINUTES", 1440))
    rss_scraper_task = asyncio.create_task(
        run_scheduled_rss_scraping(
            rss_scraper, interval_minutes=rss_scrape_interval, skip_first=True
        )
    )
    logger.info(
        f"RSS background scraping started (interval: {rss_scrape_interval} minutes)"
    )

    if os.getenv("API_URL"):
        scrape_interval = int(os.getenv("JOB_FETCH_INTERVAL_MINUTES", 1440))
        scraper_task = asyncio.create_task(
            run_scheduled_scraping(scraper, interval_minutes=scrape_interval)
        )
        logger.info(
            f"API background scraping started (interval: {scrape_interval} minutes)"
        )

    yield

    if rss_scraper_task:
        rss_scraper_task.cancel()
        try:
            await rss_scraper_task
        except asyncio.CancelledError:
            pass

    if scraper_task:
        scraper_task.cancel()
        try:
            await scraper_task
        except asyncio.CancelledError:
            pass

    logger.info("Freelance Trends Agent shut down")


app = FastAPI(
    title="Freelance Trends Agent",
    description="AI agent tracking freelancing jobs and identifying emerging trends with A2A protocol support",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(job.router)
app.include_router(trends.router)
app.include_router(admin.router)
app.include_router(ai.router)


def normalize_to_text(obj):
    """Convert all data parts to well-formatted markdown text."""

    def format_data_as_markdown(data, level=0):
        """Recursively format dicts/lists into clean markdown."""

        if isinstance(data, dict):
            lines = []

            if "skills" in data and isinstance(data["skills"], list):
                return format_skills_list(data["skills"])
            elif "roles" in data and isinstance(data["roles"], list):
                return format_roles_list(data["roles"])
            elif "jobs" in data and isinstance(data["jobs"], list):
                return format_jobs_list(data["jobs"])

            for key, value in data.items():
                formatted_key = key.replace("_", " ").title()

                if isinstance(value, dict):
                    lines.append(f"\n**{formatted_key}:**\n")
                    lines.append(format_data_as_markdown(value, level + 1))
                elif isinstance(value, list):
                    lines.append(f"\n**{formatted_key}:**")
                    lines.append(format_data_as_markdown(value, level + 1))
                else:
                    lines.append(f"**{formatted_key}:** {value}")

            return "\n".join(lines)

        elif isinstance(data, list):
            if not data:
                return "_No items_"

            lines = []
            if data and isinstance(data[0], dict):
                for i, item in enumerate(data, 1):
                    lines.append(f"\n{i}. {format_dict_item(item)}")
            else:
                for item in data:
                    lines.append(f"- {item}")

            return "\n".join(lines)

        else:
            return str(data)

    def format_skills_list(skills):
        """Format trending skills list beautifully."""
        if not skills:
            return "_No skills data available_"

        lines = ["## 📊 Trending Skills\n"]

        for i, skill in enumerate(skills[:15], 1):
            name = skill.get("skill_name", "Unknown").title()
            current = skill.get("current_mentions", 0)
            growth = skill.get("growth_percentage", "N/A")

            if "+" in str(growth):
                emoji = "🔥"
            elif "-" in str(growth):
                emoji = "📉"
            else:
                emoji = "📊"

            lines.append(f"{i}. {emoji} **{name}**")
            lines.append(f"   - Mentions: {current}")
            lines.append(f"   - Growth: {growth}\n")

        return "\n".join(lines)

    def format_roles_list(roles):
        """Format trending roles list beautifully."""
        if not roles:
            return "_No roles data available_"

        lines = ["## 💼 Trending Job Roles\n"]

        for i, role in enumerate(roles[:15], 1):
            name = role.get("role_name", "Unknown")
            count = role.get("job_count", 0)
            skills = role.get("top_skills", [])

            lines.append(f"{i}. **{name}**")
            lines.append(f"   - Open Positions: {count}")
            if skills:
                skills_str = ", ".join(skills[:5])
                lines.append(f"   - Key Skills: {skills_str}\n")
            else:
                lines.append("")

        return "\n".join(lines)

    def format_jobs_list(jobs):
        """Format job listings beautifully."""
        if not jobs:
            return "_No jobs found_"

        lines = [f"## 🔍 Found {len(jobs)} Jobs\n"]

        for i, job in enumerate(jobs[:20], 1):
            position = job.get("position", "Unknown Position")
            company = job.get("company", "Unknown Company")
            tags = job.get("tags", [])
            url = job.get("url", "")

            lines.append(f"### {i}. {position}")
            lines.append(f"**Company:** {company}")

            if tags:
                skills_str = ", ".join(tags[:6])
                lines.append(f"**Skills:** {skills_str}")

            if url:
                lines.append(f"**[Apply Here]({url})**")

            lines.append("")

        return "\n".join(lines)

    def format_dict_item(item):
        """Format a single dict item inline."""
        if "skill_name" in item:
            return f"**{item['skill_name'].title()}** - {item.get('current_mentions', 0)} mentions"
        elif "role_name" in item:
            return f"**{item['role_name']}** - {item.get('job_count', 0)} jobs"
        elif "position" in item:
            company = item.get("company", "Unknown")
            return f"**{item['position']}** at {company}"
        else:

            key_val_pairs = [f"{k}: {v}" for k, v in item.items() if v]
            return ", ".join(key_val_pairs[:3])

    if hasattr(obj, "status") and hasattr(obj.status, "message"):
        parts = getattr(obj.status.message, "parts", [])
        for part in parts:
            if part.kind == "data" and part.data:
                part.kind = "text"
                part.text = format_data_as_markdown(part.data)
                part.data = None

    if hasattr(obj, "artifacts"):
        for artifact in getattr(obj, "artifacts", []):
            for part in artifact.parts:
                if part.kind == "data" and part.data:
                    part.kind = "text"
                    part.text = format_data_as_markdown(part.data)
                    part.data = None

    return obj


@app.post("/a2a/freelance")
async def a2a_endpoint(request: Request):
    """Main A2A endpoint for freelance trends agent"""
    try:
        body = await request.json()
        logger.info(
            f"Received A2A request: method={body.get('method')}, id={body.get('id')}"
        )

        if body.get("jsonrpc") != "2.0" or "id" not in body:
            return JSONResponse(
                status_code=400,
                content={
                    "jsonrpc": "2.0",
                    "id": body.get("id"),
                    "error": {
                        "code": -32600,
                        "message": "Invalid Request: jsonrpc must be '2.0' and id is required",
                    },
                },
            )

        rpc_request = JSONRPCRequest(**body)

        messages = []
        context_id = None
        task_id = None
        config = None
        push_notification_config = None

        if rpc_request.method == "message/send":
            msg = rpc_request.params.message
            user_text = ""

            for part in msg.parts:
                if part.kind == "text" and part.text:
                    user_text = part.text
                    break
                elif part.kind == "data" and part.data:
                    if isinstance(part.data, dict):
                        user_text = part.data.get("text", "")
                    elif isinstance(part.data, list):
                        for item in part.data:
                            if isinstance(item, dict) and item.get("kind") == "text":
                                user_text = item.get("text", "")
                                break
                    if user_text:
                        break

            messages = [
                A2AMessage(
                    kind=msg.kind,
                    role=msg.role,
                    parts=[MessagePart(kind="text", text=user_text)],
                    messageId=msg.messageId,
                )
            ]
            config = rpc_request.params.configuration
            if (
                config
                and isinstance(config, dict)
                and "pushNotificationConfig" in config
            ):
                push_notification_config = config["pushNotificationConfig"]
                logger.info(f"Push notification config: {push_notification_config}")
            logger.info(f"Processing message/send: {user_text}")

        elif rpc_request.method == "execute":
            messages = rpc_request.params.messages or []
            context_id = rpc_request.params.contextId
            task_id = rpc_request.params.taskId
            logger.info(
                f"Processing execute: {len(messages)} messages, contextId={context_id}"
            )

        is_blocking = True
        if isinstance(config, dict):
            is_blocking = config.get("blocking", True)

        logger.info(f"Request blocking mode: {is_blocking}")

        if not is_blocking and push_notification_config:

            logger.info("Non-blocking request - processing in background")

            asyncio.create_task(
                process_and_notify(
                    messages=messages,
                    context_id=context_id,
                    task_id=task_id,
                    config=config,
                    push_config=push_notification_config,
                    request_id=rpc_request.id,
                )
            )

            return {
                "jsonrpc": "2.0",
                "id": rpc_request.id,
                "result": {
                    "status": "processing",
                    "message": "Request accepted and processing in background",
                },
            }
        else:
            logger.info("Blocking request - processing synchronously")
            result = await freelance_agent.process_messages(
                messages=messages, context_id=context_id, task_id=task_id, config=config
            )

            result = normalize_to_text(result)

            if messages and messages[0].messageId:
                incoming_message_id = messages[0].messageId
                if hasattr(result, "id"):
                    result.id = incoming_message_id
                if hasattr(result, "status") and hasattr(result.status, "message"):
                    result.status.message.messageId = incoming_message_id

                logger.info(f"Agent processing completed: state={result.status.state}")

                response = JSONRPCResponse(id=rpc_request.id, result=result)
                return response.model_dump()

    except Exception as e:
        logger.error(f"Error in A2A endpoint: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "jsonrpc": "2.0",
                "id": body.get("id") if "body" in locals() else None,
                "error": {
                    "code": -32603,
                    "message": "Internal error",
                    "data": {"details": str(e)},
                },
            },
        )


async def process_and_notify(
    messages, context_id, task_id, config, push_config, request_id
):
    """Process request in background and send push notification"""
    try:
        logger.info(f"[BACKGROUND] Starting processing for request {request_id}")

        NOTIFICATION_URL = os.getenv("NOTIFICATION_URL")

        result = await freelance_agent.process_messages(
            messages=messages, context_id=context_id, task_id=task_id, config=config
        )

        logger.info(f"[BACKGROUND] Processing completed: state={result.status.state}")

        notification_url = NOTIFICATION_URL
        notification_token = None

        if isinstance(push_config, dict):
            notification_url = push_config.get("url") or NOTIFICATION_URL
            notification_token = push_config.get("token")
            logger.debug(f"[DEBUG] push_config value: {push_config}")
            logger.debug(f"[DEBUG] notification_url: {notification_url}")

        if not notification_url:
            logger.warning(
                f"[BACKGROUND] No notification URL provided in config: {push_config}"
            )
            return

        if not notification_url or not str(notification_url).startswith(
            ("http://", "https://")
        ):
            logger.error(
                f"[BACKGROUND] Invalid or missing notification URL: {notification_url}"
            )
            return

        if notification_url:
            logger.info(
                f"[BACKGROUND] Sending push notification to: {notification_url}"
            )

            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {
                    "Content-Type": "application/json",
                }

                if notification_token:
                    headers["Authorization"] = f"Bearer {notification_token}"

                response_data = JSONRPCResponse(
                    id=request_id, result=result
                ).model_dump()

                response = await client.post(
                    notification_url, json=response_data, headers=headers
                )

                logger.info(
                    f"[BACKGROUND] Push notification sent: {response.status_code}"
                )
        else:
            logger.warning(f"[BACKGROUND] No notification URL provided")

    except Exception as e:
        logger.error(f"[BACKGROUND] Error processing and notifying: {e}", exc_info=True)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    from src.db.repository import JobRepository
    from src.db.session import get_db_context

    try:
        with get_db_context() as db:
            total_jobs = JobRepository.get_total_jobs(db)
            jobs_24h = JobRepository.get_jobs_count_by_period(db, hours=24)
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        total_jobs = -1
        jobs_24h = -1

    return {
        "status": "healthy",
        "agent": "freelance-trends",
        "version": "1.0.0",
        "database": {
            "connected": total_jobs >= 0,
            "total_jobs": total_jobs,
            "jobs_last_24h": jobs_24h,
        },
        "scrapers": {
            "rss_enabled": True,
            "api_enabled": bool(os.getenv("API_URL")),
        },
    }


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "Freelance Trends Agent",
        "version": "1.0.0",
        "description": "AI agent tracking freelancing jobs from multiple sources",
        "endpoints": {"a2a": "/a2a/freelance", "health": "/health", "docs": "/docs"},
        "capabilities": [
            "Track latest remote jobs ",
            "Analyze trending skills and technologies",
            "Identify popular job roles",
            "Provide job search and statistics",
            "A2A protocol support for AI agents",
        ],
    }
