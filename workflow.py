import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
import logging
import autogen
from autogen import GroupChat, GroupChatManager
from statemachine import StateMachine, State
from enum import Enum  # <<< EZ A HIÁNYZÓ, KRITIKUS SOR

# A projekt többi részéből importáljuk a szükséges osztályokat
from .agents import AgentOrchestrator
from ..config.settings import ConfigManager

logger = logging.getLogger(__name__)

# 1. ÁLLAPOTOK DEFINIÁLÁSA (Enum a típusbiztonságért)
class WorkflowState(Enum):
    """A munkafolyamat lehetséges állapotait definiáló felsorolás."""
    INITIALIZED = "initialized"
    REQUIREMENTS_ANALYZED = "requirements_analyzed"
    ARCHITECTURE_DESIGNED = "architecture_designed"
    PROMPT_ENGINEERED = "prompt_engineered"
    CODE_GENERATED = "code_generated"
    CODE_REVIEWED = "code_reviewed"
    SECURITY_VALIDATED = "security_validated"
    TESTS_EXECUTED = "tests_executed"
    DOCUMENTATION_GENERATED = "documentation_generated"
    QUALITY_APPROVED = "quality_approved"
    COMPLETED = "completed"
    FAILED = "failed"


# 2. AZ ÁLLAPOTGÉP (FSM)
class CodeGenerationFSM(StateMachine):
    """A kódgenerálási munkafolyamatot leíró, robusztus állapotgép."""
    
    # Állapotok a te dokumentációd alapján, Enum-ot használva
    initialized = State(WorkflowState.INITIALIZED.value, initial=True)
    requirements_analyzed = State(WorkflowState.REQUIREMENTS_ANALYZED.value)
    architecture_designed = State(WorkflowState.ARCHITECTURE_DESIGNED.value)
    prompt_engineered = State(WorkflowState.PROMPT_ENGINEERED.value)
    code_generated = State(WorkflowState.CODE_GENERATED.value)
    code_reviewed = State(WorkflowState.CODE_REVIEWED.value)
    security_validated = State(WorkflowState.SECURITY_VALIDATED.value)
    tests_executed = State(WorkflowState.TESTS_EXECUTED.value)
    documentation_generated = State(WorkflowState.DOCUMENTATION_GENERATED.value)
    quality_approved = State(WorkflowState.QUALITY_APPROVED.value)
    completed = State(WorkflowState.COMPLETED.value, final=True)
    failed = State(WorkflowState.FAILED.value, final=True)

    # Átmenetek
    analyze_requirements = initialized.to(requirements_analyzed)
    design_architecture = requirements_analyzed.to(architecture_designed)
    engineer_prompt = architecture_designed.to(prompt_engineered)
    generate_code = prompt_engineered.to(code_generated)
    review_code = code_generated.to(code_reviewed)
    validate_security = code_reviewed.to(security_validated)
    execute_tests = security_validated.to(tests_executed)
    generate_documentation = tests_executed.to(documentation_generated)
    approve_quality = documentation_generated.to(quality_approved)
    complete_workflow = quality_approved.to(completed)
    
    # Hibakezelés és újrapróbálkozási logika
    fail_from_any = (initialized.to(failed) | requirements_analyzed.to(failed) | architecture_designed.to(failed) | prompt_engineered.to(failed) | code_generated.to(failed) | code_reviewed.to(failed) | security_validated.to(failed) | tests_executed.to(failed) | documentation_generated.to(failed) | quality_approved.to(failed))
    retry_from_review = code_reviewed.to(prompt_engineered)
    retry_from_security = security_validated.to(code_generated)
    retry_from_tests = tests_executed.to(code_generated)
    retry_from_quality = quality_approved.to(architecture_designed)

    def __init__(self, workflow_id: str):
        self.workflow_id = workflow_id
        super().__init__()

    def on_enter_state(self, event, state):
        logger.info(f"Workflow [{self.workflow_id}] state changed: '{state.id}' -> '{self.current_state.id}' (via '{event}')")


# 3. A KONTEXTUS OBJEKTUM
class WorkflowContext:
    """Egyetlen munkafolyamat teljes kontextusát tároló, adatorientált osztály."""
    def __init__(self, workflow_id: str, initial_requirements: Dict):
        self.workflow_id: str = workflow_id
        self.requirements: Dict = initial_requirements
        self.data: Dict[str, Any] = {} # Minden ügynök ide teszi az eredményét
        self.history: List[Dict] = []
        self.errors: List[Dict] = []
        self.retry_count: int = 0
        self.start_time: datetime = datetime.utcnow()

    def update(self, agent_name: str, response: Dict):
        """Frissíti a kontextust egy ügynök válaszával."""
        self.history.append({"agent": agent_name, "response": response})
        self.data[agent_name] = response.get("result", {})

    def add_error(self, agent_name: str, error_response: Dict):
        """Hiba naplózása a kontextusban."""
        self.errors.append({"agent": agent_name, "error": error_response})
        self.retry_count += 1
        logger.warning(f"Workflow [{self.workflow_id}] error from {agent_name}. Retry count: {self.retry_count}.")


# 4. A VÉGLEGES, REFAKTORÁLT ORKESZTRÁTOR
class GroupChatWorkflowManager:
    """
    A rendszer agya. `GroupChat`-et használ a dinamikus, FSM-vezérelt párbeszédhez.
    """
    def __init__(self, config_manager: ConfigManager):
        self.agent_orchestrator = AgentOrchestrator(config_manager)
        self.config = config_manager
        self.active_workflow: Optional[CodeGenerationFSM] = None
        self.active_context: Optional[WorkflowContext] = None
        logger.info("GroupChatWorkflowManager inicializálva.")

    def _custom_speaker_selection(self, last_speaker: autogen.Agent, groupchat: GroupChat) -> Union[autogen.Agent, str, None]:
        """
        A `GroupChat` agyaként működő metódus. Minden lépésben ez dönti el, ki beszéljen.
        """
        if len(groupchat.messages) <= 1:
            return self.agent_orchestrator.get_agent("SystemArchitect")
            
        try:
            last_message = json.loads(groupchat.messages[-1]["content"])
            if not self.agent_orchestrator.validate_agent_response(last_message):
                logger.error(f"Érvénytelen üzenetformátum: {last_message}")
                self.active_workflow.fail_from_any()
                return None
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Hiba az ügynök válaszának feldolgozásakor: {e}")
            self.active_workflow.fail_from_any()
            return None

        status = last_message.get("status")
        agent_name = last_message.get("agent")

        if status == "success":
            self.active_context.update(agent_name, last_message)
            next_agent_name = self._get_next_agent_on_success(agent_name)
        elif status == "error":
            self.active_context.add_error(agent_name, last_message)
            if self.active_context.retry_count > 3:
                self.active_workflow.fail_from_any()
                return None
            next_agent_name = self._get_agent_for_retry()
        else:
            return None 

        if next_agent_name:
            return self.agent_orchestrator.get_agent(next_agent_name)
        else:
            self.active_workflow.complete_workflow()
            return None 

    def _get_next_agent_on_success(self, last_agent_name: str) -> Optional[str]:
        """Meghatározza a következő ügynököt a láncban sikeres végrehajtás után."""
        chain = ["SystemArchitect", "PromptEngineer", "CodeGenerator", "CodeReviewer", "SecurityValidator", "TestRunner", "DocumentationGenerator", "QualityGate"]
        try:
            current_index = chain.index(last_agent_name)
            if current_index + 1 < len(chain):
                # A megfelelő FSM esemény meghívása
                event_name = self.active_workflow.events[current_index + 1].name
                self.active_workflow.trigger(event_name)
                return chain[current_index + 1]
            return None
        except ValueError:
            return None
    
    def _get_agent_for_retry(self) -> str:
        """Meghatározza, melyik ügynöknek kell újrapróbálkoznia hiba esetén."""
        state_map = {
            WorkflowState.CODE_REVIEWED.value: "PromptEngineer",
            WorkflowState.SECURITY_VALIDATED.value: "CodeGenerator",
            WorkflowState.TESTS_EXECUTED.value: "CodeGenerator",
            WorkflowState.QUALITY_APPROVED.value: "SystemArchitect"
        }
        retry_agent = state_map.get(self.active_workflow.current_state.value, "SystemArchitect")
        retry_event = f"retry_from_{self.active_workflow.current_state.id.lower()}"
        if self.active_workflow.has_transition(retry_event):
            self.active_workflow.trigger(retry_event)
        
        return retry_agent

    async def execute(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """A teljes munkafolyamat elindítása és végrehajtása."""
        workflow_id = str(uuid.uuid4())
        self.active_workflow = CodeGenerationFSM(workflow_id)
        self.active_context = WorkflowContext(workflow_id, requirements)
        
        groupchat = GroupChat(
            agents=list(self.agent_orchestrator.agents.values()),
            messages=[],
            max_round=50,
            speaker_selection_method=self._custom_speaker_selection
        )
        manager = GroupChatManager(
            groupchat=groupchat,
            llm_config=self.config.get_llm_config("standard")
        )
        
        initial_message = json.dumps({
            "action": "start_workflow",
            "requirements": requirements,
            "metadata": {"workflow_id": workflow_id}
        })
        
        executor = self.agent_orchestrator.get_agent("Executor")
        await executor.a_initiate_chat(manager, message=initial_message)
        
        final_state = self.active_workflow.current_state.value
        if final_state == WorkflowState.COMPLETED.value:
            return {"success": True, "final_state": final_state, "results": self.active_context.data}
        else:
            return {"success": False, "final_state": final_state, "errors": self.active_context.errors}