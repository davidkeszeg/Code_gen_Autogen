"""
Structured logging configuration.
"""
import logging
import sys
import json
from datetime import datetime
from typing import Any, Dict
import structlog
from structlog.processors import JSONRenderer, TimeStamper, add_log_level
from structlog.stdlib import LoggerFactory, add_logger_name


def setup_logging(log_level: str = "INFO", log_format: str = "json"):
    """Setup structured logging for the application."""
    
    # Configure structlog
    timestamper = TimeStamper(fmt="iso")
    
    # Processors for structured logging
    shared_processors = [
        timestamper,
        add_log_level,
        add_logger_name,
        add_correlation_id,
        add_application_context,
    ]
    
    # Configure output format
    if log_format == "json":
        renderer = JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()
    
    structlog.configure(
        processors=shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        context_class=dict,
        logger_factory=LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Configure standard logging
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            processor=renderer,
            foreign_pre_chain=shared_processors,
        )
    )
    
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Disable noisy loggers
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("docker").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def add_correlation_id(logger, method_name, event_dict):
    """Add correlation ID to log entries."""
    
    # Try to get correlation ID from context
    correlation_id = event_dict.get("correlation_id")
    
    if not correlation_id:
        # Generate new correlation ID if not present
        import uuid
        correlation_id = str(uuid.uuid4())
        
    event_dict["correlation_id"] = correlation_id
    return event_dict


def add_application_context(logger, method_name, event_dict):
    """Add application context to log entries."""
    
    event_dict["application"] = "autogen-enterprise"
    event_dict["environment"] = "production"  # Should come from env var
    event_dict["version"] = "1.0.0"
    
    return event_dict


class LoggerAdapter:
    """Logger adapter for adding contextual information."""
    
    def __init__(self, logger, extra: Dict[str, Any]):
        self.logger = logger
        self.extra = extra
        
    def bind(self, **kwargs) -> "LoggerAdapter":
        """Bind additional context."""
        new_extra = self.extra.copy()
        new_extra.update(kwargs)
        return LoggerAdapter(self.logger, new_extra)
        
    def _log(self, method, message, **kwargs):
        """Log with extra context."""
        kwargs.update(self.extra)
        getattr(self.logger, method)(message, **kwargs)
        
    def debug(self, message, **kwargs):
        self._log("debug", message, **kwargs)
        
    def info(self, message, **kwargs):
        self._log("info", message, **kwargs)
        
    def warning(self, message, **kwargs):
        self._log("warning", message, **kwargs)
        
    def error(self, message, **kwargs):
        self._log("error", message, **kwargs)
        
    def critical(self, message, **kwargs):
        self._log("critical", message, **kwargs)


def get_logger(name: str, **initial_context) -> LoggerAdapter:
    """Get a logger with initial context."""
    base_logger = structlog.get_logger(name)
    return LoggerAdapter(base_logger, initial_context)


class AuditLogger:
    """Specialized logger for security audit events."""
    
    def __init__(self):
        self.logger = get_logger("security.audit")
        
    def log_authentication(self, user_id: str, success: bool, method: str, ip_address: str = None):
        """Log authentication attempts."""
        self.logger.info(
            "authentication_attempt",
            user_id=user_id,
            success=success,
            method=method,
            ip_address=ip_address,
            event_type="authentication"
        )
        
    def log_authorization(self, user_id: str, resource: str, action: str, granted: bool):
        """Log authorization decisions."""
        self.logger.info(
            "authorization_check",
            user_id=user_id,
            resource=resource,
            action=action,
            granted=granted,
            event_type="authorization"
        )
        
    def log_code_execution(self, workflow_id: str, code_hash: str, security_scan: Dict[str, Any]):
        """Log code execution attempts."""
        self.logger.info(
            "code_execution",
            workflow_id=workflow_id,
            code_hash=code_hash,
            security_scan=security_scan,
            event_type="code_execution"
        )
        
    def log_data_access(self, user_id: str, data_type: str, operation: str, success: bool):
        """Log data access events."""
        self.logger.info(
            "data_access",
            user_id=user_id,
            data_type=data_type,
            operation=operation,
            success=success,
            event_type="data_access"
        )