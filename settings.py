import os
from dotenv import load_dotenv
from typing import Dict, Any, List
import logging

# Logger beállítása a modul szintjén, hogy mindenhol elérhető legyen
logger = logging.getLogger(__name__)

class ConfigManager:
    """
    Kezeli a környezeti változókat és a teljes rendszerkonfigurációt.
    Felelős az API kulcsok és a modellbeállítások betöltéséért a .env fájlból,
    és biztosítja a különböző szintekhez (tiers) a megfelelő LLM-konfigurációt.
    """
    def __init__(self, env_path: str = ".env"):
        """
        Betölti a .env fájlt és inicializálja a konfigurációt.
        Ha a fájl nem létezik, figyelmeztetést ad, de a már meglévő
        környezeti változókkal megpróbál működni.
        """
        if not os.path.exists(env_path):
            logger.warning(f"A megadott .env fájl nem található itt: {env_path}. A rendszer csak a meglévő környezeti változókra támaszkodik.")
            load_dotenv()
        else:
            load_dotenv(dotenv_path=env_path)
            logger.info(f".env fájl sikeresen betöltve innen: {env_path}")
            
        self.model_configs = self._load_model_configs()
        logger.info("ConfigManager inicializálva, LLM konfigurációk betöltve.")

    def _load_model_configs(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Betölti és összeállítja a különböző szintű LLM-ek konfigurációját.
        Prioritást ad a jobb minőségű modelleknek (Claude), de tartalékként
        kezeli az OpenAI modelleket is, ha van hozzájuk API kulcs.
        """
        configs = {
            "high_performance": [],
            "standard": [],
            "local": []
        }

        # 1. Elsődleges modellek (Anthropic - Claude) beállítása
        if os.getenv("ANTHROPIC_API_KEY"):
            logger.info("Anthropic (Claude) API kulcs megtalálva. Claude modellek beállítása.")
            configs["high_performance"].append({
                "model": "claude-3-opus-20240229",
                "api_key": os.getenv("ANTHROPIC_API_KEY"),
                "api_type": "anthropic"
            })
            configs["standard"].append({
                "model": "claude-3-sonnet-20240229",
                "api_key": os.getenv("ANTHROPIC_API_KEY"),
                "api_type": "anthropic"
            })
        else:
            logger.warning("ANTHROPIC_API_KEY nincs beállítva. A Claude modellek nem lesznek használhatók.")

        # 2. Tartalék (Failover) modellek (OpenAI - GPT) beállítása
        if os.getenv("OPENAI_API_KEY"):
            logger.info("OpenAI API kulcs megtalálva. Tartalék GPT modellek beállítása.")
            configs["high_performance"].append({
                "model": "gpt-4o",
                "api_key": os.getenv("OPENAI_API_KEY"),
                "api_type": "openai"
            })
            configs["standard"].append({
                "model": "gpt-4o", 
                "api_key": os.getenv("OPENAI_API_KEY"),
                "api_type": "openai"
            })
        else:
            logger.warning("OPENAI_API_KEY nincs beállítva. Az OpenAI modellek nem lesznek használhatók.")

        # 3. Helyi (Local) modell beállítása (Ollama)
        configs["local"].append({
            "model": os.getenv("LOCAL_MODEL", "deepseek-coder-v2-lite"),
            "api_key": "ollama",
            "base_url": os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434/v1"),
            "api_type": "openai" 
        })
        logger.info(f"Helyi modell beállítva: {configs['local'][0]['model']} a {configs['local'][0]['base_url']} címen.")
        
        final_configs = {}
        for tier, tier_configs in configs.items():
            if tier_configs:
                final_configs[tier] = tier_configs
            else:
                logger.error(f"KRITIKUS: Nincs egyetlen használható modell sem a(z) '{tier}' szinthez! Ez a szint hibát fog dobni.")
        
        return final_configs

    def get_llm_config(self, tier: str) -> Dict[str, Any]:
        """
        Visszaadja a megadott szinthez (tier) tartozó LLM konfigurációt.
        """
        if tier not in self.model_configs:
            error_msg = f"Nincs érvényes konfiguráció a '{tier}' szinthez. Ellenőrizd a .env fájlt és a környezeti változókat!"
            logger.critical(error_msg)
            raise ValueError(error_msg)

        return {"config_list": self.model_configs[tier]}