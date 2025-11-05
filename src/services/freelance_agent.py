import logging
from typing import List, Dict, Any, Optional
from uuid import uuid4

from src.models.a2a import (
    A2AMessage,
    TaskResult,
    TaskStatus,
    Artifact,
    MessagePart,
    MessageConfiguration,
)
from src.db.session import get_db_context
from src.db.repository import JobRepository, SkillRepository, TrendRepository
from src.services.trend_analyzer import TrendAnalyzer
from src.services.job_scraper import JobScraper
from src.services.rss_scraper import RSSFeedScraper
from src.services.ai import AIService
from src.schemas.job import JobSearchQuery

logger = logging.getLogger(__name__)


class FreelanceAgent:
    """AI Agent for tracking freelance jobs and trends using A2A protocol"""

    def __init__(self, scraper: JobScraper, rss_scraper: RSSFeedScraper):
        self.scraper = scraper
        self.rss_scraper = rss_scraper
        self.analyzer = TrendAnalyzer()
        self.ai_service = AIService()
        self.conversations = {}

    async def process_messages(
        self,
        messages: List[A2AMessage],
        context_id: Optional[str] = None,
        task_id: Optional[str] = None,
        config: Optional[MessageConfiguration] = None,
    ) -> TaskResult:
        """Process incoming A2A messages and generate response"""

        context_id = context_id or str(uuid4())
        task_id = task_id or str(uuid4())

        user_message = messages[-1] if messages else None
        if not user_message:
            return self._create_error_result(
                context_id, task_id, "No message provided", messages
            )

        user_text = ""
        for part in user_message.parts:
            if part.kind == "text":
                user_text = part.text.strip()
                break

        try:
            response_text, artifacts, state = await self._handle_intent(
                user_text, context_id
            )

            response_message = A2AMessage(
                role="agent",
                parts=[MessagePart(kind="text", text=response_text)],
                taskId=task_id,
            )

            history = messages + [response_message]

            return TaskResult(
                id=task_id,
                contextId=context_id,
                status=TaskStatus(state=state, message=response_message),
                artifacts=artifacts,
                history=history,
            )

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            return self._create_error_result(context_id, task_id, str(e), messages)

    async def _handle_intent(
        self, user_text: str, context_id: str
    ) -> tuple[str, List[Artifact], str]:
        """Parse user intent and execute appropriate action."""

        intent_data = await self.ai_service.classify_intent(user_text)
        intent = intent_data.get("intent")
        entities = intent_data.get("entities", {})

        logger.info(f"Intent: {intent}, Entities: {entities}")

        handlers = {
            "get_trending_skills": self._get_trending_skills,
            "get_trending_roles": self._get_trending_roles,
            "search_jobs": lambda: self._search_jobs(
                entities.get("job_query", user_text)
            ),
            "get_statistics": self._get_statistics,
            "run_analysis": self._run_analysis,
            "scrape_jobs": self._scrape_jobs,
            "get_latest_analysis": self._get_latest_analysis,
            "compare_skills": lambda: (
                self._compare_skills(entities.get("skill1"), entities.get("skill2"))
                if entities.get("skill1") and entities.get("skill2")
                else self._invalid_compare()
            ),
            "get_learning_path": lambda: self._get_learning_path(
                entities.get("target_skill", user_text)
            ),
            "get_help": self._get_help,
            "answer_question": lambda: self._answer_question(user_text, context_id),
        }

        handler = handlers.get(
            intent, lambda: self._answer_question(user_text, context_id)
        )
        return await handler()

    def _invalid_compare(self) -> tuple[str, List[Artifact], str]:
        """Handle invalid skill comparison"""
        return (
            "Please specify two skills to compare. Example: 'compare Python vs JavaScript'",
            [],
            "completed",
        )

    async def _get_trending_skills(self) -> tuple[str, List[Artifact], str]:
        """Get trending skills"""
        with get_db_context() as db:
            analyzer = TrendAnalyzer(window_days=30)
            trending_skills = analyzer.analyze_skill_trends(db)

            if not trending_skills:
                return (
                    "No trending skills data available yet. Try running an analysis first.",
                    [],
                    "completed",
                )

            response = "**Top Trending Skills (Last 30 Days)**\n\n"
            response += "Based on remote job listings:\n\n"
            for i, skill in enumerate(trending_skills[:10], 1):
                response += f"{i}. **{skill.skill_name.title()}**: {skill.current_mentions} mentions ({skill.growth_percentage})\n"

            skills_data = [skill.model_dump() for skill in trending_skills]
            artifact = Artifact(
                name="trending_skills",
                parts=[MessagePart(kind="data", data={"skills": skills_data})],
            )

            return response, [artifact], "completed"

    async def _get_trending_roles(self) -> tuple[str, List[Artifact], str]:
        """Get trending job roles"""
        with get_db_context() as db:
            analyzer = TrendAnalyzer(window_days=30)
            trending_roles = analyzer.analyze_role_trends(db)

            if not trending_roles:
                return "No trending roles data available yet.", [], "completed"

            response = "**Top Trending Job Roles (Last 30 Days)**\n\n"
            for i, role in enumerate(trending_roles[:10], 1):
                skills_str = (
                    ", ".join(role.top_skills[:3]) if role.top_skills else "N/A"
                )
                response += f"{i}. **{role.role_name}**: {role.job_count} jobs\n"
                response += f"   Top Skills: {skills_str}\n\n"

            roles_data = [role.model_dump() for role in trending_roles]
            artifact = Artifact(
                name="trending_roles",
                parts=[MessagePart(kind="data", data={"roles": roles_data})],
            )

            return response, [artifact], "completed"

    async def _search_jobs(self, query_text: str) -> tuple[str, List[Artifact], str]:
        """Search for jobs"""
        with get_db_context() as db:
            search_query = JobSearchQuery(limit=20)
            jobs = JobRepository.search_jobs(db, search_query)

            if not jobs:
                return "No jobs found matching your criteria.", [], "completed"

            response = f"**Found {len(jobs)} Recent Remote Jobs**\n\n"
            for i, job in enumerate(jobs[:10], 1):
                skills = ", ".join(job.tags[:5]) if job.tags else "N/A"
                response += f"{i}. **{job.position}** at {job.company}\n"
                response += f"   Skills: {skills}\n"
                if job.url:
                    response += f"   Apply: {job.url}\n"
                response += "\n"

            jobs_data = [
                {
                    "id": job.id,
                    "position": job.position,
                    "company": job.company,
                    "tags": job.tags,
                    "url": job.url,
                }
                for job in jobs
            ]

            artifact = Artifact(
                name="job_search_results",
                parts=[MessagePart(kind="data", data={"jobs": jobs_data})],
            )

            return response, [artifact], "completed"

    async def _get_statistics(self) -> tuple[str, List[Artifact], str]:
        """Get overall statistics"""
        with get_db_context() as db:
            total_jobs = JobRepository.get_total_jobs(db)
            jobs_24h = JobRepository.get_jobs_count_by_period(db, hours=24)
            jobs_7d = JobRepository.get_jobs_count_by_period(db, hours=24 * 7)

            top_skills = SkillRepository.get_top_skills(db, limit=5)
            skill_names = [skill.name for skill in top_skills]

            response = "**Freelance Jobs Statistics**\n\n"
            response += f"📊 **Total Jobs Tracked**: {total_jobs}\n"
            response += f"📅 **Last 24 Hours**: {jobs_24h} jobs\n"
            response += f"📅 **Last 7 Days**: {jobs_7d} jobs\n"
            response += f"🔥 **Top Skills**: {', '.join(skill_names)}\n"

            stats_data = {
                "total_jobs": total_jobs,
                "jobs_24h": jobs_24h,
                "jobs_7d": jobs_7d,
                "top_skills": skill_names,
            }

            artifact = Artifact(
                name="statistics", parts=[MessagePart(kind="data", data=stats_data)]
            )

            return response, [artifact], "completed"

    async def _run_analysis(self) -> tuple[str, List[Artifact], str]:
        """Run trend analysis"""
        result = await self.analyzer.run_full_analysis()

        response = "**Trend Analysis Completed**\n\n"
        response += f"✅ Analyzed {result['total_jobs_analyzed']} jobs\n"
        response += f"📈 Found {result['trending_skills_count']} trending skills\n"
        response += f"💼 Found {result['trending_roles_count']} trending roles\n"

        artifact = Artifact(
            name="analysis_result", parts=[MessagePart(kind="data", data=result)]
        )

        return response, [artifact], "completed"

    async def _scrape_jobs(self) -> tuple[str, List[Artifact], str]:
        """Scrape new jobs"""
        result = await self.rss_scraper.scrape_and_store()

        response = "**RSS Scraping Completed**\n\n"
        response += f"✅ **Fetched**: {result['total_fetched']} jobs\n"
        response += f"➕ **New**: {result['jobs_added']}\n"

        artifact = Artifact(
            name="scrape_result", parts=[MessagePart(kind="data", data=result)]
        )

        return response, [artifact], "completed"

    async def _scrape_jobs(self) -> tuple[str, List[Artifact], str]:
        """Scrape new jobs from RSS feeds"""
        result = await self.rss_scraper.scrape_and_store()

        response = "**RSS Feed Scraping Completed**\n\n"
        response += f"📡 **Feeds Processed**: {result['feeds_processed']}\n"
        response += f"✅ **Fetched**: {result['total_fetched']} jobs\n"
        response += f"➕ **New Jobs**: {result['jobs_added']}\n"
        response += f"🔄 **Updated Jobs**: {result.get('jobs_updated', 0)}\n"
        response += f"🏷️ **Skills Tracked**: {result['skills_added']}\n\n"
        response += (
            "Sources: Full-Stack, Frontend, Programming, Design, DevOps categories"
        )

        artifact = Artifact(
            name="scrape_result", parts=[MessagePart(kind="data", data=result)]
        )

        return response, [artifact], "completed"

    async def _get_latest_analysis(self) -> tuple[str, List[Artifact], str]:
        """Get latest analysis"""
        with get_db_context() as db:
            analysis = TrendRepository.get_latest_analysis(db)

            if not analysis:
                return (
                    "No analysis available yet. Run 'analyze trends' first.",
                    [],
                    "completed",
                )

            response = "**Latest Trend Analysis**\n\n"
            response += f"📊 Jobs Analyzed: {analysis.total_jobs_analyzed}\n"

            artifact = Artifact(
                name="latest_analysis",
                parts=[
                    MessagePart(
                        kind="data",
                        data={
                            "analysis_date": analysis.analysis_date.isoformat(),
                            "trending_skills": analysis.trending_skills,
                        },
                    )
                ],
            )

            return response, [artifact], "completed"

    def _get_help(self) -> tuple[str, List[Artifact], str]:
        """Get help message"""
        response = """**Freelance Trends Agent**

Ask me anything about the remote job market! Examples:

📊 "show statistics" or "how many jobs?"
🔥 "trending skills" or "popular technologies"
💼 "trending roles" or "popular jobs"
🔍 "search React jobs" or "find Python positions"
📚 "learn backend development" or "learning path for React"
⚖️ "compare Python vs JavaScript"
🤖 Ask questions like "what skills should I learn?"

Just ask naturally!"""

        artifact = Artifact(
            name="help", parts=[MessagePart(kind="text", text=response)]
        )

        return response, [artifact], "completed"

    async def _compare_skills(
        self, skill1: Optional[str], skill2: Optional[str]
    ) -> tuple[str, List[Artifact], str]:
        """Compare two skills"""

        if not skill1 or not skill2:
            return (
                "Please specify two skills to compare. Example: 'compare Python vs JavaScript'",
                [],
                "completed",
            )

        logger.info(f"Comparing {skill1} vs {skill2}")

        with get_db_context() as db:
            all_skills = SkillRepository.get_all_skills(db)
            skill1_data = next(
                (
                    s
                    for s in all_skills
                    if skill1.lower() in s.name.lower()
                    or s.name.lower() in skill1.lower()
                ),
                None,
            )
            skill2_data = next(
                (
                    s
                    for s in all_skills
                    if skill2.lower() in s.name.lower()
                    or s.name.lower() in skill2.lower()
                ),
                None,
            )

            market_data = {
                "skill1_mentions": skill1_data.total_mentions if skill1_data else 0,
                "skill2_mentions": skill2_data.total_mentions if skill2_data else 0,
            }

        comparison = await self.ai_service.compare_skills(skill1, skill2, market_data)

        response = f"**Comparing {skill1.title()} vs {skill2.title()}**\n\n{comparison}"

        artifact = Artifact(
            name="skill_comparison", parts=[MessagePart(kind="text", text=comparison)]
        )

        return response, [artifact], "completed"

    async def _get_learning_path(
        self, target_skill: str
    ) -> tuple[str, List[Artifact], str]:
        """Generate learning path for a skill"""

        skill = target_skill.strip()
        if not skill or len(skill) < 2:
            return (
                "Please specify a skill you want to learn. Example: 'learn React' or 'create learning path for Python'",
                [],
                "completed",
            )

        logger.info(f"Generating learning path for: '{skill}'")

        with get_db_context() as db:
            top_skills = [
                s.name.lower() for s in SkillRepository.get_top_skills(db, limit=30)
            ]
            is_trending = any(
                skill.lower() in ts or ts in skill.lower() for ts in top_skills
            )

        learning_path = await self.ai_service.generate_skill_learning_path(skill)

        market_note = ""
        if is_trending:
            market_note = f"\n\n**📈 Market Insight:** {skill.title()} is currently trending in remote job listings!\n"

        response = (
            f"**Learning Path for {skill.title()}**{market_note}\n{learning_path}"
        )

        artifact = Artifact(
            name="learning_path", parts=[MessagePart(kind="text", text=learning_path)]
        )

        return response, [artifact], "completed"

    async def _answer_question(
        self, user_text: str, context_id: str
    ) -> tuple[str, List[Artifact], str]:
        """Answer user question using AI"""

        with get_db_context() as db:
            total_jobs = JobRepository.get_total_jobs(db)
            recent_jobs = JobRepository.get_jobs_count_by_period(db, hours=24 * 7)
            top_skills = [
                skill.name for skill in SkillRepository.get_top_skills(db, limit=5)
            ]

            from sqlalchemy import func
            from src.models.job import Job

            total_companies = db.query(func.count(func.distinct(Job.company))).scalar()

            context_data = {
                "total_jobs": total_jobs,
                "recent_jobs": recent_jobs,
                "top_skills": top_skills,
                "total_companies": total_companies,
                "data_sources": "We Work Remotely RSS feeds (Full-Stack, Frontend, Programming, Design, DevOps)",
            }

        answer = await self.ai_service.answer_question(user_text, context_data)

        response = f"{answer}"

        artifact = Artifact(
            name="ai_answer", parts=[MessagePart(kind="text", text=answer)]
        )

        return response, [artifact], "completed"

    def _create_error_result(
        self, context_id: str, task_id: str, error_msg: str, history: List[A2AMessage]
    ) -> TaskResult:
        """Create error result"""
        error_message = A2AMessage(
            role="agent",
            parts=[MessagePart(kind="text", text=f"Error: {error_msg}")],
            taskId=task_id,
        )

        return TaskResult(
            id=task_id,
            contextId=context_id,
            status=TaskStatus(state="failed", message=error_message),
            artifacts=[],
            history=history + [error_message],
        )
