"""Configuración central de Lexa. Todo lo ajustable vive aquí."""
import os
from dataclasses import dataclass

try:  # python-dotenv es opcional
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


@dataclass(frozen=True)
class Settings:
    modelo: str = os.getenv("LEXA_MODEL", "anthropic/claude-sonnet-5-5")
    max_iters: int = int(os.getenv("LEXA_MAX_ITERS", "6"))
    max_alternativas: int = int(os.getenv("LEXA_MAX_ALTERNATIVAS", "3"))  # [AJUSTABLE]
    max_emojis: int = 1  # [AJUSTABLE] solo en canales informales
    umbral_venta_corporativa_cop: int = 5_000_000  # [AJUSTABLE] valor de ejemplo, definir con negocio
    temperatura: float = 0.3


SETTINGS = Settings()
