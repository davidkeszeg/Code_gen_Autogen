"""
Intelligent cost optimization for LLM usage.
"""
import json
import hashlib
import asyncio
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import numpy as np
import redis.asyncio as redis
import logging

logger = logging.getLogger(__name__)


@dataclass
class CostMetrics:
    """Cost tracking metrics."""
    model: str
    tokens_used: int
    cost: float
    timestamp: datetime
    workflow_id: str
    complexity_score: float


@dataclass
class ComplexityScore:
    """Request complexity analysis."""
    score: float  # 0.0 to 1.0
    factors: Dict[str, float]
    recommended_tier: str


class IntelligentCostOptimizer:
    """Advanced cost optimization with caching and intelligent routing."""
    
    def __init__(self, config_manager, redis_url: str):
        self.config = config_manager
        self.redis_client = None
        self.redis_url = redis_url
        self.usage_history = []
        self.model_performance_cache = {}
        
    async def initialize(self):
        """Initialize Redis connection."""
        self.redis_client = await redis.from_url(self.redis_url)
        logger.info("Cost optimizer initialized")
        
    async def analyze_request_complexity(self, request: Dict[str, Any]) -> ComplexityScore:
        """Analyze request complexity for optimal model routing."""
        
        factors = {
            "token_count": 0.0,
            "code_complexity": 0.0,
            "domain_complexity": 0.0,
            "security_requirements": 0.0,
            "performance_requirements": 0.0
        }
        
        # Token count analysis
        content = json.dumps(request)
        token_estimate = len(content.split()) * 1.3  # Rough token estimate
        factors["token_count"] = min(token_estimate / 1000, 1.0)
        
        # Code complexity indicators
        code_indicators = [
            "algorithm", "optimization", "parallel", "distributed",
            "machine learning", "neural network", "cryptography"
        ]
        code_complexity = sum(1 for indicator in code_indicators if indicator in content.lower())
        factors["code_complexity"] = min(code_complexity / 3, 1.0)
        
        # Domain complexity
        domain_indicators = [
            "financial", "trading", "medical", "legal", "compliance",
            "real-time", "high-frequency", "mission-critical"
        ]
        domain_complexity = sum(1 for indicator in domain_indicators if indicator in content.lower())
        factors["domain_complexity"] = min(domain_complexity / 2, 1.0)
        
        # Security requirements
        security_indicators = [
            "security", "authentication", "encryption", "authorization",
            "vulnerability", "penetration", "compliance"
        ]
        security_complexity = sum(1 for indicator in security_indicators if indicator in content.lower())
        factors["security_requirements"] = min(security_complexity / 2, 1.0)
        
        # Performance requirements
        performance_indicators = [
            "performance", "optimization", "latency", "throughput",
            "scalability", "concurrent", "real-time"
        ]
        performance_complexity = sum(1 for indicator in performance_indicators if indicator in content.lower())
        factors["performance_requirements"] = min(performance_complexity / 2, 1.0)
        
        # Calculate weighted complexity score
        weights = {
            "token_count": 0.15,
            "code_complexity": 0.25,
            "domain_complexity": 0.25,
            "security_requirements": 0.20,
            "performance_requirements": 0.15
        }
        
        complexity_score = sum(factors[k] * weights[k] for k in factors)
        
        # Determine recommended tier
        if complexity_score < 0.3:
            recommended_tier = "local"
        elif complexity_score < 0.5:
            recommended_tier = "economic"
        elif complexity_score < 0.7:
            recommended_tier = "standard"
        else:
            recommended_tier = "high_performance"
            
        return ComplexityScore(
            score=complexity_score,
            factors=factors,
            recommended_tier=recommended_tier
        )
    
    async def get_cached_response(self, request_hash: str) -> Optional[Dict[str, Any]]:
        """Check for cached response with semantic similarity."""
        
        if not self.redis_client:
            return None
            
        try:
            # Try exact match first
            cached = await self.redis_client.get(f"cache:exact:{request_hash}")
            if cached:
                logger.info("Cache hit: exact match")
                return json.loads(cached)
            
            # Try semantic similarity (simplified version)
            pattern = f"cache:semantic:{request_hash[:8]}*"
            similar_keys = []
            async for key in self.redis_client.scan_iter(match=pattern):
                similar_keys.append(key)
                
            if similar_keys:
                # Get the most recent similar response
                cached = await self.redis_client.get(similar_keys[0])
                if cached:
                    logger.info("Cache hit: semantic match")
                    return json.loads(cached)
                    
        except Exception as e:
            logger.error(f"Cache lookup error: {e}")
            
        return None
    
    async def cache_response(self, request_hash: str, response: Dict[str, Any], ttl: int = 3600):
        """Cache response for future use."""
        
        if not self.redis_client:
            return
            
        try:
            # Cache exact match
            await self.redis_client.setex(
                f"cache:exact:{request_hash}",
                ttl,
                json.dumps(response)
            )
            
            # Cache for semantic matching
            await self.redis_client.setex(
                f"cache:semantic:{request_hash[:8]}:{request_hash}",
                ttl,
                json.dumps(response)
            )
            
        except Exception as e:
            logger.error(f"Cache storage error: {e}")
    
    def calculate_request_hash(self, request: Dict[str, Any]) -> str:
        """Calculate hash for request caching."""
        
        # Normalize request for consistent hashing
        normalized = json.dumps(request, sort_keys=True)
        return hashlib.sha256(normalized.encode()).hexdigest()
    
    async def route_request(self, request: Dict[str, Any], agent_type: str) -> Tuple[str, Dict[str, Any]]:
        """Route request to optimal model based on complexity and cost."""
        
        # Check cache first
        request_hash = self.calculate_request_hash(request)
        cached_response = await self.get_cached_response(request_hash)
        
        if cached_response:
            return "cached", cached_response
        
        # Analyze complexity
        complexity = await self.analyze_request_complexity(request)
        
        # Override for specific agent types
        tier_overrides = {
            "SystemArchitect": "high_performance",
            "SecurityValidator": "high_performance",
            "QualityGate": "high_performance"
        }
        
        if agent_type in tier_overrides:
            selected_tier = tier_overrides[agent_type]
        else:
            selected_tier = complexity.recommended_tier
            
        # Check budget constraints
        if await self._check_budget_exceeded():
            # Downgrade to more economic tier if budget exceeded
            tier_downgrades = {
                "high_performance": "standard",
                "standard": "economic",
                "economic": "local",
                "local": "local"
            }
            selected_tier = tier_downgrades.get(selected_tier, "local")
            logger.warning(f"Budget exceeded, downgrading to {selected_tier}")
        
        # Get model configuration
        model_config = self.config.get_llm_config(selected_tier)
        
        # Track routing decision
        await self._track_routing_decision(
            request_hash=request_hash,
            agent_type=agent_type,
            selected_tier=selected_tier,
            complexity_score=complexity.score
        )
        
        return selected_tier, model_config
    
    async def track_usage(self, metrics: CostMetrics):
        """Track usage metrics for cost optimization."""
        
        self.usage_history.append(metrics)
        
        # Store in Redis for persistence
        if self.redis_client:
            await self.redis_client.lpush(
                f"usage:{metrics.workflow_id}",
                json.dumps({
                    "model": metrics.model,
                    "tokens": metrics.tokens_used,
                    "cost": metrics.cost,
                    "timestamp": metrics.timestamp.isoformat(),
                    "complexity": metrics.complexity_score
                })
            )
            
            # Update daily cost counter
            daily_key = f"daily_cost:{datetime.utcnow().strftime('%Y-%m-%d')}"
            await self.redis_client.incrbyfloat(daily_key, metrics.cost)
    
    async def get_cost_report(self, time_period: timedelta) -> Dict[str, Any]:
        """Generate cost report for specified time period."""
        
        end_time = datetime.utcnow()
        start_time = end_time - time_period
        
        # Filter usage history
        period_usage = [
            m for m in self.usage_history
            if start_time <= m.timestamp <= end_time
        ]
        
        if not period_usage:
            return {
                "total_cost": 0.0,
                "total_tokens": 0,
                "model_breakdown": {},
                "average_complexity": 0.0
            }
        
        # Calculate metrics
        total_cost = sum(m.cost for m in period_usage)
        total_tokens = sum(m.tokens_used for m in period_usage)
        
        # Model breakdown
        model_costs = {}
        for metric in period_usage:
            if metric.model not in model_costs:
                model_costs[metric.model] = {"cost": 0.0, "tokens": 0, "requests": 0}
            model_costs[metric.model]["cost"] += metric.cost
            model_costs[metric.model]["tokens"] += metric.tokens_used
            model_costs[metric.model]["requests"] += 1
        
        # Average complexity
        avg_complexity = np.mean([m.complexity_score for m in period_usage])
        
        return {
            "total_cost": total_cost,
            "total_tokens": total_tokens,
            "total_requests": len(period_usage),
            "model_breakdown": model_costs,
            "average_complexity": avg_complexity,
            "period_start": start_time.isoformat(),
            "period_end": end_time.isoformat()
        }
    
    async def _check_budget_exceeded(self) -> bool:
        """Check if monthly budget is exceeded."""
        
        if not self.redis_client:
            return False
            
        try:
            # Get current month's total cost
            current_month = datetime.utcnow().strftime('%Y-%m')
            monthly_cost = 0.0
            
            # Sum daily costs for current month
            for day in range(1, 32):
                daily_key = f"daily_cost:{current_month}-{day:02d}"
                cost = await self.redis_client.get(daily_key)
                if cost:
                    monthly_cost += float(cost)
            
            # Check against budget
            budget = self.config.models.monthly_budget_usd
            threshold = budget * self.config.models.cost_alert_threshold
            
            return monthly_cost >= threshold
            
        except Exception as e:
            logger.error(f"Budget check error: {e}")
            return False
    
    async def _track_routing_decision(self, request_hash: str, agent_type: str, 
                                    selected_tier: str, complexity_score: float):
        """Track routing decisions for optimization."""
        
        if self.redis_client:
            await self.redis_client.lpush(
                "routing_decisions",
                json.dumps({
                    "request_hash": request_hash[:8],
                    "agent_type": agent_type,
                    "selected_tier": selected_tier,
                    "complexity_score": complexity_score,
                    "timestamp": datetime.utcnow().isoformat()
                })
            )
    
    async def optimize_routing_strategy(self) -> Dict[str, Any]:
        """Analyze routing decisions and optimize strategy."""
        
        if not self.redis_client:
            return {}
            
        # Get recent routing decisions
        decisions = []
        raw_decisions = await self.redis_client.lrange("routing_decisions", 0, 1000)
        
        for raw in raw_decisions:
            decisions.append(json.loads(raw))
        
        if not decisions:
            return {}
        
        # Analyze patterns
        tier_usage = {}
        agent_patterns = {}
        
        for decision in decisions:
            tier = decision["selected_tier"]
            agent = decision["agent_type"]
            
            if tier not in tier_usage:
                tier_usage[tier] = 0
            tier_usage[tier] += 1
            
            if agent not in agent_patterns:
                agent_patterns[agent] = {"tiers": {}, "avg_complexity": []}
            
            if tier not in agent_patterns[agent]["tiers"]:
                agent_patterns[agent]["tiers"][tier] = 0
            
            agent_patterns[agent]["tiers"][tier] += 1
            agent_patterns[agent]["avg_complexity"].append(decision["complexity_score"])
        
        # Calculate average complexities
        for agent in agent_patterns:
            if agent_patterns[agent]["avg_complexity"]:
                agent_patterns[agent]["avg_complexity"] = np.mean(
                    agent_patterns[agent]["avg_complexity"]
                )
            else:
                agent_patterns[agent]["avg_complexity"] = 0.0
        
        return {
            "tier_usage": tier_usage,
            "agent_patterns": agent_patterns,
            "total_decisions": len(decisions),
            "optimization_suggestions": self._generate_optimization_suggestions(
                tier_usage, agent_patterns
            )
        }
    
    def _generate_optimization_suggestions(self, tier_usage: Dict[str, int], 
                                         agent_patterns: Dict[str, Any]) -> List[str]:
        """Generate optimization suggestions based on usage patterns."""
        
        suggestions = []
        
        # Check if local models are underutilized
        total_usage = sum(tier_usage.values())
        if total_usage > 0:
            local_percentage = tier_usage.get("local", 0) / total_usage
            
            if local_percentage < 0.5:
                suggestions.append(
                    "Consider routing more simple requests to local models for cost savings"
                )
        
        # Check for agents that could use lower tiers
        for agent, patterns in agent_patterns.items():
            if patterns["avg_complexity"] < 0.5 and agent not in ["SystemArchitect", "SecurityValidator", "QualityGate"]:
                suggestions.append(
                    f"Agent {agent} has low average complexity ({patterns['avg_complexity']:.2f}), "
                    f"consider using more economic models"
                )
        
        return suggestions