"""
Secure code execution with sandboxing and validation.
"""
import ast
import re
import os
import json
import asyncio
import tempfile
import shutil
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from datetime import datetime
import docker
import logging

logger = logging.getLogger(__name__)


@dataclass
class SecurityScanResult:
    """Security scan results."""
    safe: bool
    risk_level: str  # low, medium, high
    violations: List[str]
    warnings: List[str]
    scan_time: float


@dataclass
class ExecutionResult:
    """Code execution results."""
    success: bool
    output: str
    error: Optional[str]
    execution_time: float
    memory_used: Optional[int]
    security_scan: SecurityScanResult


class CodeSecurityScanner:
    """Comprehensive security scanning for code."""
    
    def __init__(self, config):
        self.config = config
        self.dangerous_imports = {
            "os", "subprocess", "sys", "eval", "exec", "compile",
            "__import__", "importlib", "open", "file", "input",
            "raw_input", "execfile", "reload", "globals", "locals",
            "vars", "dir", "getattr", "setattr", "delattr"
        }
        
        self.dangerous_patterns = [
            (r"eval\s*\(", "Use of eval() detected"),
            (r"exec\s*\(", "Use of exec() detected"),
            (r"__import__\s*\(", "Dynamic import detected"),
            (r"subprocess\.", "Subprocess usage detected"),
            (r"os\.system", "OS command execution detected"),
            (r"open\s*\(", "File operation detected"),
            (r"compile\s*\(", "Dynamic code compilation detected"),
            (r"globals\s*\(\)", "Global scope access detected"),
            (r"locals\s*\(\)", "Local scope access detected"),
            (r"\b__\w+__\b", "Dunder method usage detected")
        ]
        
        self.secret_patterns = [
            (r"(?i)(api[_-]?key|apikey)\s*[:=]\s*['\"][^'\"]+['\"]", "Hardcoded API key detected"),
            (r"(?i)(password|passwd|pwd)\s*[:=]\s*['\"][^'\"]+['\"]", "Hardcoded password detected"),
            (r"(?i)(secret|token)\s*[:=]\s*['\"][^'\"]+['\"]", "Hardcoded secret detected"),
            (r"(?i)(aws[_-]?access[_-]?key[_-]?id)\s*[:=]", "AWS credentials detected"),
            (r"(?i)(aws[_-]?secret[_-]?access[_-]?key)\s*[:=]", "AWS secret key detected")
        ]
        
    async def scan_code(self, code: str, language: str = "python") -> SecurityScanResult:
        """Perform comprehensive security scan on code."""
        
        start_time = asyncio.get_event_loop().time()
        violations = []
        warnings = []
        
        if language == "python":
            # AST-based analysis
            try:
                tree = ast.parse(code)
                violations.extend(self._analyze_ast(tree))
            except SyntaxError as e:
                violations.append(f"Syntax error: {e}")
                return SecurityScanResult(
                    safe=False,
                    risk_level="high",
                    violations=violations,
                    warnings=warnings,
                    scan_time=asyncio.get_event_loop().time() - start_time
                )
            
        # Pattern-based analysis
        for pattern, message in self.dangerous_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                violations.append(message)
                
        # Secret detection
        for pattern, message in self.secret_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                violations.append(message)
                
        # Check for network operations
        network_patterns = [
            (r"urllib|requests|http\.client|socket", "Network operation detected"),
            (r"urlopen|urlretrieve", "URL access detected")
        ]
        
        for pattern, message in network_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                warnings.append(message)
        
        # Determine risk level
        if violations:
            if any("eval" in v or "exec" in v or "subprocess" in v for v in violations):
                risk_level = "high"
            elif len(violations) > 3:
                risk_level = "high"
            else:
                risk_level = "medium"
        elif warnings:
            risk_level = "low"
        else:
            risk_level = "low"
            
        safe = risk_level == "low" and len(violations) == 0
        
        scan_time = asyncio.get_event_loop().time() - start_time
        
        return SecurityScanResult(
            safe=safe,
            risk_level=risk_level,
            violations=violations,
            warnings=warnings,
            scan_time=scan_time
        )
    
    def _analyze_ast(self, tree: ast.AST) -> List[str]:
        """Analyze AST for security issues."""
        
        violations = []
        
        for node in ast.walk(tree):
            # Check imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in self.dangerous_imports:
                        violations.append(f"Dangerous import: {alias.name}")
                        
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module in self.dangerous_imports:
                    violations.append(f"Dangerous import from: {node.module}")
                    
            # Check function calls
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in ["eval", "exec", "compile", "__import__"]:
                        violations.append(f"Dangerous function call: {node.func.id}")
                        
            # Check attribute access
            elif isinstance(node, ast.Attribute):
                if node.attr.startswith("_") and not node.attr.startswith("__"):
                    violations.append(f"Private attribute access: {node.attr}")
                    
        return violations


class SecureCodeExecutor:
    """Secure code execution with Docker sandboxing."""
    
    def __init__(self, config):
        self.config = config
        self.scanner = CodeSecurityScanner(config)
        self.docker_client = None
        
    async def initialize(self):
        """Initialize Docker client."""
        try:
            self.docker_client = docker.from_env()
            logger.info("Docker client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Docker: {e}")
            raise
            
    async def execute_code(self, code: str, language: str = "python", 
                          timeout: Optional[int] = None) -> ExecutionResult:
        """Execute code securely in sandboxed environment."""
        
        # Security scan first
        security_scan = await self.scanner.scan_code(code, language)
        
        if not security_scan.safe and security_scan.risk_level == "high":
            return ExecutionResult(
                success=False,
                output="",
                error=f"Code failed security scan: {', '.join(security_scan.violations)}",
                execution_time=0.0,
                memory_used=None,
                security_scan=security_scan
            )
            
        # Prepare for execution
        timeout = timeout or self.config.security.max_execution_time
        
        if self.docker_client:
            return await self._execute_in_docker(code, language, timeout, security_scan)
        else:
            return await self._execute_local_restricted(code, language, timeout, security_scan)
    
    async def _execute_in_docker(self, code: str, language: str, 
                                timeout: int, security_scan: SecurityScanResult) -> ExecutionResult:
        """Execute code in Docker container."""
        
        start_time = asyncio.get_event_loop().time()
        
        # Create temporary directory for code
        with tempfile.TemporaryDirectory() as temp_dir:
            code_file = os.path.join(temp_dir, "code.py")
            with open(code_file, "w") as f:
                f.write(code)
                
            try:
                # Container configuration
                container_config = {
                    "image": self._get_docker_image(language),
                    "command": f"python /code/code.py",
                    "volumes": {temp_dir: {"bind": "/code", "mode": "ro"}},
                    "working_dir": "/code",
                    "mem_limit": f"{self.config.security.max_memory_mb}m",
                    "memswap_limit": f"{self.config.security.max_memory_mb}m",
                    "cpu_quota": 50000,  # 50% CPU
                    "cpu_period": 100000,
                    "network_mode": "none",  # No network access
                    "read_only": True,
                    "user": "nobody:nogroup",
                    "security_opt": ["no-new-privileges"],
                    "cap_drop": ["ALL"],
                    "remove": True,
                    "detach": False
                }
                
                # Run container
                result = self.docker_client.containers.run(
                    **container_config,
                    timeout=timeout
                )
                
                output = result.decode("utf-8")
                execution_time = asyncio.get_event_loop().time() - start_time
                
                return ExecutionResult(
                    success=True,
                    output=self._sanitize_output(output),
                    error=None,
                    execution_time=execution_time,
                    memory_used=None,
                    security_scan=security_scan
                )
                
            except docker.errors.ContainerError as e:
                return ExecutionResult(
                    success=False,
                    output="",
                    error=f"Execution error: {str(e)}",
                    execution_time=asyncio.get_event_loop().time() - start_time,
                    memory_used=None,
                    security_scan=security_scan
                )
            except docker.errors.APIError as e:
                return ExecutionResult(
                    success=False,
                    output="",
                    error=f"Docker API error: {str(e)}",
                    execution_time=asyncio.get_event_loop().time() - start_time,
                    memory_used=None,
                    security_scan=security_scan
                )
    
    async def _execute_local_restricted(self, code: str, language: str,
                                      timeout: int, security_scan: SecurityScanResult) -> ExecutionResult:
        """Execute code locally with restrictions (fallback)."""
        
        start_time = asyncio.get_event_loop().time()
        
        # Create restricted globals
        restricted_globals = {
            "__builtins__": {
                "print": print,
                "len": len,
                "range": range,
                "str": str,
                "int": int,
                "float": float,
                "list": list,
                "dict": dict,
                "tuple": tuple,
                "set": set,
                "bool": bool,
                "abs": abs,
                "min": min,
                "max": max,
                "sum": sum,
                "sorted": sorted,
                "enumerate": enumerate,
                "zip": zip,
                "map": map,
                "filter": filter,
                "any": any,
                "all": all
            },
            "__name__": "__main__",
            "__doc__": None,
            "__package__": None
        }
        
        # Capture output
        from io import StringIO
        import sys
        
        old_stdout = sys.stdout
        sys.stdout = output_buffer = StringIO()
        
        try:
            # Execute with timeout
            exec_globals = restricted_globals.copy()
            exec_locals = {}
            
            exec(code, exec_globals, exec_locals)
            
            output = output_buffer.getvalue()
            execution_time = asyncio.get_event_loop().time() - start_time
            
            return ExecutionResult(
                success=True,
                output=self._sanitize_output(output),
                error=None,
                execution_time=execution_time,
                memory_used=None,
                security_scan=security_scan
            )
            
        except Exception as e:
            return ExecutionResult(
                success=False,
                output=output_buffer.getvalue(),
                error=f"Execution error: {str(e)}",
                execution_time=asyncio.get_event_loop().time() - start_time,
                memory_used=None,
                security_scan=security_scan
            )
        finally:
            sys.stdout = old_stdout
    
    def _get_docker_image(self, language: str) -> str:
        """Get appropriate Docker image for language."""
        
        images = {
            "python": "python:3.11-alpine",
            "javascript": "node:18-alpine",
            "java": "openjdk:11-alpine",
            "go": "golang:1.21-alpine"
        }
        
        return images.get(language, "python:3.11-alpine")
    
    def _sanitize_output(self, output: str) -> str:
        """Sanitize output to remove sensitive information."""
        
        # Remove potential file paths
        output = re.sub(r"(/[a-zA-Z0-9_\-./]+)+", "[PATH]", output)
        
        # Remove potential IP addresses
        output = re.sub(r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b", "[IP]", output)
        
        # Remove potential URLs
        output = re.sub(r"https?://[^\s]+", "[URL]", output)
        
        # Truncate if too long
        max_length = 10000
        if len(output) > max_length:
            output = output[:max_length] + "\n... (output truncated)"
            
        return output