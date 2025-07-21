"""
FSM-based workflow orchestration for code generation.
"""
import json
import asyncio
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from enum import Enum
import autogen
from autogen import GroupChat, GroupChatManager
from statemachine import StateMachine, State
import logging

from .agents import AgentOrchestrator

logger = logging.getLogger(__name__)


class WorkflowState(Enum):
    """Workflow states enumeration."""
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


class CodeGenerationWorkflow(StateMachine):
    """FSM for code generation workflow management."""
    
    # Define states
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
    
    # Define transitions
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
    
    # Error transitions
    fail_from_any = (
        initialized.to(failed) |
        requirements_analyzed.to(failed) |
        architecture_designed.to(failed) |
        prompt_engineered.to(failed) |
        code_generated.to(failed) |
        code_reviewed.to(failed) |
        security_validated.to(failed) |
        tests_executed.to(failed) |
        documentation_generated.to(failed) |
        quality_approved.to(failed)
    )
    
    # Retry transitions
    retry_from_review = code_reviewed.to(prompt_engineered)
    retry_from_security = security_validated.to(code_generated)
    retry_from_tests = tests_executed.to(code_generated)
    retry_from_quality = quality_approved.to(architecture_designed)


class WorkflowContext:
    """Context object for workflow execution."""
    
    def __init__(self):
        self.workflow_id = None
        self.requirements = {}
        self.architecture = {}
        self.prompts = {}
        self.generated_code = {}
        self.review_results = {}
        self.security_results = {}
        self.test_results = {}
        self.documentation = {}
        self.quality_results = {}
        self.errors = []
        self.retry_count = 0
        self.start_time = datetime.utcnow()
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary."""
        return {
            "workflow_id": self.workflow_id,
            "requirements": self.requirements,
            "architecture": self.architecture,
            "prompts": self.prompts,
            "generated_code": self.generated_code,
            "review_results": self.review_results,
            "security_results": self.security_results,
            "test_results": self.test_results,
            "documentation": self.documentation,
            "quality_results": self.quality_results,
            "errors": self.errors,
            "retry_count": self.retry_count,
            "start_time": self.start_time.isoformat()
        }


class FSMWorkflowOrchestrator:
    """Main workflow orchestrator using FSM and AutoGen."""
    
    def __init__(self, agent_orchestrator: AgentOrchestrator, config_manager):
        self.agent_orchestrator = agent_orchestrator
        self.config = config_manager
        self.active_workflows = {}
        
    def custom_speaker_selection(self, last_speaker: autogen.Agent, groupchat: GroupChat) -> Union[autogen.Agent, str, None]:
        """Custom speaker selection based on FSM state and agent responses."""
        
        messages = groupchat.messages
        if len(messages) == 0:
            return self.agent_orchestrator.get_agent("SystemArchitect")
        
        # Get workflow context from the active workflows
        workflow_id = self._extract_workflow_id(messages)
        if workflow_id not in self.active_workflows:
            logger.error(f"Workflow {workflow_id} not found")
            return None
            
        workflow, context = self.active_workflows[workflow_id]
        
        # Parse last message
        if last_speaker and messages:
            try:
                last_message = json.loads(messages[-1]["content"])
                next_agent_name = last_message.get("next_agent")
                status = last_message.get("status")
                
                # Handle errors
                if status == "error":
                    context.errors.append(last_message)
                    context.retry_count += 1
                    
                    if context.retry_count > 3:
                        workflow.fail_from_any()
                        return None
                    
                    # Retry logic based on current state
                    return self._get_retry_agent(workflow.current_state.value)
                
                # Progress workflow based on successful response
                if status == "success":
                    self._progress_workflow(workflow, last_speaker.name)
                    
                # Return next agent
                if next_agent_name:
                    return self.agent_orchestrator.get_agent(next_agent_name)
                else:
                    return self._get_next_agent_by_state(workflow.current_state.value)
                    
            except (json.JSONDecodeError, KeyError) as e:
                logger.error(f"Error parsing agent response: {e}")
                return None
                
        return None
    
    def _extract_workflow_id(self, messages: List[Dict]) -> Optional[str]:
        """Extract workflow ID from messages."""
        for message in messages:
            try:
                content = json.loads(message.get("content", "{}"))
                if "workflow_id" in content.get("metadata", {}):
                    return content["metadata"]["workflow_id"]
            except:
                continue
        return None
    
    def _progress_workflow(self, workflow: CodeGenerationWorkflow, agent_name: str):
        """Progress workflow based on agent completion."""
        
        transitions = {
            "SystemArchitect": workflow.analyze_requirements,
            "PromptEngineer": workflow.engineer_prompt,
            "CodeGenerator": workflow.generate_code,
            "CodeReviewer": workflow.review_code,
            "SecurityValidator": workflow.validate_security,
            "TestRunner": workflow.execute_tests,
            "DocumentationGenerator": workflow.generate_documentation,
            "QualityGate": workflow.approve_quality
        }
        
        if agent_name in transitions:
            try:
                transitions[agent_name]()
                logger.info(f"Workflow progressed from {agent_name}")
            except Exception as e:
                logger.error(f"Failed to progress workflow: {e}")
    
    def _get_next_agent_by_state(self, state: str) -> Optional[autogen.Agent]:
        """Get next agent based on current workflow state."""
        
        state_to_agent = {
            WorkflowState.INITIALIZED.value: "SystemArchitect",
            WorkflowState.REQUIREMENTS_ANALYZED.value: "SystemArchitect",
            WorkflowState.ARCHITECTURE_DESIGNED.value: "PromptEngineer",
            WorkflowState.PROMPT_ENGINEERED.value: "CodeGenerator",
            WorkflowState.CODE_GENERATED.value: "CodeReviewer",
            WorkflowState.CODE_REVIEWED.value: "SecurityValidator",
            WorkflowState.SECURITY_VALIDATED.value: "TestRunner",
            WorkflowState.TESTS_EXECUTED.value: "DocumentationGenerator",
            WorkflowState.DOCUMENTATION_GENERATED.value: "QualityGate",
            WorkflowState.QUALITY_APPROVED.value: "Executor"
        }
        
        agent_name = state_to_agent.get(state)
        if agent_name:
            return self.agent_orchestrator.get_agent(agent_name)
        return None
    
    def _get_retry_agent(self, state: str) -> Optional[autogen.Agent]:
        """Get agent for retry based on current state."""
        
        retry_mapping = {
            WorkflowState.CODE_REVIEWED.value: "PromptEngineer",
            WorkflowState.SECURITY_VALIDATED.value: "CodeGenerator",
            WorkflowState.TESTS_EXECUTED.value: "CodeGenerator",
            WorkflowState.QUALITY_APPROVED.value: "SystemArchitect"
        }
        
        agent_name = retry_mapping.get(state, "SystemArchitect")
        return self.agent_orchestrator.get_agent(agent_name)
    
    async def execute_workflow(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Execute complete code generation workflow."""
        
        import uuid
        workflow_id = str(uuid.uuid4())
        
        # Initialize workflow and context
        workflow = CodeGenerationWorkflow()
        context = WorkflowContext()
        context.workflow_id = workflow_id
        context.requirements = requirements
        
        self.active_workflows[workflow_id] = (workflow, context)
        
        try:
            # Create group chat with all agents
            agents = list(self.agent_orchestrator.agents.values())
            
            groupchat = GroupChat(
                agents=agents,
                messages=[],
                max_round=50,
                speaker_selection_method=self.custom_speaker_selection,
                allow_repeat_speaker=False
            )
            
            # Create manager with coordinator config
            manager = GroupChatManager(
                groupchat=groupchat,
                llm_config=self.config.get_llm_config("standard")
            )
            
            # Prepare initial message
            initial_message = json.dumps({
                "action": "start_workflow",
                "requirements": requirements,
                "metadata": {
                    "workflow_id": workflow_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            })
            
            # Start chat
            admin = self.agent_orchestrator.get_agent("Executor")
            result = await admin.a_initiate_chat(
                manager,
                message=initial_message,
                clear_history=True
            )
            
            # Check final state
            if workflow.current_state == workflow.completed:
                return {
                    "success": True,
                    "workflow_id": workflow_id,
                    "results": context.to_dict(),
                    "duration": (datetime.utcnow() - context.start_time).total_seconds()
                }
            else:
                return {
                    "success": False,
                    "workflow_id": workflow_id,
                    "error": "Workflow did not complete successfully",
                    "final_state": workflow.current_state.value,
                    "errors": context.errors
                }
                
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            workflow.fail_from_any()
            
            return {
                "success": False,
                "workflow_id": workflow_id,
                "error": str(e),
                "final_state": workflow.current_state.value
            }
            
        finally:
            # Cleanup
            if workflow_id in self.active_workflows:
                del self.active_workflows[workflow_id]