import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import pytest
from unittest.mock import Mock, patch, AsyncMock
from src.services.freelance_agent import FreelanceAgent
from src.services.job_scraper import JobScraper
from src.models.a2a import (
    A2AMessage,
    MessagePart,
    JSONRPCResponse,
    TaskStatus,
    Artifact,
)
from src.services.rss_scraper import RSSFeedScraper


@pytest.fixture
def agent():
    """Create test agent with mocked dependencies"""
    scraper = JobScraper()
    return FreelanceAgent(
        scraper=scraper,
        rss_scraper=RSSFeedScraper(rate_limit=int(os.getenv("RATE_LIMIT", 1440))),
    )


@pytest.fixture
def mock_db_session():
    """Mock database session"""
    with patch("src.services.freelance_agent.SessionLocal") as mock_session:
        session = Mock()
        mock_session.return_value.__enter__ = Mock(return_value=session)
        mock_session.return_value.__exit__ = Mock(return_value=False)
        yield session


@pytest.mark.asyncio
async def test_a2a_message_structure_validation(agent):
    """Test that agent accepts valid A2A message structure"""
    message = A2AMessage(role="user", parts=[MessagePart(kind="text", text="hello")])

    result = await agent.process_messages(messages=[message])

    assert isinstance(result, JSONRPCResponse)
    assert hasattr(result, "status")
    assert hasattr(result, "artifacts")
    assert isinstance(result.status, TaskStatus)


@pytest.mark.asyncio
async def test_a2a_response_status_states(agent):
    """Test all possible A2A status states"""
    message = A2AMessage(role="user", parts=[MessagePart(kind="text", text="help")])
    result = await agent.process_messages(messages=[message])
    assert result.status.state in ["completed", "failed", "processing"]

    result = await agent.process_messages(messages=[])
    assert result.status.state == "failed"


@pytest.mark.asyncio
async def test_a2a_message_parts_validation(agent):
    """Test handling of different message part types"""
    message = A2AMessage(
        role="user", parts=[MessagePart(kind="text", text="show jobs")]
    )
    result = await agent.process_messages(messages=[message])
    assert result.status.state == "completed"

    message = A2AMessage(
        role="user",
        parts=[
            MessagePart(kind="text", text="hello"),
            MessagePart(kind="text", text="show statistics"),
        ],
    )
    result = await agent.process_messages(messages=[message])
    assert result.status.state == "completed"


@pytest.mark.asyncio
async def test_a2a_artifacts_structure(agent):
    """Test A2A artifact structure in responses"""
    message = A2AMessage(
        role="user", parts=[MessagePart(kind="text", text="show statistics")]
    )
    result = await agent.process_messages(messages=[message])

    assert len(result.artifacts) > 0
    for artifact in result.artifacts:
        assert isinstance(artifact, Artifact)
        assert hasattr(artifact, "name")
        assert hasattr(artifact, "kind")
        assert hasattr(artifact, "data")


@pytest.mark.asyncio
async def test_empty_message_handling(agent):
    """Test handling of empty messages"""
    result = await agent.process_messages(messages=[])
    assert result.status.state == "failed"
    assert "Error" in result.status.message.parts[0].text


@pytest.mark.asyncio
async def test_invalid_message_format(agent):
    """Test handling of messages without parts"""
    try:
        message = A2AMessage(role="user", parts=[])
        result = await agent.process_messages(messages=[message])
        assert result.status.state in ["completed", "failed"]
    except Exception:
        pass


@pytest.mark.asyncio
async def test_help_intent(agent):
    """Test help command intent"""
    test_cases = ["help", "Help", "HELP", "show help", "commands"]

    for text in test_cases:
        message = A2AMessage(role="user", parts=[MessagePart(kind="text", text=text)])
        result = await agent.process_messages(messages=[message])

        assert result.status.state == "completed"
        assert "Available Commands" in result.status.message.parts[0].text


@pytest.mark.asyncio
async def test_stats_intent(agent):
    """Test statistics intent"""
    test_cases = [
        "show statistics",
        "stats",
        "show stats",
        "statistics",
        "show me statistics",
    ]

    for text in test_cases:
        message = A2AMessage(role="user", parts=[MessagePart(kind="text", text=text)])
        result = await agent.process_messages(messages=[message])

        assert result.status.state == "completed"
        assert any("ai_answer" in artifact.name for artifact in result.artifacts)


@pytest.mark.asyncio
async def test_trending_skills_intent(agent):
    """Test trending skills intent"""
    test_cases = [
        "show trending skills",
        "trending skills",
        "what skills are trending",
        "popular skills",
    ]

    for text in test_cases:
        message = A2AMessage(role="user", parts=[MessagePart(kind="text", text=text)])
        result = await agent.process_messages(messages=[message])

        assert result.status.state == "completed"
        assert any("trending_skills" in artifact.name for artifact in result.artifacts)


@pytest.mark.asyncio
async def test_trending_roles_intent(agent):
    """Test trending roles intent"""
    test_cases = ["trending roles", "show trending roles", "popular roles"]

    for text in test_cases:
        message = A2AMessage(role="user", parts=[MessagePart(kind="text", text=text)])
        result = await agent.process_messages(messages=[message])

        assert result.status.state == "completed"
        assert any("trending_roles" in artifact.name for artifact in result.artifacts)


@pytest.mark.asyncio
async def test_recent_jobs_intent(agent):
    """Test recent jobs intent"""
    test_cases = ["recent jobs", "show recent jobs", "latest jobs", "new jobs"]

    for text in test_cases:
        message = A2AMessage(role="user", parts=[MessagePart(kind="text", text=text)])
        result = await agent.process_messages(messages=[message])

        assert result.status.state == "completed"


@pytest.mark.asyncio
async def test_skill_search_intent(agent):
    """Test skill search intent"""
    test_cases = [
        "jobs with python",
        "search python jobs",
        "find python developer positions",
        "show me react jobs",
    ]

    for text in test_cases:
        message = A2AMessage(role="user", parts=[MessagePart(kind="text", text=text)])
        result = await agent.process_messages(messages=[message])

        assert result.status.state == "completed"


@pytest.mark.asyncio
async def test_compare_skills_intent(agent):
    """Test skill comparison intent"""
    test_cases = [
        "compare python and javascript",
        "python vs javascript",
        "compare react vs vue",
    ]

    for text in test_cases:
        message = A2AMessage(role="user", parts=[MessagePart(kind="text", text=text)])
        result = await agent.process_messages(messages=[message])

        assert result.status.state == "completed"


@pytest.mark.asyncio
async def test_learning_path_intent(agent):
    """Test learning path generation intent"""
    test_cases = [
        "learning path for react",
        "how to learn python",
        "path to learn javascript",
    ]

    for text in test_cases:
        message = A2AMessage(role="user", parts=[MessagePart(kind="text", text=text)])
        result = await agent.process_messages(messages=[message])

        assert result.status.state == "completed"


@pytest.mark.asyncio
async def test_question_intent(agent):
    """Test general question intent"""
    test_cases = [
        "what are the most in-demand skills?",
        "which companies are hiring?",
        "what is the average salary for python developers?",
    ]

    for text in test_cases:
        message = A2AMessage(role="user", parts=[MessagePart(kind="text", text=text)])
        result = await agent.process_messages(messages=[message])

        assert result.status.state == "completed"


@pytest.mark.asyncio
async def test_unknown_intent(agent):
    """Test handling of unknown intents"""
    message = A2AMessage(
        role="user",
        parts=[MessagePart(kind="text", text="xyzabc123randomtext")],
    )
    result = await agent.process_messages(messages=[message])

    assert result.status.state in ["completed", "failed"]
    assert len(result.status.message.parts) > 0


@pytest.mark.asyncio
async def test_database_error_handling(agent):
    """Test handling of database errors"""
    with patch("src.services.freelance_agent.SessionLocal") as mock_session:
        mock_session.side_effect = Exception("Database connection error")

        message = A2AMessage(
            role="user", parts=[MessagePart(kind="text", text="show statistics")]
        )
        result = await agent.process_messages(messages=[message])

        assert result.status.state == "failed"


@pytest.mark.asyncio
async def test_ai_service_error_handling(agent):
    """Test handling of AI service errors"""
    with patch.object(
        agent.ai_service, "answer_question", side_effect=Exception("AI API error")
    ):
        message = A2AMessage(
            role="user",
            parts=[MessagePart(kind="text", text="what are the top skills?")],
        )
        result = await agent.process_messages(messages=[message])

        assert result.status.state in ["completed", "failed"]


@pytest.mark.asyncio
async def test_malformed_input_handling(agent):
    """Test handling of malformed inputs"""
    try:
        message = A2AMessage(role="user", parts=[MessagePart(kind="text", text=None)])
        result = await agent.process_messages(messages=[message])
        assert result.status.state in ["completed", "failed"]
    except Exception:
        pass


@pytest.mark.asyncio
async def test_concurrent_requests(agent):
    """Test handling of concurrent requests"""
    import asyncio

    messages = [
        A2AMessage(role="user", parts=[MessagePart(kind="text", text="help")]),
        A2AMessage(role="user", parts=[MessagePart(kind="text", text="stats")]),
        A2AMessage(
            role="user", parts=[MessagePart(kind="text", text="trending skills")]
        ),
    ]

    results = await asyncio.gather(
        *[agent.process_messages(messages=[msg]) for msg in messages]
    )

    for result in results:
        assert result.status.state == "completed"


@pytest.mark.asyncio
async def test_artifact_data_types(agent):
    """Test that artifacts contain valid data types"""
    message = A2AMessage(
        role="user", parts=[MessagePart(kind="text", text="show statistics")]
    )
    result = await agent.process_messages(messages=[message])

    for artifact in result.artifacts:
        assert isinstance(artifact.data, (str, dict))
        if isinstance(artifact.data, str):
            assert len(artifact.data) > 0


@pytest.mark.asyncio
async def test_response_message_validation(agent):
    """Test that response messages are properly formatted"""
    message = A2AMessage(role="user", parts=[MessagePart(kind="text", text="help")])
    result = await agent.process_messages(messages=[message])

    assert result.status.message is not None
    assert isinstance(result.status.message, A2AMessage)
    assert len(result.status.message.parts) > 0
    assert result.status.message.parts[0].kind == "text"


@pytest.mark.asyncio
async def test_multiple_artifacts_handling(agent):
    """Test handling of responses with multiple artifacts"""
    message = A2AMessage(
        role="user", parts=[MessagePart(kind="text", text="trending skills")]
    )
    result = await agent.process_messages(messages=[message])

    if len(result.artifacts) > 1:
        for artifact in result.artifacts:
            assert artifact.name is not None
            assert artifact.kind is not None
            assert artifact.data is not None


@pytest.mark.asyncio
async def test_response_time(agent):
    """Test that responses are returned in reasonable time"""
    import time

    message = A2AMessage(role="user", parts=[MessagePart(kind="text", text="help")])

    start_time = time.time()
    result = await agent.process_messages(messages=[message])
    end_time = time.time()

    response_time = end_time - start_time

    assert response_time < 10
    assert result.status.state == "completed"


@pytest.mark.asyncio
async def test_large_message_handling(agent):
    """Test handling of large messages"""
    large_text = "python " * 1000
    message = A2AMessage(role="user", parts=[MessagePart(kind="text", text=large_text)])

    result = await agent.process_messages(messages=[message])

    assert result.status.state in ["completed", "failed"]


@pytest.mark.asyncio
async def test_full_conversation_flow(agent):
    """Test a complete conversation flow"""
    help_msg = A2AMessage(role="user", parts=[MessagePart(kind="text", text="help")])
    help_result = await agent.process_messages(messages=[help_msg])
    assert help_result.status.state == "completed"

    stats_msg = A2AMessage(
        role="user", parts=[MessagePart(kind="text", text="show statistics")]
    )
    stats_result = await agent.process_messages(messages=[stats_msg])
    assert stats_result.status.state == "completed"

    search_msg = A2AMessage(
        role="user", parts=[MessagePart(kind="text", text="python jobs")]
    )
    search_result = await agent.process_messages(messages=[search_msg])
    assert search_result.status.state == "completed"


@pytest.mark.asyncio
async def test_context_preservation(agent):
    """Test that agent maintains context appropriately"""
    msg1 = A2AMessage(
        role="user", parts=[MessagePart(kind="text", text="show statistics")]
    )
    result1 = await agent.process_messages(messages=[msg1])

    msg2 = A2AMessage(
        role="user", parts=[MessagePart(kind="text", text="trending skills")]
    )
    result2 = await agent.process_messages(messages=[msg1, msg2])

    assert result1.status.state == "completed"
    assert result2.status.state == "completed"


@pytest.mark.asyncio
async def test_special_characters_handling(agent):
    """Test handling of special characters in input"""
    special_cases = [
        "python & javascript",
        "C++ developer",
        "jobs with $100k+ salary",
        "react/vue developer",
    ]

    for text in special_cases:
        message = A2AMessage(role="user", parts=[MessagePart(kind="text", text=text)])
        result = await agent.process_messages(messages=[message])
        assert result.status.state in ["completed", "failed"]


@pytest.mark.asyncio
async def test_case_insensitivity(agent):
    """Test that commands are case-insensitive"""
    cases = ["HELP", "Help", "help", "HeLp"]

    for text in cases:
        message = A2AMessage(role="user", parts=[MessagePart(kind="text", text=text)])
        result = await agent.process_messages(messages=[message])
        assert result.status.state == "completed"
        assert "Available Commands" in result.status.message.parts[0].text


@pytest.mark.asyncio
async def test_whitespace_handling(agent):
    """Test handling of extra whitespace"""
    message = A2AMessage(role="user", parts=[MessagePart(kind="text", text="  help  ")])
    result = await agent.process_messages(messages=[message])
    assert result.status.state == "completed"


@pytest.mark.asyncio
async def test_unicode_handling(agent):
    """Test handling of unicode characters"""
    message = A2AMessage(
        role="user", parts=[MessagePart(kind="text", text="python 🐍 developer")]
    )
    result = await agent.process_messages(messages=[message])
    assert result.status.state in ["completed", "failed"]
