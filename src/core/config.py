"""
Enterprise configuration management with security and validation.
"""
import os
from typing import Dict, Any, Optional, List
from pydantic_settings import BaseSettings
from pydantic import validator, Field
from cryptography.fernet import Fernet
import json
import logging

logger = logging.getLogger(__name__)


class SecurityConfig(BaseSettings):
    """Security configuration with encrypted API keys."""
    
    # API Keys (will be encrypted)
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    anthropic_api_key: str = Field(..., env="ANTHROPIC_API_KEY")
    encryption_key: str = Field(..., env="ENCRYPTION_KEY")
    
    # Security settings
    jwt_secret: str = Field(..., env="JWT_SECRET")
    max_execution_time: int = Field(300, env="MAX_EXECUTION_TIME")
    max_memory_mb: int = Field(1024, env="MAX_MEMORY_MB")
    allowed_imports: List[str] = ["json", "math", "datetime", "typing", "dataclasses"]
    
    # Database
    redis_url: str = Field("redis://localhost:6379/0", env="REDIS_URL")
    postgres_url: Optional[str] = Field(None, env="POSTGRES_URL")
    
    @validator('openai_api_key', 'anthropic_api_key', pre=True)
    def validate_api_keys(cls, v: str) -> str:
        """Validate API key format."""
        if not v or len(v) < 20:
            raise ValueError("Invalid API key format")
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = False


class ModelConfig(BaseSettings):
    """Model routing and optimization configuration."""
    
    # Local model settings
    ollama_base_url: str = Field("http://localhost:11434", env="OLLAMA_BASE_URL")
    local_model_timeout: int = Field(120, env="LOCAL_MODEL_TIMEOUT")
    
    # Cost management
    monthly_budget_usd: float = Field(1000.0, env="MONTHLY_BUDGET_USD")
    cost_alert_threshold: float = Field(0.8, env="COST_ALERT_THRESHOLD")
    cache_ttl_seconds: int = Field(3600, env="CACHE_TTL_SECONDS")
    
    # Model routing
    use_local_for_simple_tasks: bool = Field(True, env="USE_LOCAL_FOR_SIMPLE_TASKS")
    complexity_threshold: float = Field(0.7, env="COMPLEXITY_THRESHOLD")
    
    # Model configurations
    model_configs: Dict[str, Any] = {
        "high_performance": {
            "models": ["claude-3-opus-20240229", "gpt-4-turbo-preview"],
            "temperature": 0.1,
            "max_tokens": 4000,
            "cost_per_1k_tokens": 0.075
        },
        "standard": {
            "models": ["gpt-4", "claude-3-sonnet-20240229"],
            "temperature": 0.3,
            "max_tokens": 2000,
            "cost_per_1k_tokens": 0.030
        },
        "economic": {
            "models": ["gpt-3.5-turbo", "claude-instant-1.2"],
            "temperature": 0.5,
            "max_tokens": 1000,
            "cost_per_1k_tokens": 0.002
        },
        "local": {
            "models": ["deepseek-coder:33b", "codellama:34b", "mixtral:8x7b"],
            "temperature": 0.1,
            "max_tokens": 4000,
            "cost_per_1k_tokens": 0.0002
        }
    }


class MonitoringConfig(BaseSettings):
    """Monitoring and observability configuration."""
    
    prometheus_port: int = Field(8000, env="PROMETHEUS_PORT")
    log_level: str = Field("INFO", env="LOG_LEVEL")
    enable_tracing: bool = Field(True, env="ENABLE_TRACING")
    
    # Structured logging format
    log_format: str = "json"
    
    # Metrics configuration
    metrics_enabled: bool = True
    metrics_prefix: str = "autogen_enterprise"


class ConfigManager:
    """Central configuration management with encryption support."""
    
    def __init__(self):
        self.security = SecurityConfig()
        self.models = ModelConfig()
        self.monitoring = MonitoringConfig()
        self._fernet = None
        
    @property
    def fernet(self) -> Fernet:
        """Lazy load Fernet encryption."""
        if not self._fernet:
            self._fernet = Fernet(self.security.encryption_key.encode())
        return self._fernet
    
    def encrypt_value(self, value: str) -> str:
        """Encrypt sensitive values."""
        return self.fernet.encrypt(value.encode()).decode()
    
    def decrypt_value(self, encrypted_value: str) -> str:
        """Decrypt sensitive values."""
        return self.fernet.decrypt(encrypted_value.encode()).decode()
    
    def get_llm_config(self, tier: str) -> Dict[str, Any]:
        """Get LLM configuration for specified tier with cost optimization."""
        
        if tier not in ["high_performance", "standard", "economic", "local"]:
            raise ValueError(f"Invalid tier: {tier}")
        
        model_config = self.models.model_configs[tier]
        
        if tier == "local":
            return {
                "config_list": [{
                    "model": model_config["models"][0],
                    "base_url": f"{self.models.ollama_base_url}/v1",
                    "api_key": "ollama",
                    "timeout": self.models.local_model_timeout
                }],
                "temperature": model_config["temperature"],
                "max_tokens": model_config["max_tokens"],
                "cache_seed": 42
            }
        else:
            # Cloud models
            config_list = []
            
            # Add OpenAI models
            if any("gpt" in model for model in model_config["models"]):
                for model in model_config["models"]:
                    if "gpt" in model:
                        config_list.append({
                            "model": model,
                            "api_key": self.security.openai_api_key,
                            "api_type": "openai"
                        })
            
            # Add Anthropic models
            if any("claude" in model for model in model_config["models"]):
                for model in model_config["models"]:
                    if "claude" in model:
                        config_list.append({
                            "model": model,
                            "api_key": self.security.anthropic_api_key,
                            "api_type": "anthropic"
                        })
            
            return {
                "config_list": config_list,
                "temperature": model_config["temperature"],
                "max_tokens": model_config["max_tokens"],
                "cache_seed": 42,
                "response_format": {"type": "json_object"}
            }
    
    def get_model_cost(self, tier: str) -> float:
        """Get cost per 1000 tokens for specified tier."""
        return self.models.model_configs[tier]["cost_per_1k_tokens"]
    
    def validate_configuration(self) -> bool:
        """Validate all configuration settings."""
        try:
            # Test encryption
            test_value = "test_encryption"
            encrypted = self.encrypt_value(test_value)
            decrypted = self.decrypt_value(encrypted)
            assert decrypted == test_value
            
            # Validate API keys format
            assert len(self.security.openai_api_key) > 20
            assert len(self.security.anthropic_api_key) > 20
            
            # Validate model configurations
            for tier in ["high_performance", "standard", "economic", "local"]:
                config = self.get_llm_config(tier)
                assert "config_list" in config
                assert len(config["config_list"]) > 0
            
            logger.info("Configuration validation successful")
            return True
            
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            return False


# Global configuration instance
config_manager = ConfigManager()