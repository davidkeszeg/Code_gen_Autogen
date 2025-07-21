#!/usr/bin/env python3
"""
Enterprise AutoGen Code Generation System - Main Controller
Professzionális kódgenerátor rendszer nem-programozók számára
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import ConfigManager, SystemValidator
from core.orchestrator import WorkflowOrchestrator
from core.agents.agent_factory import AgentFactory
from core.workflow.fsm_engine import CodeGenerationFSM
from core.prompt_optimizer import PromptOptimizer
from utils.logger import setup_logging

logger = setup_logging(__name__)


class AutoGenCodeGenerator:
    """
    Fő vezérlő osztály - kezeli a teljes kódgenerálási folyamatot
    Automatikusan optimalizálja a promptokat és minimalizálja a hibákat
    """
    
    def __init__(self):
        logger.info("AutoGen Code Generator inicializálása...")
        
        # Konfiguráció betöltése
        self.config = ConfigManager()
        
        # Rendszer validátor
        self.validator = SystemValidator(self.config)
        
        # Prompt optimalizáló
        self.prompt_optimizer = PromptOptimizer()
        
        # Agent factory
        self.agent_factory = AgentFactory(self.config)
        
        # Workflow orchestrator
        self.orchestrator = None
        
        # FSM engine
        self.fsm_engine = None
        
        self.is_initialized = False
        
    async def initialize(self) -> bool:
        """
        Rendszer inicializálása és validálása
        """
        try:
            logger.info("Rendszer validálása...")
            
            # 1. Környezet validálása
            validation_result = await self.validator.validate_system()
            if not validation_result.is_valid:
                logger.error(f"Rendszer validáció sikertelen: {validation_result.errors}")
                return False
                
            logger.info("✓ Környezet validálva")
            
            # 2. Modellek kompatibilitásának ellenőrzése
            model_check = await self.validator.check_model_compatibility()
            if not model_check.compatible:
                logger.error(f"Model kompatibilitási hiba: {model_check.issues}")
                return False
                
            logger.info("✓ Modellek kompatibilisek")
            
            # 3. Agentek inicializálása
            logger.info("Agentek létrehozása...")
            agents = await self.agent_factory.create_all_agents()
            
            # 4. FSM motor inicializálása
            self.fsm_engine = CodeGenerationFSM()
            
            # 5. Orchestrator inicializálása
            self.orchestrator = WorkflowOrchestrator(
                agents=agents,
                fsm_engine=self.fsm_engine,
                config=self.config
            )
            
            logger.info("✓ Rendszer sikeresen inicializálva")
            self.is_initialized = True
            return True
            
        except Exception as e:
            logger.error(f"Inicializálási hiba: {str(e)}")
            return False
    
    async def generate_code(self, user_request: str, project_type: str = "general") -> Dict[str, Any]:
        """
        Kód generálása egyszerű természetes nyelvű kérés alapján
        
        Args:
            user_request: Egyszerű magyar vagy angol nyelvű leírás
            project_type: Projekt típusa (web, api, trading, data_analysis, stb.)
            
        Returns:
            Dict a generált kóddal és dokumentációval
        """
        if not self.is_initialized:
            raise RuntimeError("A rendszer nincs inicializálva. Hívja meg először az initialize() metódust.")
            
        try:
            logger.info(f"Új kódgenerálási kérés: {user_request[:100]}...")
            
            # 1. Prompt optimalizálás - átalakítjuk profi prompttá
            optimized_prompt = await self.prompt_optimizer.optimize_user_request(
                user_request=user_request,
                project_type=project_type
            )
            
            logger.info("✓ Prompt optimalizálva")
            
            # 2. Rendszer kontextus felépítése
            system_context = {
                "original_request": user_request,
                "optimized_prompt": optimized_prompt,
                "project_type": project_type,
                "timestamp": datetime.utcnow().isoformat(),
                "quality_requirements": {
                    "code_coverage": 0.95,
                    "type_hints": 0.90,
                    "documentation": "comprehensive",
                    "error_handling": "production-grade",
                    "integration_ready": True
                }
            }
            
            # 3. Workflow végrehajtása
            logger.info("Kódgenerálási workflow indítása...")
            result = await self.orchestrator.execute_workflow(system_context)
            
            # 4. Eredmény validálása
            if result.success:
                logger.info("✓ Kód sikeresen generálva")
                
                # Eredmény struktúra
                return {
                    "success": True,
                    "generated_files": result.generated_files,
                    "documentation": result.documentation,
                    "integration_guide": result.integration_guide,
                    "test_results": result.test_results,
                    "quality_score": result.quality_score,
                    "warnings": result.warnings,
                    "next_steps": self._generate_next_steps(result)
                }
            else:
                logger.error(f"Kódgenerálás sikertelen: {result.error}")
                return {
                    "success": False,
                    "error": result.error,
                    "suggestions": result.suggestions
                }
                
        except Exception as e:
            logger.error(f"Kódgenerálási hiba: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "suggestions": ["Próbálja meg újrafogalmazni a kérést", 
                               "Ellenőrizze a projekt típust",
                               "Részletesebb leírást adjon"]
            }
    
    def _generate_next_steps(self, result: Any) -> List[str]:
        """
        Következő lépések generálása a felhasználó számára
        """
        steps = []
        
        if result.quality_score < 90:
            steps.append("A generált kód további optimalizálást igényelhet")
            
        if result.warnings:
            steps.append(f"Tekintse át a figyelmeztetéseket ({len(result.warnings)} db)")
            
        steps.extend([
            "Telepítse a függőségeket: pip install -r requirements.txt",
            "Futtassa a teszteket: pytest tests/",
            "Olvassa el az integrációs útmutatót",
            "Konfigurálja a környezeti változókat a .env.example alapján"
        ])
        
        return steps
    
    async def generate_from_template(self, template_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Kód generálása előre definiált sablon alapján
        """
        templates = {
            "trading_bot": "Készíts egy professzionális trading botot {strategy} stratégiával, {broker} brókerhez",
            "rest_api": "Készíts egy REST API-t {entity} kezelésére, {database} adatbázissal",
            "web_scraper": "Készíts egy web scraper-t {target_site} oldalhoz, {output_format} formátumú kimenettel",
            "data_pipeline": "Készíts egy adat pipeline-t {source} forrásból {destination} célba",
            "ml_model": "Készíts egy {model_type} ML modellt {task} feladatra"
        }
        
        if template_name not in templates:
            raise ValueError(f"Ismeretlen sablon: {template_name}")
            
        # Sablon kitöltése
        prompt = templates[template_name].format(**parameters)
        
        # Normál generálás a kitöltött sablonnal
        return await self.generate_code(prompt, project_type=template_name.split('_')[0])
    
    async def validate_generated_code(self, file_path: str) -> Dict[str, Any]:
        """
        Már generált kód validálása
        """
        return await self.orchestrator.validate_code(file_path)
    
    async def shutdown(self):
        """
        Rendszer leállítása
        """
        logger.info("Rendszer leállítása...")
        if self.orchestrator:
            await self.orchestrator.shutdown()
        logger.info("✓ Rendszer leállítva")


async def main():
    """
    Példa használat
    """
    generator = AutoGenCodeGenerator()
    
    # Inicializálás
    if not await generator.initialize():
        print("❌ Rendszer inicializálási hiba!")
        return
        
    print("✅ AutoGen Code Generator sikeresen elindult!")
    print("-" * 50)
    
    # Példa: Trading bot generálása
    print("\n📊 Trading Bot generálása...")
    result = await generator.generate_code(
        user_request="Készíts egy crypto trading botot ami 15 perces gyertyákon kereskedik, "
                    "RSI és MACD indikátorokat használ, kockázatkezeléssel",
        project_type="trading"
    )
    
    if result["success"]:
        print(f"✅ Sikeres generálás!")
        print(f"📁 Generált fájlok: {len(result['generated_files'])}")
        print(f"📊 Minőségi pontszám: {result['quality_score']}/100")
        print(f"📝 Következő lépések:")
        for step in result["next_steps"]:
            print(f"   - {step}")
    else:
        print(f"❌ Hiba: {result['error']}")
        
    # Példa: Sablon alapú generálás
    print("\n🔧 API generálása sablonból...")
    api_result = await generator.generate_from_template(
        template_name="rest_api",
        parameters={
            "entity": "felhasználók és termékek",
            "database": "PostgreSQL"
        }
    )
    
    if api_result["success"]:
        print(f"✅ API sikeresen generálva!")
        
    await generator.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
