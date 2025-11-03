import httpx
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
from sqlalchemy.orm import Session

from src.db.repository import JobRepository, SkillRepository
from src.db.session import get_db_context
import os

logger = logging.getLogger(__name__)

API_URL = os.getenv("API_URL")
RATE_LIMIT = int(os.getenv("RATE_LIMIT", 60))


class JobScraper:
    """Service for scraping jobs from API"""

    def __init__(self, api_url: str = API_URL, rate_limit: int = 60):
        self.api_url = api_url
        self.rate_limit = rate_limit
        self.last_fetch_time = None

    async def fetch_jobs(self) -> List[Dict[str, Any]]:
        """Fetch jobs from API"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {
                    "User-Agent": "FreelanceTrendsAgent/1.0",
                    "Accept": "application/json",
                }
                response = await client.get(self.api_url, headers=headers)
                response.raise_for_status()

                data = response.json()

                if isinstance(data, list) and len(data) > 0:
                    jobs = (
                        data[1:]
                        if isinstance(data[0], dict) and "api" in data[0]
                        else data
                    )
                    logger.info(f"Fetched {len(jobs)} jobs from API")
                    return jobs

                return []

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching jobs: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching jobs: {e}")
            return []

    def parse_job(self, raw_job: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse raw job data into our schema"""
        try:
            job_id = str(raw_job.get("id", ""))
            if not job_id:
                return None

            date_posted = raw_job.get("date")
            if isinstance(date_posted, str):
                try:
                    date_posted = datetime.fromisoformat(
                        date_posted.replace("Z", "+00:00")
                    )
                except:
                    date_posted = datetime.utcnow()
            elif isinstance(date_posted, (int, float)):
                date_posted = datetime.fromtimestamp(date_posted)
            else:
                date_posted = datetime.utcnow()

            tags = raw_job.get("tags", [])
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(",")]
            elif not isinstance(tags, list):
                tags = []

            salary_min = raw_job.get("salary_min")
            salary_max = raw_job.get("salary_max")

            parsed_job = {
                "id": job_id,
                "slug": raw_job.get("slug", f"job-{job_id}"),
                "company": raw_job.get("company", "Unknown"),
                "company_logo": raw_job.get("company_logo"),
                "position": raw_job.get("position", ""),
                "tags": tags,
                "location": raw_job.get("location", "Remote"),
                "description": raw_job.get("description"),
                "url": raw_job.get("url"),
                "salary_min": int(salary_min) if salary_min else None,
                "salary_max": int(salary_max) if salary_max else None,
                "date_posted": date_posted,
                "remote_allowed": True,
                "apply_url": raw_job.get("apply_url"),
                "raw_data": raw_job,
            }

            return parsed_job

        except Exception as e:
            logger.error(f"Error parsing job: {e}")
            return None

    async def scrape_and_store(self) -> Dict[str, Any]:
        """Scrape jobs and store in database"""
        logger.info("Starting job scraping...")

        raw_jobs = await self.fetch_jobs()

        if not raw_jobs:
            logger.warning("No jobs fetched")
            return {"success": False, "jobs_added": 0, "skills_added": 0}

        jobs_added = 0
        skills_added = 0
        skills_set = set()

        with get_db_context() as db:
            for raw_job in raw_jobs:
                parsed_job = self.parse_job(raw_job)
                if not parsed_job:
                    continue

                existing = JobRepository.get_job_by_id(db, parsed_job["id"])
                if existing:
                    continue

                try:
                    JobRepository.create_job(db, parsed_job)
                    jobs_added += 1

                    for tag in parsed_job.get("tags", []):
                        if tag and tag.lower() not in skills_set:
                            SkillRepository.create_or_update_skill(
                                db, name=tag, category="technology"
                            )
                            skills_set.add(tag.lower())
                            skills_added += 1

                except Exception as e:
                    logger.error(f"Error storing job {parsed_job['id']}: {e}")
                    continue

        logger.info(
            f"Scraping completed: {jobs_added} jobs added, {skills_added} skills tracked"
        )

        return {
            "success": True,
            "jobs_added": jobs_added,
            "skills_added": skills_added,
            "total_fetched": len(raw_jobs),
        }


async def run_scheduled_scraping(scraper: JobScraper, interval_minutes: int = 1440):
    """Run scraping on a schedule"""
    while True:
        try:
            result = await scraper.scrape_and_store()
            logger.info(f"Scheduled scraping result: {result}")
        except Exception as e:
            logger.error(f"Error in scheduled scraping: {e}")

        await asyncio.sleep(interval_minutes * 60)
