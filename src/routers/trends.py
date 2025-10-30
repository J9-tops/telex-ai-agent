from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from src.db.session import get_db
from src.db.repository import TrendRepository, SkillRepository
from src.schemas.job import TrendAnalysisSchema, SkillSchema, TrendQuery
from src.services.trend_analyzer import TrendAnalyzer

router = APIRouter(prefix="/api/trends", tags=["trends"])


@router.get("/latest", response_model=TrendAnalysisSchema)
async def get_latest_trends(db: Session = Depends(get_db)):
    """Get the latest trend analysis"""
    analysis = TrendRepository.get_latest_analysis(db)

    if not analysis:
        raise HTTPException(
            status_code=404, detail="No trend analysis available. Run analysis first."
        )

    return analysis


@router.get("/history")
async def get_trend_history(
    days: int = Query(30, ge=7, le=365, description="Number of days to look back"),
    limit: int = Query(10, ge=1, le=50, description="Maximum results"),
    db: Session = Depends(get_db),
):
    """Get historical trend analyses"""
    analyses = TrendRepository.get_analyses_by_period(db, days=days, limit=limit)
    return analyses


@router.post("/analyze")
async def run_trend_analysis(
    window_days: int = Query(30, ge=7, le=365, description="Analysis window in days"),
    db: Session = Depends(get_db),
):
    """Trigger a new trend analysis"""
    analyzer = TrendAnalyzer(window_days=window_days)
    result = await analyzer.run_full_analysis()

    return {"message": "Trend analysis completed", "result": result}


@router.get("/skills", response_model=List[SkillSchema])
async def get_skills(
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(50, ge=1, le=500, description="Maximum results"),
    db: Session = Depends(get_db),
):
    """Get skills with optional category filter"""
    if category:
        skills = SkillRepository.get_skills_by_category(db, category)
    else:
        skills = SkillRepository.get_top_skills(db, limit=limit)

    return skills


@router.get("/skills/trending")
async def get_trending_skills(
    window_days: int = Query(30, ge=7, le=365, description="Analysis window"),
    top_n: int = Query(20, ge=1, le=50, description="Number of results"),
    db: Session = Depends(get_db),
):
    """Get currently trending skills"""
    analyzer = TrendAnalyzer(window_days=window_days)
    trending = analyzer.analyze_skill_trends(db)

    return {"window_days": window_days, "trending_skills": trending[:top_n]}


@router.get("/roles/trending")
async def get_trending_roles(
    window_days: int = Query(30, ge=7, le=365, description="Analysis window"),
    top_n: int = Query(15, ge=1, le=50, description="Number of results"),
    db: Session = Depends(get_db),
):
    """Get currently trending job roles"""
    analyzer = TrendAnalyzer(window_days=window_days)
    trending = analyzer.analyze_role_trends(db)

    return {"window_days": window_days, "trending_roles": trending[:top_n]}


@router.get("/clusters")
async def get_skill_clusters(
    window_days: int = Query(30, ge=7, le=365, description="Analysis window"),
    db: Session = Depends(get_db),
):
    """Get skill clusters (skills that often appear together)"""
    analyzer = TrendAnalyzer(window_days=window_days)
    clusters = analyzer.identify_skill_clusters(db)

    return {"window_days": window_days, "skill_clusters": clusters}
