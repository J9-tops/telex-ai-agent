import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))


import pytest
from src.services.freelance_agent import FreelanceAgent
from src.services.job_scraper import JobScraper
from src.models.a2a import A2AMessage, MessagePart


@pytest.fixture
def agent():
    """Create test agent"""
    scraper = JobScraper()
    return FreelanceAgent(scraper=scraper)


@pytest.mark.asyncio
async def test_help_intent(agent):
    """Test help intent"""
    message = A2AMessage(role="user", parts=[MessagePart(kind="text", text="help")])

    result = await agent.process_messages(messages=[message])

    assert result.status.state == "completed"
    assert "Available Commands" in result.status.message.parts[0].text


@pytest.mark.asyncio
async def test_stats_intent(agent):
    """Test statistics intent"""
    message = A2AMessage(
        role="user", parts=[MessagePart(kind="text", text="show statistics")]
    )

    result = await agent.process_messages(messages=[message])

    assert result.status.state == "completed"
    assert len(result.artifacts) > 0
    assert result.artifacts[0].name == "statistics"


@pytest.mark.asyncio
async def test_trending_skills_intent(agent):
    """Test trending skills intent"""
    message = A2AMessage(
        role="user", parts=[MessagePart(kind="text", text="show trending skills")]
    )

    result = await agent.process_messages(messages=[message])

    assert result.status.state == "completed"
    assert any("trending_skills" in artifact.name for artifact in result.artifacts)


@pytest.mark.asyncio
async def test_error_handling(agent):
    """Test error handling"""
    result = await agent.process_messages(messages=[])

    assert result.status.state == "failed"
    assert "Error" in result.status.message.parts[0].text
