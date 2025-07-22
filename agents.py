import json
from pathlib import Path
from typing import Dict, Any, List, Optional
import autogen
from autogen import AssistantAgent, UserProxyAgent
import logging

from ..config.settings import ConfigManager

logger = logging.getLogger(__name__)

# --- ALAPOSZTÁLY A SZIGORÚ KOMMUNIKÁCIÓHOZ ---
class StrictJSONAgent(AssistantAgent):
    def __init__(self, name: str, role_description: str, llm_config: Dict[str, Any]):
        system_message = f"""You are the {name}, a critical component in an automated software generation pipeline.
# YOUR ROLE
{role_description}
# CRITICAL RULES
1.  **JSON-ONLY OUTPUT**: You MUST respond ONLY with a single, valid JSON object.
2.  **STRICT STRUCTURE**: You MUST use this EXACT structure for ALL your responses:
    ```json
    {{
      "agent": "{name}",
      "action": "A short, descriptive name for the action you performed.",
      "status": "success | error",
      "result": {{}},
      "next_agent": "The name of the agent who should receive your output, or null."
    }}
    ```
3.  **ERROR HANDLING**: If you cannot fulfill the request, set `status` to "error" and provide a clear error message in `result.error`.
"""
        super().__init__(
            name=name, system_message=system_message,
            llm_config={**llm_config, "response_format": {"type": "json_object"}},
            human_input_mode="NEVER", max_consecutive_auto_reply=1
        )

# --- SPECIALIZÁLT ÜGYNÖKÖK ---
class SystemArchitect(StrictJSONAgent):
    def __init__(self, llm_config: Dict[str, Any]):
        super().__init__(name="SystemArchitect", role_description="Analyze high-level requirements and design a robust, modular system architecture.", llm_config=llm_config)

class PromptEngineer(StrictJSONAgent):
    def __init__(self, llm_config: Dict[str, Any]):
        super().__init__(name="PromptEngineer", role_description="Convert system architecture into detailed prompts for the CodeGenerator.", llm_config=llm_config)

class CodeGenerator(StrictJSONAgent):
    def __init__(self, llm_config: Dict[str, Any]):
        super().__init__(name="CodeGenerator", role_description="Write clean, production-ready code based *exactly* on the prompts provided.", llm_config=llm_config)

class CodeReviewer(StrictJSONAgent):
    def __init__(self, llm_config: Dict[str, Any]):
        super().__init__(name="CodeReviewer", role_description="Perform a critical review of the generated code for bugs, standards, and performance.", llm_config=llm_config)

class SecurityValidator(StrictJSONAgent):
    def __init__(self, llm_config: Dict[str, Any]):
        super().__init__(name="SecurityValidator", role_description="Conduct a thorough security analysis of the generated code.", llm_config=llm_config)

class TestRunner(StrictJSONAgent):
    def __init__(self, llm_config: Dict[str, Any]):
        super().__init__(name="TestRunner", role_description="Generate a comprehensive suite of unit and integration tests.", llm_config=llm_config)

class DocumentationGenerator(StrictJSONAgent):
    def __init__(self, llm_config: Dict[str, Any]):
        super().__init__(name="DocumentationGenerator", role_description="Create comprehensive and user-friendly documentation for the code.", llm_config=llm_config)

class QualityGate(StrictJSONAgent):
    def __init__(self, llm_config: Dict[str, Any]):
        super().__init__(name="QualityGate", role_description="Act as the final quality assurance step, providing a final pass/fail decision.", llm_config=llm_config)

# --- VÉGREHAJTÓ ÜGYNÖK ---
class ExecutorAgent(UserProxyAgent):
    def __init__(self, work_dir: str = "generated_code"):
        super().__init__(
            name="Executor", human_input_mode="NEVER",
            code_execution_config={"work_dir": work_dir, "use_docker": True, "timeout": 300},
            default_auto_reply="", is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("TERMINATE")
        )
        self.register_function(function_map={"save_file": self.save_file, "run_tests": self.run_tests})

    def save_file(self, filename: str, content: str) -> str:
        filepath = Path(self._code_execution_config["work_dir"]) / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(filepath, "w", encoding="utf-8") as f: f.write(content)
            logger.info(f"Fájl sikeresen elmentve: {filepath}")
            return f"Fájl '{filename}' sikeresen elmentve."
        except Exception as e:
            logger.error(f"Hiba a(z) {filename} fájl mentésekor: {e}", exc_info=True)
            return f"Hiba a fájl mentésekor: {e}"

    def run_tests(self) -> str:
        exit_code, logs, _ = self.execute_code_blocks([("shell", "pytest --json-report")])
        logger.info(f"Tesztek lefutottak, exit code: {exit_code}")
        return logs

# --- ORKESZTRÁTOR ---
class AgentOrchestrator:
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self.agents = self._initialize_agents()
        # A hibás _setup_function_calling() metódus eltávolítva.
        logger.info("AgentOrchestrator inicializálva.")
        
    def _initialize_agents(self) -> Dict[str, autogen.Agent]:
        agent_tier_mapping = {
            "SystemArchitect": "high_performance", "SecurityValidator": "high_performance",
            "QualityGate": "high_performance", "PromptEngineer": "standard",
            "CodeReviewer": "standard", "CodeGenerator": "local",
            "TestRunner": "local", "DocumentationGenerator": "local"
        }
        agent_classes = {
            "SystemArchitect": SystemArchitect, "PromptEngineer": PromptEngineer,
            "CodeGenerator": CodeGenerator, "CodeReviewer": CodeReviewer,
            "SecurityValidator": SecurityValidator, "TestRunner": TestRunner,
            "DocumentationGenerator": DocumentationGenerator, "QualityGate": QualityGate,
        }
        agents = {}
        for name, tier in agent_tier_mapping.items():
            try:
                agents[name] = agent_classes[name](llm_config=self.config.get_llm_config(tier))
            except ValueError as e:
                logger.error(f"Nem sikerült létrehozni a(z) {name} ügynököt: {e}.")
        agents["Executor"] = ExecutorAgent()
        return agents
    
    def get_agent(self, agent_name: str) -> Optional[autogen.Agent]:
        return self.agents.get(agent_name)
    
    def validate_agent_response(self, response: Dict[str, Any]) -> bool:
        required = ["agent", "action", "status", "result"]
        if not all(k in response for k in required):
            logger.error(f"Validációs hiba: hiányzó kulcsok. Kötelező: {required}")
            return False
        return True