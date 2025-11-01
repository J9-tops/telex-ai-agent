import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))


import pytest
from unittest.mock import Mock, patch
from src.services.ai import AIService


@pytest.fixture
def ai_service():
    """Create test AI service"""
    with patch.dict("os.environ", {"API_KEY": "test-api-key"}):
        return AIService()


@pytest.mark.asyncio
async def test_generate_trend_insights(ai_service):
    """Test trend insights generation"""
    trending_skills = [
        {
            "skill_name": "python",
            "current_mentions": 100,
            "previous_mentions": 80,
            "growth_rate": 25.0,
            "growth_percentage": "+25.0%",
        }
    ]

    trending_roles = [
        {
            "role_name": "Developer",
            "job_count": 50,
            "growth_rate": 10.0,
            "top_skills": ["python", "javascript"],
        }
    ]

    skill_clusters = {"python": ["django", "flask", "fastapi"]}

    with patch.object(ai_service.client.models, "generate_content") as mock_generate:
        mock_response = Mock()
        mock_response.text = "Python shows strong growth with 25% increase..."
        mock_generate.return_value = mock_response

        insights = await ai_service.generate_trend_insights(
            trending_skills=trending_skills,
            trending_roles=trending_roles,
            skill_clusters=skill_clusters,
            total_jobs=1000,
        )

        assert insights is not None
        assert len(insights) > 0
        mock_generate.assert_called_once()


@pytest.mark.asyncio
async def test_compare_skills(ai_service):
    """Test skill comparison"""
    market_data = {
        "skill1_mentions": 100,
        "skill2_mentions": 80,
        "skill1_growth": "+20%",
        "skill2_growth": "+15%",
    }

    with patch.object(ai_service.client.models, "generate_content") as mock_generate:
        mock_response = Mock()
        mock_response.text = "Python shows stronger demand..."
        mock_generate.return_value = mock_response

        comparison = await ai_service.compare_skills(
            "Python", "JavaScript", market_data
        )

        assert comparison is not None
        assert len(comparison) > 0


@pytest.mark.asyncio
async def test_generate_learning_path(ai_service):
    """Test learning path generation"""
    with patch.object(ai_service.client.models, "generate_content") as mock_generate:
        mock_response = Mock()
        mock_response.text = "Step 1: Learn basics...\nStep 2: Practice..."
        mock_generate.return_value = mock_response

        learning_path = await ai_service.generate_skill_learning_path(
            target_skill="React", current_skills=["JavaScript", "HTML"]
        )

        assert learning_path is not None
        assert "Step" in learning_path


@pytest.mark.asyncio
async def test_answer_question(ai_service):
    """Test question answering"""
    context_data = {
        "total_jobs": 5000,
        "recent_jobs": 500,
        "top_skills": ["Python", "JavaScript", "React"],
        "total_companies": 200,
    }

    with patch.object(ai_service.client.models, "generate_content") as mock_generate:
        mock_response = Mock()
        mock_response.text = "Based on the data, the most in-demand skills are..."
        mock_generate.return_value = mock_response

        answer = await ai_service.answer_question(
            "What are the most in-demand skills?", context_data
        )

        assert answer is not None
        assert len(answer) > 0


@pytest.mark.asyncio
async def test_error_handling(ai_service):
    """Test error handling in AI service"""
    with patch.object(ai_service.client.models, "generate_content") as mock_generate:
        mock_generate.side_effect = Exception("API Error")

        insights = await ai_service.generate_trend_insights([], [], {}, 100)
        assert "Unable to generate" in insights


@pytest.mark.asyncio
async def test_summarize_jobs(ai_service):
    """Test job summarization"""
    jobs = [
        {
            "position": "Python Developer",
            "company": "TechCorp",
            "tags": ["python", "django", "postgresql"],
            "location": "Remote",
        },
        {
            "position": "Frontend Developer",
            "company": "WebCo",
            "tags": ["react", "typescript", "css"],
            "location": "Remote",
        },
    ]

    with patch.object(ai_service.client.models, "generate_content") as mock_generate:
        mock_response = Mock()
        mock_response.text = "Recent jobs show strong demand for Python and React..."
        mock_generate.return_value = mock_response

        summary = await ai_service.summarize_jobs(jobs)

        assert summary is not None
        assert len(summary) > 0


@pytest.mark.asyncio
async def test_analyze_job_description(ai_service):
    """Test job description analysis"""
    job_description = """
    We are looking for a Senior Python Developer with 5+ years of experience.
    Required skills: Python, Django, PostgreSQL, Docker, AWS.
    Responsibilities include building scalable APIs and mentoring junior developers.
    """

    with patch.object(ai_service.client.models, "generate_content") as mock_generate:
        mock_response = Mock()
        mock_response.text = """
        ```json
        {
            "required_skills": ["Python", "Django", "PostgreSQL", "Docker", "AWS"],
            "experience_level": "senior",
            "key_responsibilities": ["Building APIs", "Mentoring"],
            "technology_stack": ["Python", "Django"],
            "job_category": "backend"
        }
        ```
        """
        mock_generate.return_value = mock_response

        analysis = await ai_service.analyze_job_description(job_description)

        assert analysis is not None
        assert "required_skills" in analysis
        assert analysis["experience_level"] == "senior"
