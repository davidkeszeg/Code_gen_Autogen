"""
Enterprise AutoGen agent definitions with strict JSON communication.
"""
import json
from typing import Dict, Any, List, Optional
import autogen
from autogen import AssistantAgent, UserProxyAgent
import logging

logger = logging.getLogger(__name__)


class StrictJSONAgent(AssistantAgent):
    """Base agent class enforcing JSON-only communication."""
    
    def __init__(self, name: str, role_description: str, llm_config: Dict[str, Any]):
        """Initialize agent with strict JSON communication."""
        
        system_message = f"""You are {name}, {role_description}.

CRITICAL RULES:
1. You MUST respond ONLY with valid JSON
2. NO conversational text, explanations, or apologies
3. Use this EXACT structure for ALL responses:
{{
    "agent": "{name}",
    "action": "action_performed",
    "status": "success|error|pending",
    "result": {{
        // Action-specific results
    }},
    "next_agent": "AgentName|null",
    "metadata": {{
        "timestamp": "ISO8601",
        "tokens_used": integer,
        "complexity_score": float
    }}
}}

ROLE: {role_description}

ERROR HANDLING: If you encounter an error, set status="error" and include error details in result.error field."""
        
        super().__init__(
            name=name,
            system_message=system_message,
            llm_config={
                **llm_config,
                "response_format": {"type": "json_object"}
            },
            human_input_mode="NEVER",
            max_consecutive_auto_reply=3
        )
    
    def process_last_message(self, messages: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Process and validate last message as JSON."""
        if not messages:
            return None
            
        try:
            last_message = messages[-1]
            content = last_message.get("content", "")
            
            # Parse JSON content
            if isinstance(content, str):
                return json.loads(content)
            return content
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON from {self.name}: {e}")
            return {
                "agent": self.name,
                "action": "parse_error",
                "status": "error",
                "result": {"error": str(e)},
                "next_agent": None
            }


class SystemArchitect(StrictJSONAgent):
    """System architect for analyzing requirements and designing architecture."""
    
    def __init__(self, llm_config: Dict[str, Any]):
        super().__init__(
            name="SystemArchitect",
            role_description="""Enterprise system architect responsible for:
- Analyzing high-level requirements
- Designing modular system architecture
- Defining interfaces and dependencies
- Creating technical specifications
- Establishing coding standards and constraints""",
            llm_config=llm_config
        )
        
    def analyze_requirements(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze requirements and create architecture design."""
        prompt = {
            "action": "analyze_requirements",
            "requirements": requirements,
            "output_format": {
                "modules": ["list of module definitions"],
                "interfaces": ["list of interface specifications"],
                "dependencies": {"module": ["dependencies"]},
                "constraints": ["technical constraints"],
                "technology_stack": ["recommended technologies"]
            }
        }
        
        response = self.generate_reply([{"content": json.dumps(prompt), "role": "user"}])
        return json.loads(response)


class PromptEngineer(StrictJSONAgent):
    """Prompt engineer for creating detailed code generation prompts."""
    
    def __init__(self, llm_config: Dict[str, Any]):
        super().__init__(
            name="PromptEngineer",
            role_description="""Prompt engineering specialist responsible for:
- Converting architecture specs into detailed prompts
- Ensuring zero ambiguity in instructions
- Defining exact code structure and patterns
- Specifying performance and security requirements
- Creating test scenarios and edge cases""",
            llm_config=llm_config
        )


class CodeGenerator(StrictJSONAgent):
    """Code generator for creating production-ready code."""
    
    def __init__(self, llm_config: Dict[str, Any]):
        super().__init__(
            name="CodeGenerator",
            role_description="""Senior code generation specialist responsible for:
- Writing clean, efficient, production-ready code
- Following architectural specifications exactly
- Implementing proper error handling and logging
- Adding comprehensive documentation
- Ensuring type safety and security""",
            llm_config=llm_config
        )


class CodeReviewer(StrictJSONAgent):
    """Code reviewer for validating generated code."""
    
    def __init__(self, llm_config: Dict[str, Any]):
        super().__init__(
            name="CodeReviewer",
            role_description="""Code review specialist responsible for:
- Validating code against specifications
- Checking for bugs and edge cases
- Ensuring coding standards compliance
- Verifying security best practices
- Assessing performance characteristics""",
            llm_config=llm_config
        )


class SecurityValidator(StrictJSONAgent):
    """Security validator for comprehensive security analysis."""
    
    def __init__(self, llm_config: Dict[str, Any]):
        super().__init__(
            name="SecurityValidator",
            role_description="""Security validation specialist responsible for:
- Scanning for security vulnerabilities
- Checking input validation and sanitization
- Verifying authentication and authorization
- Detecting potential injection attacks
- Ensuring secure coding practices""",
            llm_config=llm_config
        )


class TestRunner(StrictJSONAgent):
    """Test runner for executing and validating code."""
    
    def __init__(self, llm_config: Dict[str, Any]):
        super().__init__(
            name="TestRunner",
            role_description="""Test execution specialist responsible for:
- Creating comprehensive test suites
- Executing unit and integration tests
- Performing edge case testing
- Measuring code coverage
- Validating performance requirements""",
            llm_config=llm_config
        )


class DocumentationGenerator(StrictJSONAgent):
    """Documentation generator for creating comprehensive docs."""
    
    def __init__(self, llm_config: Dict[str, Any]):
        super().__init__(
            name="DocumentationGenerator",
            role_description="""Documentation specialist responsible for:
- Creating API documentation
- Writing user guides
- Generating code comments
- Creating architecture diagrams
- Documenting deployment procedures""",
            llm_config=llm_config
        )


class QualityGate(StrictJSONAgent):
    """Quality gate for final validation and approval."""
    
    def __init__(self, llm_config: Dict[str, Any]):
        super().__init__(
            name="QualityGate",
            role_description="""Quality assurance lead responsible for:
- Final quality validation
- Verifying all requirements are met
- Checking test coverage and results
- Validating security compliance
- Approving for production deployment""",
            llm_config=llm_config
        )


class ExecutorAgent(UserProxyAgent):
    """Executor agent for actual code execution and file operations."""
    
    def __init__(self):
        super().__init__(
            name="Executor",
            human_input_mode="NEVER",
            code_execution_config={
                "work_dir": "generated_code",
                "use_docker": True,
                "timeout": 300
            },
            system_message="Execute code and file operations. Report results in JSON format.",
            default_auto_reply=json.dumps({
                "agent": "Executor",
                "action": "ready",
                "status": "success",
                "result": {"message": "Ready to execute"},
                "next_agent": None
            })
        )


class AgentOrchestrator:
    """Orchestrate agent interactions with cost optimization."""
    
    def __init__(self, config_manager):
        self.config = config_manager
        self.agents = self._initialize_agents()
        logger.info("Agent orchestrator initialized")
        
    def _initialize_agents(self) -> Dict[str, StrictJSONAgent]:
        """Initialize all agents with appropriate configurations."""
        
        agents = {
            # High-performance tier (critical decisions)
            "SystemArchitect": SystemArchitect(
                self.config.get_llm_config("high_performance")
            ),
            "SecurityValidator": SecurityValidator(
                self.config.get_llm_config("high_performance")
            ),
            "QualityGate": QualityGate(
                self.config.get_llm_config("high_performance")
            ),
            
            # Standard tier (moderate complexity)
            "PromptEngineer": PromptEngineer(
                self.config.get_llm_config("standard")
            ),
            "CodeReviewer": CodeReviewer(
                self.config.get_llm_config("standard")
            ),
            
            # Local tier (high-volume operations)
            "CodeGenerator": CodeGenerator(
                self.config.get_llm_config("local")
            ),
            "TestRunner": TestRunner(
                self.config.get_llm_config("local")
            ),
            "DocumentationGenerator": DocumentationGenerator(
                self.config.get_llm_config("local")
            ),
            
            # Executor (no LLM)
            "Executor": ExecutorAgent()
        }
        
        return agents
    
    def get_agent(self, agent_name: str) -> Optional[StrictJSONAgent]:
        """Get agent by name."""
        return self.agents.get(agent_name)
    
    def validate_agent_response(self, response: Dict[str, Any]) -> bool:
        """Validate agent response format."""
        required_fields = ["agent", "action", "status", "result", "next_agent"]
        
        for field in required_fields:
            if field not in response:
                logger.error(f"Missing required field: {field}")
                return False
                
        if response["status"] not in ["success", "error", "pending"]:
            logger.error(f"Invalid status: {response['status']}")
            return False
            
        return True