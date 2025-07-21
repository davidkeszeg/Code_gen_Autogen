"""
Monitoring and observability utilities.
"""
import time
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
from prometheus_client import Counter, Histogram, Gauge, Info
import logging

logger = logging.getLogger(__name__)

# Prometheus metrics
workflow_counter = Counter(
    'autogen_workflows_total',
    'Total number of workflows executed',
    ['status', 'project_type']
)

workflow_duration = Histogram(
    'autogen_workflow_duration_seconds',
    'Workflow execution duration',
    buckets=[1, 5, 10, 30, 60, 120, 300, 600]
)

agent_response_time = Histogram(
    'autogen_agent_response_seconds',
    'Agent response time',
    ['agent_name', 'action'],
    buckets=[0.1, 0.5, 1, 2, 5, 10, 30]
)

api_request_counter = Counter(
    'autogen_api_requests_total',
    'Total API requests',
    ['endpoint', 'method', 'status_code']
)

api_request_duration = Histogram(
    'autogen_api_request_duration_seconds',
    'API request duration',
    ['endpoint', 'method'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1, 2, 5]
)

cost_counter = Counter(
    'autogen_llm_cost_dollars',
    'Total LLM API costs',
    ['model', 'tier', 'agent']
)

active_workflows = Gauge(
    'autogen_active_workflows',
    'Number of currently active workflows'
)

system_info = Info(
    'autogen_system',
    'System information'
)


class MetricsCollector:
    """Centralized metrics collection and reporting."""
    
    def __init__(self):
        self.start_time = time.time()
        self.workflow_history = []
        self.agent_metrics = {}
        
        # Set system info
        system_info.info({
            'version': '1.0.0',
            'start_time': datetime.utcnow().isoformat()
        })
        
    async def record_workflow_start(self, workflow_id: str, project_type: str = "unknown"):
        """Record workflow start."""
        active_workflows.inc()
        
        self.workflow_history.append({
            "workflow_id": workflow_id,
            "project_type": project_type,
            "start_time": time.time(),
            "status": "running"
        })
        
    async def record_workflow_completion(self, workflow_id: str, success: bool, 
                                       duration: float, cost: float):
        """Record workflow completion."""
        active_workflows.dec()
        
        status = "success" if success else "failure"
        
        # Find workflow in history
        workflow = next((w for w in self.workflow_history if w["workflow_id"] == workflow_id), None)
        project_type = workflow["project_type"] if workflow else "unknown"
        
        # Update metrics
        workflow_counter.labels(status=status, project_type=project_type).inc()
        workflow_duration.observe(duration)
        
        if workflow:
            workflow["status"] = status
            workflow["duration"] = duration
            workflow["cost"] = cost
            workflow["end_time"] = time.time()
            
    async def record_agent_interaction(self, agent_name: str, action: str, 
                                     response_time: float, tokens: int, cost: float):
        """Record agent interaction metrics."""
        
        agent_response_time.labels(agent_name=agent_name, action=action).observe(response_time)
        
        # Track per-agent metrics
        if agent_name not in self.agent_metrics:
            self.agent_metrics[agent_name] = {
                "total_calls": 0,
                "total_tokens": 0,
                "total_cost": 0.0,
                "total_time": 0.0,
                "actions": {}
            }
            
        self.agent_metrics[agent_name]["total_calls"] += 1
        self.agent_metrics[agent_name]["total_tokens"] += tokens
        self.agent_metrics[agent_name]["total_cost"] += cost
        self.agent_metrics[agent_name]["total_time"] += response_time
        
        if action not in self.agent_metrics[agent_name]["actions"]:
            self.agent_metrics[agent_name]["actions"][action] = 0
        self.agent_metrics[agent_name]["actions"][action] += 1
        
    async def record_api_request(self, endpoint: str, method: str, 
                               status_code: int, duration: float):
        """Record API request metrics."""
        
        api_request_counter.labels(
            endpoint=endpoint,
            method=method,
            status_code=str(status_code)
        ).inc()
        
        api_request_duration.labels(
            endpoint=endpoint,
            method=method
        ).observe(duration)
        
    async def record_llm_cost(self, model: str, tier: str, agent: str, cost: float):
        """Record LLM API costs."""
        
        cost_counter.labels(
            model=model,
            tier=tier,
            agent=agent
        ).inc(cost)
        
    async def get_current_metrics(self) -> Dict[str, Any]:
        """Get current system metrics."""
        
        uptime = time.time() - self.start_time
        
        # Calculate workflow statistics
        total_workflows = len(self.workflow_history)
        successful_workflows = sum(1 for w in self.workflow_history if w.get("status") == "success")
        failed_workflows = sum(1 for w in self.workflow_history if w.get("status") == "failure")
        
        success_rate = (successful_workflows / total_workflows * 100) if total_workflows > 0 else 0
        
        # Calculate average metrics
        completed_workflows = [w for w in self.workflow_history if "duration" in w]
        avg_duration = sum(w["duration"] for w in completed_workflows) / len(completed_workflows) if completed_workflows else 0
        avg_cost = sum(w["cost"] for w in completed_workflows) / len(completed_workflows) if completed_workflows else 0
        
        return {
            "system": {
                "uptime_seconds": uptime,
                "uptime_hours": uptime / 3600,
                "active_workflows": active_workflows._value.get(),
                "version": "1.0.0"
            },
            "workflows": {
                "total": total_workflows,
                "successful": successful_workflows,
                "failed": failed_workflows,
                "success_rate": success_rate,
                "average_duration": avg_duration,
                "average_cost": avg_cost
            },
            "agents": self.agent_metrics,
            "recent_workflows": self.workflow_history[-10:]  # Last 10 workflows
        }


class HealthChecker:
    """System health checking."""
    
    def __init__(self, orchestrator, cost_optimizer, code_executor):
        self.orchestrator = orchestrator
        self.cost_optimizer = cost_optimizer
        self.code_executor = code_executor
        self.last_check = None
        self.health_history = []
        
    async def check_system_health(self) -> Dict[str, Any]:
        """Perform comprehensive health check."""
        
        health_status = {
            "healthy": True,
            "timestamp": datetime.utcnow().isoformat(),
            "components": {}
        }
        
        # Check agent health
        agent_health = await self._check_agents()
        health_status["components"]["agents"] = agent_health
        if not agent_health["healthy"]:
            health_status["healthy"] = False
            
        # Check Redis connection
        redis_health = await self._check_redis()
        health_status["components"]["redis"] = redis_health
        if not redis_health["healthy"]:
            health_status["healthy"] = False
            
        # Check Docker
        docker_health = await self._check_docker()
        health_status["components"]["docker"] = docker_health
        if not docker_health["healthy"]:
            health_status["healthy"] = False
            
        # Check API keys
        api_health = await self._check_api_keys()
        health_status["components"]["api_keys"] = api_health
        if not api_health["healthy"]:
            health_status["healthy"] = False
            
        # Store in history
        self.health_history.append(health_status)
        if len(self.health_history) > 100:
            self.health_history.pop(0)
            
        self.last_check = datetime.utcnow()
        
        return health_status
        
    async def _check_agents(self) -> Dict[str, Any]:
        """Check agent availability."""
        
        try:
            agent_status = {}
            all_healthy = True
            
            for agent_name, agent in self.orchestrator.agents.items():
                try:
                    # Simple test message
                    test_message = [{
                        "content": json.dumps({"action": "health_check"}),
                        "role": "user"
                    }]
                    
                    start_time = time.time()
                    response = agent.generate_reply(test_message)
                    response_time = time.time() - start_time
                    
                    agent_status[agent_name] = {
                        "healthy": True,
                        "response_time": response_time
                    }
                    
                except Exception as e:
                    agent_status[agent_name] = {
                        "healthy": False,
                        "error": str(e)
                    }
                    all_healthy = False
                    
            return {
                "healthy": all_healthy,
                "agents": agent_status
            }
            
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e)
            }
            
    async def _check_redis(self) -> Dict[str, Any]:
        """Check Redis connectivity."""
        
        try:
            if self.cost_optimizer.redis_client:
                await self.cost_optimizer.redis_client.ping()
                return {"healthy": True}
            else:
                return {"healthy": False, "error": "Redis client not initialized"}
                
        except Exception as e:
            return {"healthy": False, "error": str(e)}
            
    async def _check_docker(self) -> Dict[str, Any]:
        """Check Docker availability."""
        
        try:
            if self.code_executor.docker_client:
                self.code_executor.docker_client.ping()
                return {"healthy": True}
            else:
                return {"healthy": False, "error": "Docker client not initialized"}
                
        except Exception as e:
            return {"healthy": False, "error": str(e)}
            
    async def _check_api_keys(self) -> Dict[str, Any]:
        """Check API key configuration."""
        
        try:
            openai_configured = bool(self.orchestrator.config.security.openai_api_key)
            anthropic_configured = bool(self.orchestrator.config.security.anthropic_api_key)
            
            return {
                "healthy": openai_configured or anthropic_configured,
                "openai": openai_configured,
                "anthropic": anthropic_configured
            }
            
        except Exception as e:
            return {"healthy": False, "error": str(e)}