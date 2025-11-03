import os
import logging
import time
import hashlib
import asyncio
from typing import List, Dict, Any, Optional
from collections import deque
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

        self._request_cache = {}

        self.cache_ttls = {
            "intent_classification": 3600,
            "trend_insights": 86400,
            "skill_comparison": 43200,
            "learning_path": 604800,
            "job_analysis": 3600,
            "answer_question": 1800,
            "summarize_jobs": 3600,
            "chat_response": 0,
            "default": 1800,
        }

        self.request_times = deque(maxlen=60)
        self.max_requests_per_minute = 10

        self.total_requests = 0
        self.cache_hits = 0

        logger.info(f"AI Service initialized with model: {self.model}")
        logger.info(f"Cache TTLs: {self.cache_ttls}")

    def _get_cache_key(self, prompt: str, cache_type: str = "default") -> str:
        """Generate cache key from prompt and type"""
        return f"{cache_type}:{hashlib.md5(prompt.encode()).hexdigest()}"

    async def _check_rate_limit(self):
        """Check and enforce rate limiting"""
        now = time.time()

        while self.request_times and now - self.request_times[0] > 60:
            self.request_times.popleft()

        if len(self.request_times) >= self.max_requests_per_minute:
            wait_time = 60 - (now - self.request_times[0])
            logger.warning(f"Rate limit reached. Waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)

        self.request_times.append(now)

    async def _cached_generate(
        self, prompt: str, cache_type: str = "default", use_cache: bool = True, **kwargs
    ):
        """Generate content with type-specific caching support"""
        cache_key = self._get_cache_key(prompt, cache_type)
        cache_ttl = self.cache_ttls.get(cache_type, self.cache_ttls["default"])

        if use_cache and cache_ttl > 0 and cache_key in self._request_cache:
            cached_time, cached_response = self._request_cache[cache_key]
            if time.time() - cached_time < cache_ttl:
                self.cache_hits += 1
                logger.info(
                    f"[CACHE HIT] Type: {cache_type}, "
                    f"Key: {cache_key[:20]}..., "
                    f"Age: {int(time.time() - cached_time)}s, "
                    f"TTL: {cache_ttl}s"
                )
                return cached_response

        await self._check_rate_limit()

        self.total_requests += 1
        logger.info(
            f"[GEMINI API CALL #{self.total_requests}] "
            f"Type: {cache_type}, "
            f"Prompt length: {len(prompt)} chars"
        )

        try:
            response = self.client.models.generate_content(
                model=self.model, contents=prompt, **kwargs
            )

            if use_cache and cache_ttl > 0:
                self._request_cache[cache_key] = (time.time(), response)
                logger.info(
                    f"[CACHE STORE] Type: {cache_type}, "
                    f"Key: {cache_key[:20]}..., "
                    f"TTL: {cache_ttl}s"
                )

            return response

        except Exception as e:
            logger.error(f"[GEMINI API ERROR] Type: {cache_type}, Error: {str(e)}")
            raise

    def clear_cache(self, cache_type: Optional[str] = None):
        """Clear the request cache (optionally for specific type)"""
        if cache_type:
            keys_to_delete = [
                k for k in self._request_cache.keys() if k.startswith(f"{cache_type}:")
            ]
            for key in keys_to_delete:
                del self._request_cache[key]
            logger.info(
                f"Cleared cache for type: {cache_type} ({len(keys_to_delete)} entries)"
            )
        else:
            self._request_cache.clear()
            logger.info("All cache cleared")

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
            response = await self._cached_generate(
                prompt=prompt,
                cache_type="trend_insights",
                use_cache=True,
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
            response = await self._cached_generate(
                prompt=prompt,
                cache_type="job_analysis",  # 1-hour cache
                use_cache=True,
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

        prompt = f"""Classify this query into ONE intent. Respond with ONLY valid JSON, no explanation.

Query: "{user_query}"

Available intents:
- get_trending_skills: show/list trending/popular/top skills or technologies
- get_trending_roles: show/list trending/popular roles or positions
- search_jobs: find/search/show jobs (with or without specific tech)
- get_statistics: show stats/statistics/numbers/overview
- run_analysis: analyze/deep dive/full analysis
- scrape_jobs: update/fetch/scrape/refresh jobs
- get_latest_analysis: latest/recent analysis or report
- compare_skills: compare X vs Y or X versus Y
- get_learning_path: learn/study/how to learn a skill
- answer_question: general questions about market/trends
- get_help: help/commands/what can you do

Response format:
{{"intent": "intent_name", "entities": {{"key": "value"}}}}

Examples:
"show trending skills" -> {{"intent": "get_trending_skills", "entities": {{}}}}
"find React jobs" -> {{"intent": "search_jobs", "entities": {{"job_query": "React"}}}}
"compare Python vs JavaScript" -> {{"intent": "compare_skills", "entities": {{"skill1": "Python", "skill2": "JavaScript"}}}}
"learn React" -> {{"intent": "get_learning_path", "entities": {{"target_skill": "React"}}}}
"""

        try:
            logger.info(f"[CLASSIFY INTENT] Query: {user_query[:50]}...")

            response = await self._cached_generate(
                prompt=prompt,
                cache_type="intent_classification",  # 1-hour cache
                use_cache=True,
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=150,
                ),
            )

            result = response.text.strip()

            result = result.replace("```json", "").replace("```", "").strip()

            import json

            parsed = json.loads(result)

            logger.info(
                f"[INTENT CLASSIFIED] {parsed.get('intent')} with entities: {parsed.get('entities', {})}"
            )

            return parsed

        except Exception as e:
            logger.error(
                f"Error classifying intent: {e}, Raw response: {response.text if 'response' in locals() else 'N/A'}"
            )
            return {
                "intent": "get_help",
                "entities": {},
            }

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
            response = await self._cached_generate(
                prompt=prompt,
                cache_type="learning_path",
                use_cache=True,
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
            response = await self._cached_generate(
                prompt=prompt,
                cache_type="skill_comparison",  # 12-hour cache
                use_cache=True,
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
            response = await self._cached_generate(
                prompt=prompt,
                cache_type="answer_question",  # 30-minute cache
                use_cache=True,
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    max_output_tokens=400,
                ),
            )

            return response.text

        except Exception as e:
            logger.error(f"Error answering question: {e}")
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
            response = await self._cached_generate(
                prompt=prompt,
                cache_type="summarize_jobs",
                use_cache=True,
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
            response = await self._cached_generate(
                prompt=prompt,
                cache_type="chat_response",
                use_cache=False,
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

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about API usage"""
        cache_age_distribution = {}
        now = time.time()

        for key, (cached_time, _) in self._request_cache.items():
            cache_type = key.split(":")[0]
            age = int(now - cached_time)
            if cache_type not in cache_age_distribution:
                cache_age_distribution[cache_type] = []
            cache_age_distribution[cache_type].append(age)

        return {
            "total_requests": self.total_requests,
            "cache_hits": self.cache_hits,
            "cache_hit_rate": (
                f"{(self.cache_hits / self.total_requests * 100):.1f}%"
                if self.total_requests > 0
                else "0%"
            ),
            "cache_size": len(self._request_cache),
            "cache_by_type": {k: len(v) for k, v in cache_age_distribution.items()},
            "recent_requests_count": len(self.request_times),
            "cache_ttls": self.cache_ttls,
            "max_requests_per_minute": self.max_requests_per_minute,
        }
