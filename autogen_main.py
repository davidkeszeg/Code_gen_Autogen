#!/usr/bin/env python3
"""
Enterprise AutoGen Code Generation System - API Szerver
"""
import sys
import os
from pathlib import Path
import logging
import json
from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel, Field
import uvicorn
from typing import List

# Projekt gyökerének hozzáadása a path-hoz
sys.path.insert(0, str(Path(__file__).resolve().parent))

# A HELYES, KÖZÖSEN MEGÍRT KOMPONENSEK IMPORTÁLÁSA
from src.config.settings import ConfigManager
from src.core.workflow import GroupChatWorkflowManager

# Logolás beállítása
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# API Adatmodellek
class GenerationRequest(BaseModel):
    project_name: str = Field(..., description="A projekt neve.")
    description: str = Field(..., description="A projekt részletes leírása.")
    technology_stack_preferences: List[str] = Field(default_factory=list, description="Opcionális technológiai preferenciák.")

# FastAPI Alkalmazás
app = FastAPI(
    title="AutoGen Enterprise Code Generator",
    description="Professzionális, multi-ügynökös kódgeneráló rendszer.",
    version="1.0.0"
)

# Fő Alkalmazás Osztály
class Application:
    def __init__(self):
        self.config_manager = ConfigManager()
        self.workflow_manager = GroupChatWorkflowManager(config_manager=self.config_manager)
        logger.info("Az alkalmazás komponensei sikeresen inicializálva.")

application_instance = Application()

# API Végpontok
@app.post("/api/v1/generate", tags=["Code Generation"])
async def generate_code(request: GenerationRequest = Body(...)):
    try:
        logger.info(f"Új generálási kérés érkezett a '{request.project_name}' projekthez.")
        requirements = request.model_dump()
        result = await application_instance.workflow_manager.execute(requirements)
        
        if not result.get("success"):
            raise HTTPException(status_code=500, detail={
                "message": "A kódgenerálási munkafolyamat hibával leállt.",
                "error_details": result.get("error"),
                "final_state": result.get("final_state")
            })
        return {"message": "A kódgenerálási munkafolyamat sikeresen lefutott.", "workflow_result": result}
    except Exception as e:
        logger.error(f"Váratlan hiba a /generate végponton: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Belső szerverhiba történt.")

@app.get("/api/v1/health", tags=["System"])
async def health_check():
    return {"status": "ok", "message": "AutoGen service is running."}

# Szerver Indítása
if __name__ == "__main__":
    if not os.path.exists(".env"):
        print("KRITIKUS: .env fájl nem található. Kérlek, hozz létre egy .env fájlt az API kulcsaiddal.")
    else:
        print("Indul az AutoGen API szerver a http://127.0.0.1:8000 címen")
        uvicorn.run(app, host="127.0.0.1", port=8000)