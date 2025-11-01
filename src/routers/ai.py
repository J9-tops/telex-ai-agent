from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session


from src.schemas.ai import CompareSkillsRequest, LearningPathRequest, QuestionRequest
from src.db.session import get_db
from src.db.repository import JobRepository, SkillRepository
from src.services.ai import AIService

router = APIRouter(prefix="/api/ai", tags=["ai"])

ai_service = AIService()


@router.post("/compare-skills")
async def compare_skills(request: CompareSkillsRequest, db: Session = Depends(get_db)):
    """Compare two skills using AI analysis"""

    all_skills = SkillRepository.get_all_skills(db)
    skill1_data = next(
        (s for s in all_skills if request.skill1.lower() in s.name.lower()), None
    )
    skill2_data = next(
        (s for s in all_skills if request.skill2.lower() in s.name.lower()), None
    )

    market_data = {
        "skill1_mentions": skill1_data.total_mentions if skill1_data else 0,
        "skill2_mentions": skill2_data.total_mentions if skill2_data else 0,
        "skill1_growth": "N/A",
        "skill2_growth": "N/A",
    }

    comparison = await ai_service.compare_skills(
        request.skill1, request.skill2, market_data
    )

    return {
        "skill1": request.skill1,
        "skill2": request.skill2,
        "market_data": market_data,
        "comparison": comparison,
    }


@router.post("/learning-path")
async def get_learning_path(request: LearningPathRequest):
    """Generate personalized learning path for a skill"""

    learning_path = await ai_service.generate_skill_learning_path(
        target_skill=request.target_skill, current_skills=request.current_skills
    )

    return {
        "target_skill": request.target_skill,
        "current_skills": request.current_skills,
        "learning_path": learning_path,
    }


@router.post("/ask")
async def ask_question(request: QuestionRequest, db: Session = Depends(get_db)):
    """Ask any question about the job market"""

    from sqlalchemy import func
    from src.models.job import Job

    total_jobs = JobRepository.get_total_jobs(db)
    recent_jobs = JobRepository.get_jobs_count_by_period(db, hours=24 * 7)
    top_skills = [skill.name for skill in SkillRepository.get_top_skills(db, limit=5)]
    total_companies = db.query(func.count(func.distinct(Job.company))).scalar()

    context_data = {
        "total_jobs": total_jobs,
        "recent_jobs": recent_jobs,
        "top_skills": top_skills,
        "total_companies": total_companies,
        "additional_context": "Data from API",
    }

    answer = await ai_service.answer_question(request.question, context_data)

    return {"question": request.question, "answer": answer, "context": context_data}


@router.get("/summarize-jobs")
async def summarize_jobs(
    days: int = Query(7, ge=1, le=30, description="Number of days to analyze"),
    limit: int = Query(20, ge=1, le=100, description="Number of jobs to include"),
    db: Session = Depends(get_db),
):
    """Get AI-powered summary of recent jobs"""

    jobs = JobRepository.get_recent_jobs(db, days=days, limit=limit)

    if not jobs:
        raise HTTPException(status_code=404, detail="No jobs found")

    jobs_data = [
        {
            "position": job.position,
            "company": job.company,
            "tags": job.tags,
            "location": job.location,
            "date_posted": job.date_posted.isoformat(),
        }
        for job in jobs
    ]

    summary = await ai_service.summarize_jobs(jobs_data)

    return {"period_days": days, "jobs_analyzed": len(jobs), "summary": summary}


@router.post("/analyze-job")
async def analyze_job_description(
    job_id: str = Query(..., description="Job ID to analyze"),
    db: Session = Depends(get_db),
):
    """Analyze a job description using AI"""

    job = JobRepository.get_job_by_id(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if not job.description:
        raise HTTPException(status_code=400, detail="Job has no description")

    analysis = await ai_service.analyze_job_description(job.description)

    return {
        "job_id": job.id,
        "job_title": job.position,
        "company": job.company,
        "analysis": analysis,
    }
