import httpx
import asyncio
import feedparser
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from src.db.repository import JobRepository, SkillRepository
from src.db.session import get_db_context
import os

logger = logging.getLogger(__name__)


class RSSFeedScraper:
    """Service for scraping jobs from RSS feeds"""

    def __init__(self, rate_limit: int = 1440):
        self.rate_limit = rate_limit
        rss_feeds_env = os.getenv("RSS_FEEDS", "")
        self.rss_feeds = [
            url.strip() for url in rss_feeds_env.split(",") if url.strip()
        ]
        self.last_fetch_time = None

    async def fetch_feed(self, feed_url: str) -> List[Dict[str, Any]]:
        """Fetch and parse a single RSS feed"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {
                    "User-Agent": "FreelanceTrendsAgent/1.0",
                    "Accept": "application/rss+xml, application/xml, text/xml",
                }
                response = await client.get(feed_url, headers=headers)
                response.raise_for_status()

                feed = feedparser.parse(response.text)

                jobs = []
                for entry in feed.entries:
                    try:
                        job = self._parse_rss_entry(entry)
                        if job:
                            jobs.append(job)
                    except Exception as e:
                        logger.error(f"Error parsing entry: {e}")
                        continue

                logger.info(f"Fetched {len(jobs)} jobs from {feed_url}")
                return jobs

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching feed {feed_url}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching feed {feed_url}: {e}")
            return []

    def _parse_rss_entry(self, entry) -> Optional[Dict[str, Any]]:
        """Parse a single RSS feed entry into job data"""
        try:
            job_id = entry.get("guid", entry.get("link", ""))
            if not job_id:
                return None

            title = entry.get("title", "")
            company, position = self._parse_title(title)

            description_html = entry.get("description", "")
            description_data = self._parse_description(description_html)

            pub_date = entry.get("published", entry.get("pubDate", ""))
            date_posted = self._parse_date(pub_date)

            location = entry.get("region", "Remote")
            if not location or location == "Anywhere in the World":
                location = "Remote"

            tags = self._extract_tags(description_data)

            parsed_job = {
                "id": self._generate_job_id(job_id),
                "slug": job_id.split("/")[-1] if "/" in job_id else job_id,
                "company": company,
                "company_logo": None,
                "position": position,
                "tags": tags,
                "location": location,
                "description": description_data.get("full_description", ""),
                "url": entry.get("link", ""),
                "salary_min": None,
                "salary_max": None,
                "date_posted": date_posted,
                "remote_allowed": True,
                "apply_url": entry.get("link", ""),
                "raw_data": {
                    "title": title,
                    "category": entry.get("category", ""),
                    "type": entry.get("type", "Full-Time"),
                    "region": entry.get("region", ""),
                    "skills": entry.get("skills", ""),
                },
            }

            return parsed_job

        except Exception as e:
            logger.error(f"Error parsing RSS entry: {e}")
            return None

    def _parse_title(self, title: str) -> tuple[str, str]:
        """Parse title to extract company and position"""
        if ":" in title:
            parts = title.split(":", 1)
            company = parts[0].strip()
            position = parts[1].strip()
        else:
            company = "Unknown"
            position = title.strip()

        return company, position

    def _parse_description(self, html_content: str) -> Dict[str, Any]:
        """Parse HTML description to extract structured data"""
        if not html_content:
            return {"full_description": "", "sections": {}}

        try:
            soup = BeautifulSoup(html_content, "html.parser")

            full_text = soup.get_text(separator="\n", strip=True)

            sections = {}

            for strong_tag in soup.find_all("strong"):
                section_title = strong_tag.get_text(strip=True).rstrip(":")

                content = []
                for sibling in strong_tag.next_siblings:
                    if sibling.name == "strong":
                        break
                    if isinstance(sibling, str):
                        text = sibling.strip()
                        if text:
                            content.append(text)
                    elif sibling.name:
                        text = sibling.get_text(strip=True)
                        if text:
                            content.append(text)

                if content:
                    sections[section_title.lower()] = " ".join(content)

            return {
                "full_description": full_text,
                "sections": sections,
            }

        except Exception as e:
            logger.error(f"Error parsing description HTML: {e}")
            return {"full_description": html_content, "sections": {}}

    def _extract_tags(self, description_data: Dict[str, Any]) -> List[str]:
        """Extract skills/tags from description"""
        tags = set()

        tech_keywords = [
            "python",
            "javascript",
            "typescript",
            "react",
            "vue",
            "angular",
            "node",
            "nodejs",
            "django",
            "flask",
            "fastapi",
            "express",
            "docker",
            "kubernetes",
            "aws",
            "azure",
            "gcp",
            "devops",
            "postgresql",
            "mongodb",
            "mysql",
            "redis",
            "graphql",
            "rest",
            "ci/cd",
            "git",
            "linux",
            "java",
            "golang",
            "ruby",
            "php",
            "machine learning",
            "ai",
            "data science",
            "tensorflow",
            "pytorch",
            "frontend",
            "backend",
            "fullstack",
            "mobile",
            "ios",
            "android",
            "html",
            "css",
            "sass",
            "tailwind",
            "bootstrap",
            "webpack",
        ]

        full_text = description_data.get("full_description", "").lower()

        for keyword in tech_keywords:
            if keyword in full_text:
                tags.add(keyword.title())

        return list(tags)[:15]

    def _parse_date(self, date_str: str) -> datetime:
        """Parse publication date string to datetime"""
        if not date_str:
            return datetime.utcnow()

        try:
            from email.utils import parsedate_to_datetime

            return parsedate_to_datetime(date_str)
        except:
            try:
                return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            except:
                return datetime.utcnow()

    def _generate_job_id(self, guid: str) -> str:
        """Generate a unique job ID from GUID"""
        import hashlib

        return hashlib.md5(guid.encode()).hexdigest()[:16]

    async def fetch_all_feeds(self) -> List[Dict[str, Any]]:
        """Fetch jobs from all RSS feeds concurrently"""
        logger.info(f"Fetching from {len(self.rss_feeds)} RSS feeds...")

        tasks = [self.fetch_feed(feed_url) for feed_url in self.rss_feeds]
        results = await asyncio.gather(*tasks)

        all_jobs = []
        for jobs in results:
            all_jobs.extend(jobs)

        logger.info(f"Fetched total of {len(all_jobs)} jobs from all feeds")
        return all_jobs

    async def scrape_and_store(self) -> Dict[str, Any]:
        """Scrape jobs from RSS feeds and store in database"""
        logger.info("Starting RSS feed scraping...")

        raw_jobs = await self.fetch_all_feeds()

        if not raw_jobs:
            logger.warning("No jobs fetched from RSS feeds")
            return {
                "success": False,
                "jobs_added": 0,
                "skills_added": 0,
                "feeds_processed": len(self.rss_feeds),
            }

        jobs_added = 0
        jobs_updated = 0
        skills_added = 0
        skills_set = set()

        with get_db_context() as db:
            for job_data in raw_jobs:
                try:
                    existing = JobRepository.get_job_by_id(db, job_data["id"])

                    if existing:
                        jobs_updated += 1
                    else:
                        JobRepository.create_job(db, job_data)
                        jobs_added += 1

                    for tag in job_data.get("tags", []):
                        if tag and tag.lower() not in skills_set:
                            SkillRepository.create_or_update_skill(
                                db, name=tag, category="technology"
                            )
                            skills_set.add(tag.lower())
                            skills_added += 1

                except Exception as e:
                    logger.error(f"Error storing job {job_data.get('id')}: {e}")
                    continue

        logger.info(
            f"RSS scraping completed: {jobs_added} new jobs, "
            f"{jobs_updated} updated, {skills_added} skills tracked"
        )

        return {
            "success": True,
            "jobs_added": jobs_added,
            "jobs_updated": jobs_updated,
            "skills_added": skills_added,
            "total_fetched": len(raw_jobs),
            "feeds_processed": len(self.rss_feeds),
        }


async def run_scheduled_rss_scraping(
    scraper: RSSFeedScraper, interval_minutes: int = 1440, skip_first: bool = True
):
    """Run RSS scraping on a schedule"""
    if skip_first:
        await asyncio.sleep(interval_minutes * 60)
    while True:
        try:
            result = await scraper.scrape_and_store()
            logger.info(f"Scheduled RSS scraping result: {result}")
        except Exception as e:
            logger.error(f"Error in scheduled RSS scraping: {e}")

        await asyncio.sleep(interval_minutes * 60)
