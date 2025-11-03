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
        """Parse user intent and execute appropriate action using LLM for classification."""

        intent_data = await self.ai_service.classify_intent(user_text)
        intent = intent_data.get("intent")
        entities = intent_data.get("entities", {})

        logger.info(f"Classified intent: {intent}, Entities: {entities}")

        if intent == "get_trending_skills":
            return await self._get_trending_skills()
        elif intent == "get_trending_roles":
            return await self._get_trending_roles()
        elif intent == "search_jobs":
            search_query_text = entities.get("job_query", user_text)
            return await self._search_jobs(search_query_text)
        elif intent == "get_statistics":
            return await self._get_statistics()
        elif intent == "run_analysis":
            return await self._run_analysis()
        elif intent == "scrape_jobs":
            return await self._scrape_jobs()
        elif intent == "get_latest_analysis":
            return await self._get_latest_analysis()
        elif intent == "compare_skills":
            skill1 = entities.get("skill1")
            skill2 = entities.get("skill2")
            if skill1 and skill2:
                return await self._compare_skills(f"compare {skill1} vs {skill2}")
            else:
                return "Please specify two skills to compare.", [], "completed"
        elif intent == "get_learning_path":
            target_skill = entities.get("target_skill")
            if target_skill:
                return await self._get_learning_path(f"learn {target_skill}")
            else:
                return "Please specify a skill to learn.", [], "completed"
        elif intent == "answer_question":
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
            response += "Based on remote job listings from We Work Remotely:\n\n"
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
            response += "From remote job postings across multiple categories:\n\n"
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
            response += "From We Work Remotely RSS Feeds:\n\n"
            for i, job in enumerate(jobs[:10], 1):
                skills = ", ".join(job.tags[:5]) if job.tags else "N/A"
                response += f"{i}. **{job.position}** at {job.company}\n"
                response += f"   Location: {job.location}\n"
                response += f"   Skills: {skills}\n"
                response += f"   Posted: {job.date_posted.strftime('%Y-%m-%d')}\n"
                if job.url:
                    response += f"   Apply: {job.url}\n"
                response += "\n"

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
            response += "Data aggregated from We Work Remotely RSS feeds:\n\n"
            response += f"📊 **Total Jobs Tracked**: {total_jobs}\n"
            response += f"📅 **Last 24 Hours**: {jobs_24h} jobs\n"
            response += f"📅 **Last 7 Days**: {jobs_7d} jobs\n"
            response += f"🔥 **Top Skills**: {', '.join(skill_names)}\n"
            response += f"\n🌍 **All positions are remote-friendly**\n"

            stats_data = {
                "total_jobs": total_jobs,
                "jobs_24h": jobs_24h,
                "jobs_7d": jobs_7d,
                "top_skills": skill_names,
                "data_sources": ["We Work Remotely RSS Feeds"],
            }

            artifact = Artifact(
                name="statistics", parts=[MessagePart(kind="data", data=stats_data)]
            )

            return response, [artifact], "completed"

    async def _run_analysis(self) -> tuple[str, List[Artifact], str]:
        """Run trend analysis with AI insights"""
        result = await self.analyzer.run_full_analysis()

        response = "**Comprehensive Trend Analysis Completed**\n\n"
        response += f"✅ Analyzed {result['total_jobs_analyzed']} remote jobs\n"
        response += f"📈 Found {result['trending_skills_count']} trending skills\n"
        response += f"💼 Found {result['trending_roles_count']} trending roles\n"
        response += f"🌐 Data from We Work Remotely RSS feeds\n\n"

        if result.get("ai_insights"):
            response += "**🤖 AI Insights:**\n\n"
            response += result["ai_insights"]

        artifact = Artifact(
            name="analysis_result", parts=[MessagePart(kind="data", data=result)]
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

I track remote freelance jobs from We Work Remotely across multiple categories!

📊 **Statistics**
• "show statistics" - Overall job market stats
• "show stats" - Same as above

🔥 **Trends**
• "show trending skills" - Top trending technologies
• "show trending roles" - Most popular positions
• "latest analysis" - Most recent trend analysis

🔍 **Search**
• "search jobs" - Find recent job postings
• "find React jobs" - Search for specific technologies

🤖 **AI-Powered Features**
• "compare Python vs JavaScript" - Compare skills
• "learn React" - Get a learning path
• Ask questions about the job market

⚙️ **Actions**
• "scrape jobs" - Fetch latest jobs from RSS feeds
• "analyze trends" - Run AI-powered trend analysis

💡 **Data Sources**
• We Work Remotely RSS Feeds
• Categories: Full-Stack, Frontend, Programming, Design, DevOps

Just ask naturally and I'll help you discover remote job trends!
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
                "additional_context": "Data from We Work Remotely RSS feeds, updated hourly",
                "data_sources": "Full-Stack, Frontend, Programming, Design, DevOps categories",
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
