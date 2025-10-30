from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.services.job_scraper import JobScraper
import os

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/scrape")
async def trigger_scrape(db: Session = Depends(get_db)):
    """Manually trigger job scraping"""
    scraper = JobScraper(
        api_url=os.getenv("REMOTEOK_API_URL", "https://remoteok.com/api"),
        rate_limit=int(os.getenv("REMOTEOK_RATE_LIMIT", 60)),
    )

    result = await scraper.scrape_and_store()

    return {"message": "Scraping completed", "result": result}


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
        "scraper": {
            "enabled": True,
            "interval_minutes": int(os.getenv("JOB_FETCH_INTERVAL_MINUTES", 30)),
        },
    }
