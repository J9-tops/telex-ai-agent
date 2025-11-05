import os
import logging
from typing import List, Dict, Any, Optional
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)


class AIService:
    """Service for AI-powered insights using Google Gemini"""

    def __init__(self):
        api_key = os.getenv("API_KEY")
        if not api_key:
            raise ValueError("API_KEY environment variable is required for Gemini")

        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-2.5-flash"
        logger.info(f"AI Service initialized with model: {self.model}")

    async def generate_trend_insights(
        self,
        trending_skills: List[Dict[str, Any]],
        trending_roles: List[Dict[str, Any]],
        skill_clusters: Dict[str, List[str]],
        total_jobs: int,
    ) -> str:
        """Generate AI insights about job market trends"""

        prompt = self._build_trend_analysis_prompt(
            trending_skills, trending_roles, skill_clusters, total_jobs
        )

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    max_output_tokens=1000,
                    top_p=0.95,
                ),
            )

            insights = response.text
            logger.info("Generated trend insights successfully")
            return insights

        except Exception as e:
            logger.error(f"Error generating insights: {e}")
            return "Unable to generate AI insights at this time."

    async def analyze_job_description(self, job_description: str) -> Dict[str, Any]:
        """Extract key information from job description"""

        prompt = f"""Analyze this job description and extract key information:

Job Description:
{job_description[:1000]}  

Please provide:
1. Required skills (list)
2. Experience level (entry/mid/senior)
3. Key responsibilities (3-5 points)
4. Technology stack
5. Job category (frontend/backend/fullstack/data/devops/etc)

Format your response as JSON."""

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,
                    max_output_tokens=500,
                ),
            )

            import json

            result = response.text
            if "```json" in result:
                result = result.split("```json")[1].split("```")[0].strip()
            elif "```" in result:
                result = result.split("```")[1].split("```")[0].strip()

            return json.loads(result)

        except Exception as e:
            logger.error(f"Error analyzing job description: {e}")
            return {
                "required_skills": [],
                "experience_level": "unknown",
                "key_responsibilities": [],
                "technology_stack": [],
                "job_category": "general",
            }

    async def classify_intent(self, user_query: str) -> Dict[str, Any]:
        """Classify the user's intent and extract relevant entities."""

        prompt = f"""Classify the user's intent from the following query.
    Extract any relevant entities like skill names or job search terms.

    Available intents:
    - get_trending_skills (e.g., "show trending skills", "top tech")
    - get_trending_roles (e.g., "popular job roles", "trending positions")
    - search_jobs (e.g., "find jobs in React", "show Python openings")
    - get_statistics (e.g., "market stats", "overall summary")
    - run_analysis (e.g., "analyze trends", "deep dive into data")
    - scrape_jobs (e.g., "update jobs", "fetch latest listings")
    - get_latest_analysis (e.g., "what's the newest report", "latest insights")
    - compare_skills (e.g., "compare Java vs Go", "Python vs R")
    - get_learning_path (e.g., "how to learn Machine Learning", "study NodeJS")
    - answer_question (for general questions not covered by specific intents)
    - get_help (if the query is unclear or asking for help)

    User Query: f"{user_query}"

    Respond in JSON format with 'intent' and 'entities'.
    Example for "find jobs in React":
    {{"intent": "search_jobs", "entities": {{"job_query": "React"}}}}
    Example for "compare Python vs JavaScript":
    {{"intent": "compare_skills", "entities": {{"skill1": "Python", "skill2": "JavaScript"}}}}
    Example for "what are the top skills?":
    {{"intent": "get_trending_skills", "entities": {{}}}}
    Example for "Tell me about the market":
    {{"intent": "answer_question", "entities": {{}}}}
    """

        try:
            import json

            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=200,
                ),
            )

            result = response.text
            # Ensure proper JSON parsing
            if "```json" in result:
                result = result.split("```json")[1].split("```")[0].strip()
            elif "```" in result:
                result = result.split("```")[1].split("```")[0].strip()

            return json.loads(result)

        except Exception as e:
            logger.error(
                f"Error classifying intent: {e}, Raw response: {response.text if 'response' in locals() else 'N/A'}"
            )
            return {
                "intent": "answer_question",
                "entities": {},
            }  # Fallback to general question

    async def generate_skill_learning_path(
        self, target_skill: str, current_skills: List[str]
    ) -> str:
        """Generate personalized learning path for a skill"""

        prompt = f"""Create a learning path for someone who wants to learn {target_skill}.

Their current skills: {', '.join(current_skills) if current_skills else 'None listed'}

Provide:
1. Prerequisites needed
2. Step-by-step learning path (5-7 steps)
3. Estimated time for each step
4. Recommended resources (general types, not specific URLs)
5. Projects to practice

Keep it concise and actionable."""

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.8,
                    max_output_tokens=800,
                ),
            )

            return response.text

        except Exception as e:
            logger.error(f"Error generating learning path: {e}")
            return f"Unable to generate learning path for {target_skill} at this time."

    async def compare_skills(
        self, skill1: str, skill2: str, market_data: Dict[str, Any]
    ) -> str:
        """Compare two skills based on market trends"""

        prompt = f"""Compare these two skills in the job market:

Skill 1: {skill1}
- Job mentions: {market_data.get('skill1_mentions', 'N/A')}
- Growth rate: {market_data.get('skill1_growth', 'N/A')}

Skill 2: {skill2}
- Job mentions: {market_data.get('skill2_mentions', 'N/A')}
- Growth rate: {market_data.get('skill2_growth', 'N/A')}

Provide:
1. Which is more in-demand and why
2. Market trends for each
3. Career opportunities
4. Learning difficulty comparison
5. Recommendation for someone choosing between them

Keep it concise (under 300 words)."""

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    max_output_tokens=500,
                ),
            )

            return response.text

        except Exception as e:
            logger.error(f"Error comparing skills: {e}")
            return f"Unable to compare {skill1} and {skill2} at this time."

    async def answer_question(self, question: str, context_data: Dict[str, Any]) -> str:
        """Answer user question based on job market data"""

        prompt = f"""You are a freelance job market expert. Answer this question based on the provided data:

    Question: {question}

    Market Context:
    - Total jobs tracked: {context_data.get('total_jobs', 'N/A')}
    - Recent jobs (7d): {context_data.get('recent_jobs', 'N/A')}
    - Top skills: {', '.join(context_data.get('top_skills', [])[:5])}
    - Active companies: {context_data.get('total_companies', 'N/A')}

    Additional context: {context_data.get('additional_context', 'None')}

    Provide a helpful, accurate answer based on the data. Be specific and cite numbers when relevant.
    Keep response under 250 words."""

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    max_output_tokens=400,
                ),
            )

            # FIX: Ensure we always return a valid string
            answer = response.text if response.text else "No response generated"
            return answer.strip()

        except Exception as e:
            logger.error(f"Error answering question: {e}")
            # FIX: Return a proper default message
            return "I'm having trouble processing your question right now. Please try again or rephrase your question."

    async def summarize_jobs(self, jobs: List[Dict[str, Any]]) -> str:
        """Generate summary of job listings"""

        jobs_text = "\n\n".join(
            [
                f"- {job.get('position', 'N/A')} at {job.get('company', 'N/A')}\n"
                f"  Skills: {', '.join(job.get('tags', [])[:5])}\n"
                f"  Location: {job.get('location', 'Remote')}"
                for job in jobs[:10]
            ]
        )

        prompt = f"""Summarize these job listings and identify key trends:

{jobs_text}

Provide:
1. Common patterns (2-3 points)
2. Most sought-after skills
3. Notable companies
4. Remote vs location-based trend
5. Overall market insight

Keep it concise (under 200 words)."""

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.6,
                    max_output_tokens=350,
                ),
            )

            return response.text

        except Exception as e:
            logger.error(f"Error summarizing jobs: {e}")
            return "Summary unavailable at this time."

    def _build_trend_analysis_prompt(
        self,
        trending_skills: List[Dict[str, Any]],
        trending_roles: List[Dict[str, Any]],
        skill_clusters: Dict[str, List[str]],
        total_jobs: int,
    ) -> str:
        """Build comprehensive prompt for trend analysis"""

        skills_text = "\n".join(
            [
                f"- {skill['skill_name']}: {skill['current_mentions']} mentions "
                f"({skill['growth_percentage']})"
                for skill in trending_skills[:10]
            ]
        )

        roles_text = "\n".join(
            [
                f"- {role['role_name']}: {role['job_count']} jobs, "
                f"Top skills: {', '.join(role['top_skills'][:3])}"
                for role in trending_roles[:10]
            ]
        )

        clusters_text = "\n".join(
            [
                f"- {skill}: Related to {', '.join(related[:3])}"
                for skill, related in skill_clusters.items()
            ]
        )

        prompt = f"""Analyze this freelance job market data and provide key insights:

TRENDING SKILLS (Last 30 Days):
{skills_text}

TRENDING JOB ROLES:
{roles_text}

SKILL CLUSTERS (Technologies often used together):
{clusters_text}

TOTAL JOBS ANALYZED: {total_jobs}

Provide:
1. Top 3 emerging trends in the market
2. Skills gaining momentum and why
3. Recommendations for freelancers (which skills to learn)
4. Industry shifts or patterns you notice
5. Predictions for the next quarter

Be specific, data-driven, and actionable. Keep under 400 words."""

        return prompt

    async def chat_response(
        self,
        user_message: str,
        conversation_history: List[Dict[str, str]],
        context: Dict[str, Any],
    ) -> str:
        """Generate conversational response with context awareness"""

        history_text = "\n".join(
            [f"{msg['role']}: {msg['content']}" for msg in conversation_history[-5:]]
        )

        prompt = f"""You are a friendly AI assistant specialized in freelance job market trends.

Conversation History:
{history_text}

Current Market Context:
- Total jobs: {context.get('total_jobs', 'N/A')}
- Jobs today: {context.get('jobs_today', 'N/A')}
- Top trending skill: {context.get('top_skill', 'N/A')}

User: {user_message}

Respond naturally and helpfully. If the question is about job trends, use the context data.
Keep responses conversational and under 200 words."""

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.8,
                    max_output_tokens=350,
                ),
            )

            return response.text

        except Exception as e:
            logger.error(f"Error in chat response: {e}")
            return (
                "I'm having trouble right now. Could you try rephrasing your question?"
            )
