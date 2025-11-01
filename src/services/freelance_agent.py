import logging
from typing import List, Dict, Any, Optional
from uuid import uuid4
from datetime import datetime
import json

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
from src.services.ai import AIService
from src.schemas.job import JobSearchQuery

logger = logging.getLogger(__name__)


class FreelanceAgent:
    """AI Agent for tracking freelance jobs and trends using A2A protocol"""

    def __init__(self, scraper: JobScraper):
        self.scraper = scraper
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
                user_text = part.text.strip().lower()
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
            logger.error(f"Error processing message: {e}")
            return self._create_error_result(context_id, task_id, str(e), messages)

    async def _handle_intent(
        self, user_text: str, context_id: str
    ) -> tuple[str, List[Artifact], str]:
        """Parse user intent and execute appropriate action"""

        if any(word in user_text for word in ["trending", "popular", "top"]) and any(
            word in user_text for word in ["skill", "technology", "tech"]
        ):
            return await self._get_trending_skills()

        elif any(word in user_text for word in ["trending", "popular", "top"]) and any(
            word in user_text for word in ["role", "position", "job"]
        ):
            return await self._get_trending_roles()

        elif any(
            word in user_text for word in ["search", "find", "show", "list"]
        ) and any(word in user_text for word in ["job", "position", "opening"]):
            return await self._search_jobs(user_text)

        elif any(
            word in user_text for word in ["stats", "statistics", "overview", "summary"]
        ):
            return await self._get_statistics()

        elif any(word in user_text for word in ["analyze", "analysis", "insight"]):
            return await self._run_analysis()

        elif any(
            word in user_text for word in ["scrape", "fetch", "update", "refresh"]
        ):
            return await self._scrape_jobs()

        elif any(word in user_text for word in ["latest", "recent"]) and any(
            word in user_text for word in ["analysis", "trend", "report"]
        ):
            return await self._get_latest_analysis()

        elif "compare" in user_text or "vs" in user_text or "versus" in user_text:
            return await self._compare_skills(user_text)

        elif any(word in user_text for word in ["learn", "learning", "study", "path"]):
            return await self._get_learning_path(user_text)

        elif any(
            word in user_text
            for word in ["what", "how", "why", "when", "should", "can", "?"]
        ):
            return await self._answer_question(user_text, context_id)

        else:
            return self._get_help()

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

            response = f"**Found {len(jobs)} Recent Jobs**\n\n"
            for i, job in enumerate(jobs[:10], 1):
                skills = ", ".join(job.tags[:5]) if job.tags else "N/A"
                response += f"{i}. **{job.position}** at {job.company}\n"
                response += f"   Location: {job.location}\n"
                response += f"   Skills: {skills}\n"
                response += f"   Posted: {job.date_posted.strftime('%Y-%m-%d')}\n\n"

            jobs_data = [
                {
                    "id": job.id,
                    "position": job.position,
                    "company": job.company,
                    "location": job.location,
                    "tags": job.tags,
                    "url": job.url,
                    "date_posted": job.date_posted.isoformat(),
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
        """Run trend analysis with AI insights"""
        result = await self.analyzer.run_full_analysis()

        response = "**Trend Analysis Completed with AI Insights**\n\n"
        response += f"✅ Analyzed {result['total_jobs_analyzed']} jobs\n"
        response += f"📈 Found {result['trending_skills_count']} trending skills\n"
        response += f"💼 Found {result['trending_roles_count']} trending roles\n\n"

        if result.get("ai_insights"):
            response += "**🤖 AI Insights:**\n\n"
            response += result["ai_insights"]

        artifact = Artifact(
            name="analysis_result", parts=[MessagePart(kind="data", data=result)]
        )

        return response, [artifact], "completed"

    async def _scrape_jobs(self) -> tuple[str, List[Artifact], str]:
        """Scrape new jobs"""
        result = await self.scraper.scrape_and_store()

        response = "**Job Scraping Completed**\n\n"
        response += f"✅ Fetched {result['total_fetched']} jobs\n"
        response += f"➕ Added {result['jobs_added']} new jobs\n"
        response += f"🏷️ Tracked {result['skills_added']} skills\n"

        artifact = Artifact(
            name="scrape_result", parts=[MessagePart(kind="data", data=result)]
        )

        return response, [artifact], "completed"

    async def _get_latest_analysis(self) -> tuple[str, List[Artifact], str]:
        """Get latest trend analysis with AI insights"""
        with get_db_context() as db:
            analysis = TrendRepository.get_latest_analysis(db)

            if not analysis:
                return (
                    "No analysis available yet. Run 'analyze trends' first.",
                    [],
                    "completed",
                )

            response = "**Latest Trend Analysis**\n\n"
            response += (
                f"📅 Date: {analysis.analysis_date.strftime('%Y-%m-%d %H:%M')}\n"
            )
            response += f"📊 Jobs Analyzed: {analysis.total_jobs_analyzed}\n"
            response += f"🔧 Unique Skills: {analysis.unique_skills_found}\n"

            if analysis.trending_skills:
                top_3 = analysis.trending_skills[:3]
                response += "\n**Top 3 Trending Skills:**\n"
                for skill in top_3:
                    response += (
                        f"• {skill['skill_name']}: {skill['growth_percentage']}\n"
                    )

            if analysis.ai_insights:
                response += f"\n**🤖 AI Insights:**\n\n{analysis.ai_insights}"

            artifact = Artifact(
                name="latest_analysis",
                parts=[
                    MessagePart(
                        kind="data",
                        data={
                            "analysis_date": analysis.analysis_date.isoformat(),
                            "trending_skills": analysis.trending_skills,
                            "trending_roles": analysis.trending_roles,
                            "skill_clusters": analysis.skill_clusters,
                            "ai_insights": analysis.ai_insights,
                        },
                    )
                ],
            )

            return response, [artifact], "completed"

    def _get_help(self) -> tuple[str, List[Artifact], str]:
        """Get help message"""
        response = """**Freelance Trends Agent - Available Commands**

I can help you track and analyze freelance job trends! Here's what I can do:

📊 **Statistics**
• "show statistics" - Get overall job statistics
• "show stats" - Same as above

🔥 **Trends**
• "show trending skills" - See top trending technologies
• "show trending roles" - See most popular job positions
• "latest analysis" - Get the most recent trend analysis

🔍 **Search**
• "search jobs" - Find recent job postings
• "find jobs" - Same as above

🤖 **AI-Powered Features**
• "compare Python vs JavaScript" - Compare two skills
• "learn React" - Get a learning path for a skill
• Ask any question about the job market

⚙️ **Actions**
• "scrape jobs" - Fetch latest jobs
• "analyze trends" - Run comprehensive AI-powered trend analysis

Just ask me naturally and I'll help you discover what's hot in the freelance market!
"""

        artifact = Artifact(
            name="help", parts=[MessagePart(kind="text", text=response)]
        )

        return response, [artifact], "completed"

    async def _compare_skills(self, user_text: str) -> tuple[str, List[Artifact], str]:
        """Compare two skills using AI"""
        words = (
            user_text.lower()
            .replace("compare", "")
            .replace("vs", " ")
            .replace("versus", " ")
            .split()
        )
        potential_skills = [
            w.strip()
            for w in words
            if len(w) > 2 and w not in ["and", "the", "or", "with"]
        ]

        if len(potential_skills) < 2:
            return (
                "Please specify two skills to compare (e.g., 'compare Python vs JavaScript')",
                [],
                "completed",
            )

        skill1, skill2 = potential_skills[0], potential_skills[1]

        with get_db_context() as db:
            all_skills = SkillRepository.get_all_skills(db)
            skill1_data = next(
                (s for s in all_skills if skill1.lower() in s.name.lower()), None
            )
            skill2_data = next(
                (s for s in all_skills if skill2.lower() in s.name.lower()), None
            )

            market_data = {
                "skill1_mentions": skill1_data.total_mentions if skill1_data else 0,
                "skill2_mentions": skill2_data.total_mentions if skill2_data else 0,
                "skill1_growth": "N/A",
                "skill2_growth": "N/A",
            }

        comparison = await self.ai_service.compare_skills(skill1, skill2, market_data)

        response = f"**Comparing {skill1.title()} vs {skill2.title()}**\n\n{comparison}"

        artifact = Artifact(
            name="skill_comparison", parts=[MessagePart(kind="text", text=comparison)]
        )

        return response, [artifact], "completed"

    async def _get_learning_path(
        self, user_text: str
    ) -> tuple[str, List[Artifact], str]:
        """Generate learning path for a skill"""
        words = (
            user_text.lower()
            .replace("learn", "")
            .replace("learning", "")
            .replace("path", "")
            .split()
        )
        target_skill = " ".join(w for w in words if len(w) > 2)[:50]

        if not target_skill:
            return (
                "Please specify a skill you want to learn (e.g., 'learn React')",
                [],
                "completed",
            )

        current_skills = []

        learning_path = await self.ai_service.generate_skill_learning_path(
            target_skill=target_skill, current_skills=current_skills
        )

        response = f"**Learning Path for {target_skill.title()}**\n\n{learning_path}"

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
                "additional_context": "Data from API, updated every 30 minutes",
            }

        answer = await self.ai_service.answer_question(user_text, context_data)

        response = f"**Answer:**\n\n{answer}"

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
