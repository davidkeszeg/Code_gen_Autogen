"""
Main entry point for AutoGen Enterprise Code Generator.
"""
import asyncio
import json
import logging
import sys
from typing import Dict, Any, Optional
from datetime import datetime
import uvicorn
from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import structlog

# Internal imports
from core.config import config_manager
from core.agents import AgentOrchestrator
from core.workflow import FSMWorkflowOrchestrator
from cost.optimizer import IntelligentCostOptimizer
from security.executor import SecureCodeExecutor
from utils.monitoring import MetricsCollector, HealthChecker
from utils.logging import setup_logging

# Setup structured logging
setup_logging()
logger = structlog.get_logger()

# FastAPI app
app = FastAPI(
    title="AutoGen Enterprise Code Generator",
    version="1.0.0",
    description="Professional code generation system with multi-agent architecture"
)

# Security
security = HTTPBearer()

# Global instances
orchestrator: Optional[AgentOrchestrator] = None
workflow_orchestrator: Optional[FSMWorkflowOrchestrator] = None
cost_optimizer: Optional[IntelligentCostOptimizer] = None
code_executor: Optional[SecureCodeExecutor] = None
metrics_collector: Optional[MetricsCollector] = None
health_checker: Optional[HealthChecker] = None


# Request/Response models
class CodeGenerationRequest(BaseModel):
    """Code generation request model."""
    project_name: str
    description: str
    requirements: Dict[str, Any]
    constraints: Optional[Dict[str, Any]] = {}
    technology_stack: Optional[list] = []
    complexity_hint: Optional[str] = "auto"  # auto, simple, moderate, complex


class CodeGenerationResponse(BaseModel):
    """Code generation response model."""
    success: bool
    workflow_id: str
    generated_files: Optional[Dict[str, str]] = None
    documentation: Optional[Dict[str, str]] = None
    test_results: Optional[Dict[str, Any]] = None
    metrics: Optional[Dict[str, Any]] = None
    errors: Optional[list] = None


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: str
    components: Dict[str, Any]


class CostReportRequest(BaseModel):
    """Cost report request model."""
    period_days: int = 30
    group_by: str = "model"  # model, agent, workflow


# Authentication
async def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> str:
    """Verify JWT token."""
    # TODO: Implement proper JWT validation
    # For now, just check if token exists
    if not credentials.credentials:
        raise HTTPException(status_code=403, detail="Invalid authentication credentials")
    return credentials.credentials


# API Endpoints
@app.post("/api/v1/generate", response_model=CodeGenerationResponse)
async def generate_code(
    request: CodeGenerationRequest,
    token: str = Depends(verify_token)
) -> CodeGenerationResponse:
    """Generate code based on requirements."""
    
    logger.info("code_generation_request", 
               project=request.project_name,
               complexity=request.complexity_hint)
    
    try:
        # Prepare requirements
        requirements = {
            "project_name": request.project_name,
            "description": request.description,
            "requirements": request.requirements,
            "constraints": request.constraints,
            "technology_stack": request.technology_stack,
            "requested_by": token  # Track who requested
        }
        
        # Execute workflow
        result = await workflow_orchestrator.execute_workflow(requirements)
        
        if result["success"]:
            # Track metrics
            await metrics_collector.record_workflow_completion(
                workflow_id=result["workflow_id"],
                success=True,
                duration=result.get("duration", 0),
                cost=result.get("total_cost", 0)
            )
            
            # Extract results
            context = result["results"]
            
            return CodeGenerationResponse(
                success=True,
                workflow_id=result["workflow_id"],
                generated_files=context.get("generated_code"),
                documentation=context.get("documentation"),
                test_results=context.get("test_results"),
                metrics={
                    "duration": result.get("duration"),
                    "total_cost": result.get("total_cost"),
                    "agents_used": len(context.get("architecture", {}))
                }
            )
        else:
            return CodeGenerationResponse(
                success=False,
                workflow_id=result["workflow_id"],
                errors=result.get("errors", ["Unknown error occurred"])
            )
            
    except Exception as e:
        logger.error("code_generation_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    
    health_status = await health_checker.check_system_health()
    
    return HealthResponse(
        status="healthy" if health_status["healthy"] else "unhealthy",
        timestamp=datetime.utcnow().isoformat(),
        components=health_status["components"]
    )


@app.post("/api/v1/cost-report")
async def get_cost_report(
    request: CostReportRequest,
    token: str = Depends(verify_token)
) -> Dict[str, Any]:
    """Get cost report for specified period."""
    
    from datetime import timedelta
    
    report = await cost_optimizer.get_cost_report(
        time_period=timedelta(days=request.period_days)
    )
    
    # Add optimization suggestions
    optimization = await cost_optimizer.optimize_routing_strategy()
    report["optimization_suggestions"] = optimization.get("optimization_suggestions", [])
    
    return report


@app.get("/api/v1/metrics")
async def get_metrics(token: str = Depends(verify_token)) -> Dict[str, Any]:
    """Get system metrics."""
    
    return await metrics_collector.get_current_metrics()


# Startup and shutdown
@app.on_event("startup")
async def startup_event():
    """Initialize all components on startup."""
    
    global orchestrator, workflow_orchestrator, cost_optimizer
    global code_executor, metrics_collector, health_checker
    
    logger.info("Starting AutoGen Enterprise Code Generator")
    
    try:
        # Validate configuration
        if not config_manager.validate_configuration():
            raise ValueError("Configuration validation failed")
            
        # Initialize cost optimizer
        cost_optimizer = IntelligentCostOptimizer(
            config_manager, 
            config_manager.security.redis_url
        )
        await cost_optimizer.initialize()
        
        # Initialize agent orchestrator
        orchestrator = AgentOrchestrator(config_manager)
        
        # Initialize workflow orchestrator
        workflow_orchestrator = FSMWorkflowOrchestrator(
            orchestrator,
            config_manager
        )
        
        # Initialize code executor
        code_executor = SecureCodeExecutor(config_manager)
        await code_executor.initialize()
        
        # Initialize monitoring
        metrics_collector = MetricsCollector()
        health_checker = HealthChecker(
            orchestrator=orchestrator,
            cost_optimizer=cost_optimizer,
            code_executor=code_executor
        )
        
        logger.info("All components initialized successfully")
        
    except Exception as e:
        logger.error("Failed to initialize components", error=str(e))
        sys.exit(1)


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    
    logger.info("Shutting down AutoGen Enterprise Code Generator")
    
    # Cleanup resources
    if cost_optimizer and cost_optimizer.redis_client:
        await cost_optimizer.redis_client.close()


# CLI interface
async def cli_generate(requirements_file: str):
    """Generate code from CLI."""
    
    # Load requirements
    with open(requirements_file, 'r') as f:
        requirements = json.load(f)
        
    # Create request
    request = CodeGenerationRequest(**requirements)
    
    # Initialize components
    await startup_event()
    
    try:
        # Generate code
        response = await generate_code(request, token="cli-user")
        
        # Save results
        if response.success:
            print(f"✅ Code generation successful!")
            print(f"Workflow ID: {response.workflow_id}")
            
            if response.generated_files:
                for filename, content in response.generated_files.items():
                    with open(f"generated/{filename}", 'w') as f:
                        f.write(content)
                    print(f"📄 Generated: {filename}")
                    
        else:
            print(f"❌ Code generation failed:")
            for error in response.errors:
                print(f"  - {error}")
                
    finally:
        await shutdown_event()


def main():
    """Main entry point."""
    
    import argparse
    
    parser = argparse.ArgumentParser(
        description="AutoGen Enterprise Code Generator"
    )
    parser.add_argument(
        "--mode",
        choices=["server", "cli"],
        default="server",
        help="Run mode: server or CLI"
    )
    parser.add_argument(
        "--requirements",
        type=str,
        help="Requirements file for CLI mode"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Server host"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Server port"
    )
    
    args = parser.parse_args()
    
    if args.mode == "server":
        # Run as API server
        uvicorn.run(
            app,
            host=args.host,
            port=args.port,
            log_config={
                "version": 1,
                "disable_existing_loggers": False,
                "formatters": {
                    "default": {
                        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                    },
                },
                "handlers": {
                    "default": {
                        "formatter": "default",
                        "class": "logging.StreamHandler",
                        "stream": "ext://sys.stdout",
                    },
                },
                "root": {
                    "level": "INFO",
                    "handlers": ["default"],
                },
            }
        )
    else:
        # Run in CLI mode
        if not args.requirements:
            print("Error: --requirements file required for CLI mode")
            sys.exit(1)
            
        asyncio.run(cli_generate(args.requirements))


if __name__ == "__main__":
    main()