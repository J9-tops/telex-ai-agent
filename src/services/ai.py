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

            if response and response.text:
                return response.text
            raise ValueError("Empty response")

        except Exception as e:
            logger.error(f"Error generating insights: {e}")
            return "Trend analysis completed. Check the detailed data for insights."

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
        """Classify the user's intent with more flexible parsing."""

        user_lower = user_query.lower()

        if any(
            word in user_lower
            for word in ["trending skill", "top skill", "popular tech", "hot tech"]
        ):
            return {"intent": "get_trending_skills", "entities": {}}

        if any(
            word in user_lower
            for word in [
                "trending role",
                "popular job",
                "job role",
                "trending position",
            ]
        ):
            return {"intent": "get_trending_roles", "entities": {}}

        if any(
            word in user_lower
            for word in ["search job", "find job", "job opening", "show job"]
        ):
            query = (
                user_query.lower()
                .replace("search", "")
                .replace("find", "")
                .replace("jobs", "")
                .strip()
            )
            return {"intent": "search_jobs", "entities": {"job_query": query}}

        if any(
            word in user_lower
            for word in ["statistic", "stat", "overview", "summary", "how many"]
        ):
            return {"intent": "get_statistics", "entities": {}}

        if any(
            word in user_lower
            for word in ["analyze trend", "run analysis", "deep dive", "analyze"]
        ):
            return {"intent": "run_analysis", "entities": {}}

        if any(
            word in user_lower
            for word in ["scrape", "update job", "fetch job", "refresh"]
        ):
            return {"intent": "scrape_jobs", "entities": {}}

        if any(
            word in user_lower
            for word in ["latest analysis", "recent analysis", "last report"]
        ):
            return {"intent": "get_latest_analysis", "entities": {}}

        if any(
            word in user_lower
            for word in ["learn", "learning path", "study", "how to become", "roadmap"]
        ):
            skill = user_query.lower()
            for remove in [
                "learn",
                "learning path",
                "study",
                "how to",
                "become",
                "create a",
                "for",
                "who wants to",
            ]:
                skill = skill.replace(remove, "")
            skill = skill.strip()
            return {"intent": "get_learning_path", "entities": {"target_skill": skill}}

        if "compar" in user_lower and (
            "vs" in user_lower or "versus" in user_lower or " or " in user_lower
        ):
            words = (
                user_query.lower()
                .replace("compare", "")
                .replace("vs", " ")
                .replace("versus", " ")
                .replace(" or ", " ")
                .split()
            )
            skills = [
                w.strip()
                for w in words
                if len(w) > 2 and w not in ["and", "the", "with"]
            ]
            if len(skills) >= 2:
                return {
                    "intent": "compare_skills",
                    "entities": {"skill1": skills[0], "skill2": skills[1]},
                }

        if any(
            word in user_lower
            for word in ["help", "what can you", "capabilities", "commands"]
        ):
            return {"intent": "get_help", "entities": {}}

        return {"intent": "answer_question", "entities": {}}

    async def generate_skill_learning_path(self, target_skill: str) -> str:
        """Generate personalized learning path for a skill with better error handling"""

        prompt = f"""Create a comprehensive learning path for {target_skill}.

Structure your response as follows:

**Prerequisites:**
- List 2-3 foundational skills needed

**Learning Path:**
1. **Fundamentals** (Timeframe: X weeks)
   - Key concepts to learn
   - What to practice

2. **Intermediate** (Timeframe: X weeks)
   - Advanced topics
   - Projects to build

3. **Advanced** (Timeframe: X weeks)
   - Expert-level concepts
   - Real-world applications

**Recommended Resources:**
- Types of learning materials (courses, books, docs)
- Practice platforms

**Practice Projects:**
- 3-4 project ideas from beginner to advanced

Keep it practical and actionable. Total length: 300-500 words."""

        try:
            logger.info(f"Generating learning path for: {target_skill}")

            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    max_output_tokens=1000,
                    top_p=0.9,
                ),
            )

            if response and response.text and len(response.text.strip()) > 50:
                logger.info("Successfully generated learning path")
                return response.text.strip()
            else:
                logger.warning(
                    f"Short or empty response: {response.text if response else 'None'}"
                )
                raise ValueError("Empty or invalid response from AI")

        except Exception as e:
            logger.error(f"Error generating learning path: {e}", exc_info=True)

            return f"""**Learning Path for {target_skill.title()}**

**Prerequisites:**
- Basic programming fundamentals
- Understanding of software development concepts
- Familiarity with version control (Git)

**Learning Path:**

1. **Fundamentals** (4-6 weeks)
   - Core concepts and terminology
   - Basic syntax and common patterns
   - Simple exercises and tutorials
   - Set up development environment

2. **Intermediate Skills** (6-8 weeks)
   - Advanced features and techniques
   - Best practices and design patterns
   - Build small to medium projects
   - Code review and debugging

3. **Advanced Topics** (8-12 weeks)
   - Performance optimization
   - Security considerations
   - Testing and CI/CD
   - Production deployment

**Recommended Resources:**
- Official documentation and guides
- Interactive coding platforms
- Video courses (YouTube, Udemy, Coursera)
- Community forums and Q&A sites
- Open source projects for reference

**Practice Projects:**
1. **Beginner:** Simple CRUD application
2. **Intermediate:** Full-featured web app with database
3. **Advanced:** Scalable application with authentication
4. **Expert:** Contribute to open source projects

**Timeline:** 3-6 months with consistent daily practice

💡 **Tip:** Focus on building real projects rather than just following tutorials. Learn by doing!"""

    async def compare_skills(
        self, skill1: str, skill2: str, market_data: Dict[str, Any]
    ) -> str:
        """Compare two skills based on market trends"""

        prompt = f"""Compare {skill1} and {skill2} for someone deciding which to learn:

Market Data:
- {skill1}: {market_data.get('skill1_mentions', 'N/A')} job mentions
- {skill2}: {market_data.get('skill2_mentions', 'N/A')} job mentions

Provide:
1. **Market Demand:** Which is more sought-after and why
2. **Learning Curve:** Difficulty comparison
3. **Career Opportunities:** Job roles and salaries
4. **Future Outlook:** Which has better long-term prospects
5. **Recommendation:** Clear advice for someone choosing between them

Be specific and practical. Length: 250-350 words."""

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    max_output_tokens=600,
                ),
            )

            if response and response.text:
                return response.text
            raise ValueError("Empty response")

        except Exception as e:
            logger.error(f"Error comparing skills: {e}")

            s1_mentions = market_data.get("skill1_mentions", 0)
            s2_mentions = market_data.get("skill2_mentions", 0)

            return f"""**Comparing {skill1.title()} vs {skill2.title()}**

**Market Demand:**
Based on our job data, {skill1} has {s1_mentions} mentions while {skill2} has {s2_mentions} mentions. {'Both are highly valued' if min(s1_mentions, s2_mentions) > 50 else 'Consider market trends carefully'}.

**Learning Curve:**
Both skills require dedication. Start with fundamentals and build projects to gain proficiency.

**Career Opportunities:**
Both open doors to various roles including developer, engineer, and specialist positions.

**Recommendation:**
Choose based on:
- Your current skill set
- Career goals
- Project requirements
- Personal interest

Consider learning both over time for versatility!"""

    async def answer_question(self, question: str, context_data: Dict[str, Any]) -> str:
        """Answer user question based on job market data with better fallback"""

        prompt = f"""Answer this question about the freelance job market:

Question: {question}

Available Data:
- Total jobs tracked: {context_data.get('total_jobs', 0)}
- Recent jobs (7 days): {context_data.get('recent_jobs', 0)}
- Top skills: {', '.join(context_data.get('top_skills', [])[:5])}
- Active companies: {context_data.get('total_companies', 0)}
- Data sources: {context_data.get('data_sources', 'Multiple RSS feeds')}

Provide a helpful, data-driven answer. Be specific and cite numbers when relevant.
Keep it concise (150-250 words)."""

        try:
            logger.info(f"Answering question: {question[:100]}...")

            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    max_output_tokens=500,
                    top_p=0.9,
                ),
            )

            if response and response.text and len(response.text.strip()) > 20:
                logger.info("Successfully generated answer")
                return response.text.strip()
            else:
                raise ValueError("Empty or too short response")

        except Exception as e:
            logger.error(f"Error answering question: {e}", exc_info=True)

            total = context_data.get("total_jobs", 0)
            recent = context_data.get("recent_jobs", 0)
            skills = context_data.get("top_skills", [])

            return f"""Based on our current job market data:

We're tracking **{total} total jobs** with **{recent} posted in the last 7 days**. 

The most in-demand skills right now are: **{', '.join(skills[:5]) if skills else 'various technologies'}**.

For more specific insights about "{question}", try asking about:
- Trending skills or roles
- Specific job searches
- Market statistics
- Learning paths for particular technologies

Our data comes from We Work Remotely RSS feeds covering Full-Stack, Frontend, Programming, Design, and DevOps categories."""

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
    Keep response under 200 words."""

        try:
            logger.info(f"Answering question: {question[:100]}...")
            logger.debug(f"Context data: {context_data}")

            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    max_output_tokens=400,
                ),
            )

            logger.info("AI response received for question")
            logger.debug(
                f"Response text: {response.text[:200] if response.text else 'None'}..."
            )

            if not response.text or response.text.strip() == "":
                logger.error("Empty response from AI for question answering")
                return "I apologize, but I'm having trouble generating a response right now. Please try rephrasing your question or contact support if this persists."

            return response.text.strip()

        except Exception as e:
            logger.error(f"Error answering question: {e}", exc_info=True)
            logger.error(f"Question was: {question}")
            logger.error(f"Context was: {context_data}")
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
                f"- {role['role_name']}: {role['job_count']} jobs"
                for role in trending_roles[:10]
            ]
        )

        return f"""Analyze this freelance job market data:

TRENDING SKILLS:
{skills_text}

TRENDING ROLES:
{roles_text}

TOTAL JOBS: {total_jobs}

Provide:
1. Top 3 market trends
2. Skills to learn and why
3. Predictions for next quarter

Keep under 400 words."""

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
