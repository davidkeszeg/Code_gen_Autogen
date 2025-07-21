# AutoGen Enterprise Code Generator

A professional-grade code generation system using Microsoft AutoGen with multi-agent architecture, enterprise security, and intelligent cost optimization.

## 🚀 Features

- **Multi-Agent Architecture**: 8 specialized agents (SystemArchitect, CodeGenerator, SecurityValidator, etc.)
- **Cost Optimization**: 60-90% cost reduction through intelligent model routing
- **FSM Workflow**: Deterministic execution with state persistence and recovery
- **Enterprise Security**: Docker sandboxing, comprehensive code scanning, encrypted configs
- **Production Ready**: Kubernetes deployment, monitoring, health checks, audit logging
- **JSON-Only Communication**: No "agent chatter" - strict structured communication

## 📋 Requirements

- Python 3.9+
- Docker (for secure code execution)
- Redis (for caching and state management)
- OpenAI API key and/or Anthropic API key
- Local LLM server (Ollama) for cost optimization

## 🛠️ Installation

### 1. Clone the repository
```bash
git clone https://github.com/enterprise/autogen-enterprise.git
cd autogen-enterprise
```

### 2. Install dependencies
```bash
pip install -e ".[dev]"
```

### 3. Configure environment
```bash
cp .env.example .env
# Edit .env with your API keys and configuration
```

### 4. Start Redis
```bash
docker run -d -p 6379:6379 redis:alpine
```

### 5. Start Ollama (for local models)
```bash
docker run -d -p 11434:11434 ollama/ollama
# Pull required models
docker exec -it ollama ollama pull deepseek-coder:33b
docker exec -it ollama ollama pull codellama:34b
```

## 🚀 Quick Start

### Server Mode
```bash
python -m src.main --mode server --port 8080
```

### CLI Mode
```bash
python -m src.main --mode cli --requirements example_requirements.json
```

### API Usage
```python
import requests

# Generate code via API
response = requests.post(
    "http://localhost:8080/api/v1/generate",
    headers={"Authorization": "Bearer your-token"},
    json={
        "project_name": "my_trading_bot",
        "description": "Algorithmic trading bot with ML predictions",
        "requirements": {
            "core_features": ["market data processing", "signal generation"],
            "technical_requirements": ["low latency", "high reliability"]
        },
        "technology_stack": ["Python", "FastAPI", "PostgreSQL"]
    }
)

result = response.json()
print(f"Workflow ID: {result['workflow_id']}")
```

## 🏗️ Architecture

### Agent Roles

1. **SystemArchitect** (GPT-4/Claude): Analyzes requirements, designs architecture
2. **PromptEngineer** (Standard tier): Creates detailed implementation prompts
3. **CodeGenerator** (Local): Generates production code
4. **CodeReviewer** (Local): Reviews code quality and standards
5. **SecurityValidator** (GPT-4/Claude): Security scanning and validation
6. **TestRunner** (Local): Executes tests and validation
7. **DocumentationGenerator** (Local): Creates comprehensive documentation
8. **QualityGate** (GPT-4/Claude): Final approval before deployment

### Cost Optimization Strategy

```
Simple Tasks (Complexity < 0.3) → Local Models ($0.0002/1k tokens)
Moderate Tasks (0.3-0.7) → Economic/Standard Tier ($0.002-0.03/1k tokens)
Complex Tasks (> 0.7) → High Performance ($0.075/1k tokens)
```

### Workflow States

```mermaid
graph LR
    Init --> RequirementsAnalyzed
    RequirementsAnalyzed --> ArchitectureDesigned
    ArchitectureDesigned --> PromptEngineered
    PromptEngineered --> CodeGenerated
    CodeGenerated --> CodeReviewed
    CodeReviewed --> SecurityValidated
    SecurityValidated --> TestsExecuted
    TestsExecuted --> DocumentationGenerated
    DocumentationGenerated --> QualityApproved
    QualityApproved --> Completed
```

## 📊 Monitoring

### Prometheus Metrics
- `autogen_workflows_total`: Total workflows by status
- `autogen_workflow_duration_seconds`: Execution time histogram
- `autogen_agent_response_seconds`: Per-agent response times
- `autogen_llm_cost_dollars`: Cost tracking by model/agent

### Health Check
```bash
curl http://localhost:8080/api/v1/health
```

### Cost Report
```bash
curl -H "Authorization: Bearer token" \
  http://localhost:8080/api/v1/cost-report
```

## 🔒 Security

- All API keys encrypted at rest
- Docker-based code execution sandboxing
- Comprehensive code security scanning
- Network isolation for executed code
- Audit logging for all operations
- JWT-based API authentication

## 🚀 Production Deployment

### Docker
```bash
docker build -t autogen-enterprise .
docker run -d -p 8080:8080 --env-file .env autogen-enterprise
```

### Kubernetes
```bash
kubectl apply -f k8s/
kubectl get pods -l app=autogen-code-generator
```

## 📈 Performance

- **Workflow Execution**: < 60 seconds for complex projects
- **Cost Savings**: 60-90% vs cloud-only approach
- **Availability**: 99.9% uptime SLA
- **Throughput**: 100+ concurrent workflows
- **Cache Hit Rate**: 40-60% for similar requests

## 🧪 Testing

```bash
# Unit tests
pytest tests/unit/

# Integration tests
pytest tests/integration/

# Coverage report
pytest --cov=src --cov-report=html
```

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Microsoft AutoGen team for the excellent framework
- OpenAI and Anthropic for powerful language models
- The open-source community for local model alternatives