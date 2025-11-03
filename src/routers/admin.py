from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.services.job_scraper import JobScraper
from src.services.rss_scraper import RSSFeedScraper
import os

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/scrape/rss")
async def trigger_rss_scrape(db: Session = Depends(get_db)):
    """Manually trigger RSS feed scraping"""
    scraper = RSSFeedScraper(rate_limit=int(os.getenv("RATE_LIMIT", 60)))

    result = await scraper.scrape_and_store()

    return {
        "message": "RSS scraping completed",
        "result": result,
        "feeds_scraped": result.get("feeds_processed", 0),
    }


@router.post("/scrape/api")
async def trigger_api_scrape(db: Session = Depends(get_db)):
    """Manually trigger API scraping (legacy)"""
    if not os.getenv("API_URL"):
        return {
            "message": "API scraping not configured",
            "result": {"success": False, "error": "API_URL not set"},
        }

    scraper = JobScraper(
        api_url=os.getenv("API_URL"),
        rate_limit=int(os.getenv("RATE_LIMIT", 60)),
    )

    result = await scraper.scrape_and_store()

    return {"message": "API scraping completed", "result": result}


@router.post("/scrape/all")
async def trigger_all_scraping(db: Session = Depends(get_db)):
    """Trigger both RSS and API scraping"""
    results = {}

    # RSS scraping
    rss_scraper = RSSFeedScraper(rate_limit=int(os.getenv("RATE_LIMIT", 60)))
    rss_result = await rss_scraper.scrape_and_store()
    results["rss"] = rss_result

    # API scraping (if configured)
    if os.getenv("API_URL"):
        api_scraper = JobScraper(
            api_url=os.getenv("API_URL"),
            rate_limit=int(os.getenv("RATE_LIMIT", 60)),
        )
        api_result = await api_scraper.scrape_and_store()
        results["api"] = api_result
    else:
        results["api"] = {"success": False, "message": "API_URL not configured"}

    total_jobs = rss_result.get("jobs_added", 0) + results["api"].get("jobs_added", 0)

    return {
        "message": "All scraping completed",
        "results": results,
        "total_jobs_added": total_jobs,
    }


@router.get("/status")
async def get_system_status(db: Session = Depends(get_db)):
    """Get system status and health"""
    from src.db.repository import JobRepository, SkillRepository

    return {
        "status": "operational",
        "database": {
            "connected": True,
            "total_jobs": JobRepository.get_total_jobs(db),
            "total_skills": len(SkillRepository.get_all_skills(db, limit=10000)),
        },
        "scrapers": {
            "rss": {
                "enabled": True,
                "interval_minutes": int(os.getenv("RSS_SCRAPE_INTERVAL_MINUTES", 60)),
                "feeds": [
                    "Full-Stack Programming",
                    "Frontend Programming",
                    "Programming",
                    "Design",
                    "DevOps/SysAdmin",
                ],
            },
            "api": {
                "enabled": bool(os.getenv("API_URL")),
                "interval_minutes": int(os.getenv("JOB_FETCH_INTERVAL_MINUTES", 30)),
            },
        },
        "data_sources": {
            "primary": "We Work Remotely RSS Feeds",
            "secondary": "Custom API" if os.getenv("API_URL") else None,
        },
    }


@router.get("/feeds")
async def get_feed_status():
    """Get RSS feed configuration and status"""
    rss_scraper = RSSFeedScraper()

    return {
        "total_feeds": len(rss_scraper.rss_feeds),
        "feeds": [
            {
                "url": feed,
                "category": feed.split("/")[-1]
                .replace(".rss", "")
                .replace("-", " ")
                .title(),
            }
            for feed in rss_scraper.rss_feeds
        ],
        "scrape_interval_minutes": int(os.getenv("RSS_SCRAPE_INTERVAL_MINUTES", 60)),
    }
