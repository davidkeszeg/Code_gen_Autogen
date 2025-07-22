from statemachine import StateMachine, State

class CodeGenerationWorkflow(StateMachine):
    initialized = State('Initialized', initial=True)
    requirements_analyzed = State('RequirementsAnalyzed')
    architecture_designed = State('ArchitectureDesigned')
    code_generated = State('CodeGenerated')
    security_validated = State('SecurityValidated')
    completed = State('Completed', final=True)
    failed = State('Failed', final=True)

    analyze_requirements = initialized.to(requirements_analyzed)
    design_architecture = requirements_analyzed.to(architecture_designed)
    generate_code = architecture_designed.to(code_generated)
    validate_security = code_generated.to(security_validated)
    complete_workflow = security_validated.to(completed)
    fail_workflow = (
        requirements_analyzed.to(failed) |
        architecture_designed.to(failed) |
        code_generated.to(failed) |
        security_validated.to(failed)
    )
    
    def __init__(self, workflow_id: str):
        super().__init__()
        self.workflow_id = workflow_id
        self.context = {}
        
    async def on_enter_state(self, state, event):
        print(f"Workflow {self.workflow_id} transitioned to {state.id}")
        # Persistence would be implemented here