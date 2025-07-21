"""
Unit tests for agent functionality.
"""
import json
import pytest
from unittest.mock import Mock, patch, AsyncMock
import sys
import os

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from core.agents import StrictJSONAgent, SystemArchitect, AgentOrchestrator
from core.config import ConfigManager


@pytest.fixture
def mock_config():
    """Mock configuration manager."""
    config = Mock(spec=ConfigManager)
    config.get_llm_config.return_value = {
        "config_list": [{
            "model": "gpt-4",
            "api_key": "test-key"
        }],
        "temperature": 0.1,
        "response_format": {"type": "json_object"}
    }
    return config


@pytest.fixture
def mock_llm_response():
    """Mock LLM JSON response."""
    return json.dumps({
        "agent": "TestAgent",
        "action": "test_action",
        "status": "success",
        "result": {"test": "data"},
        "next_agent": None,
        "metadata": {
            "timestamp": "2024-01-01T00:00:00",
            "tokens_used": 100,
            "complexity_score": 0.5
        }
    })


class TestStrictJSONAgent:
    """Test StrictJSONAgent base class."""
    
    def test_initialization(self, mock_config):
        """Test agent initialization."""
        agent = StrictJSONAgent(
            name="TestAgent",
            role_description="Test agent for unit testing",
            llm_config=mock_config.get_llm_config("standard")
        )
        
        assert agent.name == "TestAgent"
        assert "JSON" in agent.system_message
        assert agent.human_input_mode == "NEVER"
        
    def test_process_valid_json(self, mock_config, mock_llm_response):
        """Test processing valid JSON response."""
        agent = StrictJSONAgent(
            name="TestAgent",
            role_description="Test agent",
            llm_config=mock_config.get_llm_config("standard")
        )
        
        messages = [{"content": mock_llm_response, "role": "assistant"}]
        result = agent.process_last_message(messages)
        
        assert result["agent"] == "TestAgent"
        assert result["status"] == "success"
        assert result["result"]["test"] == "data"
        
    def test_process_invalid_json(self, mock_config):
        """Test handling invalid JSON response."""
        agent = StrictJSONAgent(
            name="TestAgent",
            role_description="Test agent",
            llm_config=mock_config.get_llm_config("standard")
        )
        
        messages = [{"content": "This is not JSON", "role": "assistant"}]
        result = agent.process_last_message(messages)
        
        assert result["status"] == "error"
        assert "parse_error" in result["action"]
        assert result["next_agent"] is None


class TestSystemArchitect:
    """Test SystemArchitect agent."""
    
    def test_initialization(self, mock_config):
        """Test SystemArchitect initialization."""
        architect = SystemArchitect(mock_config.get_llm_config("high_performance"))
        
        assert architect.name == "SystemArchitect"
        assert "analyzing requirements" in architect.system_message.lower()
        
    @patch.object(SystemArchitect, 'generate_reply')
    def test_analyze_requirements(self, mock_generate_reply, mock_config):
        """Test requirements analysis."""
        architect = SystemArchitect(mock_config.get_llm_config("high_performance"))
        
        mock_response = json.dumps({
            "agent": "SystemArchitect",
            "action": "requirements_analyzed",
            "status": "success",
            "result": {
                "modules": ["auth", "api", "database"],
                "interfaces": ["REST API", "GraphQL"],
                "dependencies": {"api": ["auth", "database"]},
                "constraints": ["scalability", "security"],
                "technology_stack": ["Python", "FastAPI", "PostgreSQL"]
            },
            "next_agent": "PromptEngineer"
        })
        
        mock_generate_reply.return_value = mock_response
        
        requirements = {
            "project_name": "test_project",
            "description": "Test project description",
            "requirements": {"feature": "test"}
        }
        
        result = architect.analyze_requirements(requirements)
        
        assert result["status"] == "success"
        assert "modules" in result["result"]
        assert result["next_agent"] == "PromptEngineer"


class TestAgentOrchestrator:
    """Test AgentOrchestrator."""
    
    def test_initialization(self, mock_config):
        """Test orchestrator initialization."""
        orchestrator = AgentOrchestrator(mock_config)
        
        # Check all agents are initialized
        expected_agents = [
            "SystemArchitect", "PromptEngineer", "CodeGenerator",
            "CodeReviewer", "SecurityValidator", "TestRunner",
            "DocumentationGenerator", "QualityGate", "Executor"
        ]
        
        for agent_name in expected_agents:
            assert agent_name in orchestrator.agents
            
    def test_get_agent(self, mock_config):
        """Test getting agent by name."""
        orchestrator = AgentOrchestrator(mock_config)
        
        architect = orchestrator.get_agent("SystemArchitect")
        assert architect is not None
        assert architect.name == "SystemArchitect"
        
        non_existent = orchestrator.get_agent("NonExistent")
        assert non_existent is None
        
    def test_validate_agent_response(self, mock_config):
        """Test agent response validation."""
        orchestrator = AgentOrchestrator(mock_config)
        
        # Valid response
        valid_response = {
            "agent": "TestAgent",
            "action": "test",
            "status": "success",
            "result": {},
            "next_agent": None
        }
        assert orchestrator.validate_agent_response(valid_response) is True
        
        # Missing required field
        invalid_response = {
            "agent": "TestAgent",
            "action": "test",
            "status": "success"
            # Missing result and next_agent
        }
        assert orchestrator.validate_agent_response(invalid_response) is False
        
        # Invalid status
        invalid_status = {
            "agent": "TestAgent",
            "action": "test",
            "status": "invalid_status",
            "result": {},
            "next_agent": None
        }
        assert orchestrator.validate_agent_response(invalid_status) is False


@pytest.mark.asyncio
class TestIntegration:
    """Integration tests for agent system."""
    
    async def test_agent_communication_flow(self, mock_config):
        """Test agent communication flow."""
        orchestrator = AgentOrchestrator(mock_config)
        
        # Mock agent responses
        with patch.object(orchestrator.agents["SystemArchitect"], 'generate_reply') as mock_arch:
            mock_arch.return_value = json.dumps({
                "agent": "SystemArchitect",
                "action": "analyzed",
                "status": "success",
                "result": {"architecture": "defined"},
                "next_agent": "PromptEngineer"
            })
            
            # Simulate message flow
            initial_message = {"content": json.dumps({"requirements": "test"}), "role": "user"}
            response = orchestrator.agents["SystemArchitect"].generate_reply([initial_message])
            
            parsed_response = json.loads(response)
            assert orchestrator.validate_agent_response(parsed_response)
            assert parsed_response["next_agent"] == "PromptEngineer"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])