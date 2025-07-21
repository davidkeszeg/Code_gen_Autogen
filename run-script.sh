#!/bin/bash
# AutoGen Enterprise - Quick Start Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}AutoGen Enterprise Code Generator - Setup Script${NC}"
echo "================================================"

# Check prerequisites
echo -e "\n${YELLOW}Checking prerequisites...${NC}"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker is not installed. Please install Docker first.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker found${NC}"

# Check Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}Docker Compose is not installed. Please install Docker Compose first.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker Compose found${NC}"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python 3 is not installed. Please install Python 3.9+ first.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python found${NC}"

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo -e "\n${YELLOW}Creating .env file...${NC}"
    cp .env.example .env
    echo -e "${GREEN}✓ .env file created${NC}"
    echo -e "${YELLOW}Please edit .env file and add your API keys before continuing.${NC}"
    read -p "Press enter to continue after editing .env file..."
fi

# Create necessary directories
echo -e "\n${YELLOW}Creating directories...${NC}"
mkdir -p generated_code logs config/prometheus config/grafana/dashboards config/grafana/datasources
echo -e "${GREEN}✓ Directories created${NC}"

# Create Prometheus config if it doesn't exist
if [ ! -f config/prometheus.yml ]; then
    echo -e "\n${YELLOW}Creating Prometheus configuration...${NC}"
    cat > config/prometheus.yml <<EOF
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'autogen-app'
    static_configs:
      - targets: ['autogen-app:8000']
EOF
    echo -e "${GREEN}✓ Prometheus config created${NC}"
fi

# Create Grafana datasource config
if [ ! -f config/grafana/datasources/prometheus.yml ]; then
    echo -e "\n${YELLOW}Creating Grafana datasource configuration...${NC}"
    cat > config/grafana/datasources/prometheus.yml <<EOF
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
EOF
    echo -e "${GREEN}✓ Grafana datasource config created${NC}"
fi

# Main menu
while true; do
    echo -e "\n${GREEN}What would you like to do?${NC}"
    echo "1) Start all services (Docker Compose)"
    echo "2) Start development server (Python)"
    echo "3) Pull Ollama models"
    echo "4) Run example code generation"
    echo "5) View logs"
    echo "6) Stop all services"
    echo "7) Clean up (remove volumes)"
    echo "8) Exit"
    
    read -p "Select an option (1-8): " choice
    
    case $choice in
        1)
            echo -e "\n${YELLOW}Starting all services...${NC}"
            docker-compose up -d
            echo -e "${GREEN}✓ Services started${NC}"
            echo -e "\nServices available at:"
            echo "- API: http://localhost:8080"
            echo "- Metrics: http://localhost:8000"
            echo "- Prometheus: http://localhost:9090"
            echo "- Grafana: http://localhost:3000 (admin/admin)"
            ;;
        2)
            echo -e "\n${YELLOW}Starting development server...${NC}"
            python3 -m venv venv
            source venv/bin/activate
            pip install -r requirements.txt
            python -m src.main --mode server
            ;;
        3)
            echo -e "\n${YELLOW}Pulling Ollama models...${NC}"
            docker exec autogen-ollama ollama pull deepseek-coder:33b
            docker exec autogen-ollama ollama pull codellama:34b
            docker exec autogen-ollama ollama pull mixtral:8x7b
            echo -e "${GREEN}✓ Models pulled${NC}"
            ;;
        4)
            echo -e "\n${YELLOW}Running example code generation...${NC}"
            if [ -f venv/bin/activate ]; then
                source venv/bin/activate
            fi
            python -m src.main --mode cli --requirements example_requirements.json
            ;;
        5)
            echo -e "\n${YELLOW}Showing logs...${NC}"
            docker-compose logs -f --tail=100
            ;;
        6)
            echo -e "\n${YELLOW}Stopping all services...${NC}"
            docker-compose down
            echo -e "${GREEN}✓ Services stopped${NC}"
            ;;
        7)
            echo -e "\n${RED}This will remove all data. Are you sure? (y/N)${NC}"
            read -p "" confirm
            if [ "$confirm" = "y" ]; then
                docker-compose down -v
                rm -rf generated_code/* logs/*
                echo -e "${GREEN}✓ Cleanup complete${NC}"
            fi
            ;;
        8)
            echo -e "\n${GREEN}Goodbye!${NC}"
            exit 0
            ;;
        *)
            echo -e "${RED}Invalid option${NC}"
            ;;
    esac
done