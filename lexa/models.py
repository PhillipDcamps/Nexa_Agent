"""Modelos de datos (equivalen al esquema de base de datos).

Igual que en el tutorial de DSPy, se usan modelos pydantic simples.
Las fechas viajan como texto ISO (AAAA-MM-DDTHH:MM) porque los modelos de
lenguaje fallan menos con texto que con objetos datetime.
"""
from typing import Literal, Optional

from pydantic import BaseModel, Field

TipoCliente = Literal["persona", "empresa"]


class Aliado(BaseModel):
    aliado_id: str
    nombre: str
    sector: str
    servicios: list[str]
    requisitos: str
    cobertura: str


class Producto(BaseModel):
    producto_id: str
    nombre: str
    categoria: str
    aliado_id: str
    perfil_ideal: Literal["persona", "empresa", "ambos"]
    beneficios: list[str]
    precio_cop: Optional[int] = None
    condiciones: str = ""
    promocion_vigente: Optional[str] = None  # solo si hay fecha de cierre verificable


class Consentimiento(BaseModel):
    cliente_id: str
    canal: str
    fecha_hora: str
    acepta: bool


class Lead(BaseModel):
    cliente_id: str
    nombre: str
    contacto: str
    tipo_cliente: TipoCliente
    necesidad: str
    productos_interes: list[str] = Field(default_factory=list)
    etapa: str
    notas: str = ""


class ItemCotizacion(BaseModel):
    producto_id: str
    cantidad: int = 1
    plan: Optional[str] = None


class Cotizacion(BaseModel):
    cotizacion_id: str
    cliente_id: str
    items: list[ItemCotizacion]
    total_cop: int
    condiciones: str
    vigencia: str


class Cita(BaseModel):
    cita_id: str
    cliente_id: str
    tipo: Literal["asesoria", "demo", "cierre", "postventa"]
    fecha_hora: str
    modalidad: str
    tema: str
    asesor: str


class Escalamiento(BaseModel):
    escalamiento_id: str
    cliente_id: str
    motivo: str
    resumen_conversacion: str
    prioridad: Literal["baja", "media", "alta"]


class Resultado(BaseModel):
    cliente_id: str
    resultado: Literal["venta", "cita", "seguimiento", "rechazo", "sin_ajuste"]
    motivo_rechazo: Optional[str] = None
    alternativas_ofrecidas: int = 0
    fecha_seguimiento: Optional[str] = None


class Seguimiento(BaseModel):
    cliente_id: str
    fecha: str
    canal: str
    motivo: str


class EstadoInterno(BaseModel):
    """Bloque oculto para analítica y CRM. Nunca se muestra al cliente."""

    etapa: Literal["conectar", "descubrir", "proponer", "objecion", "cierre", "postventa", "despedida"]
    intencion_cliente: Literal["exploracion", "interes", "objecion", "listo_para_comprar", "rechazo_definitivo"]
    tipo_objecion: Literal["precio", "tiempo", "confianza", "necesidad", "competencia", "autoridad", "ninguna"]
    alternativas_ofrecidas: int
    productos_mencionados: list[str]
    siguiente_accion: str
