"""Almacén en memoria con datos de demostración.

IMPORTANTE: los datos de aliados y productos salen de las propuestas y del
Brand Book entregados. Todo lo que dice DEMO debe reemplazarse por el
catálogo real (Google Sheets / CRM) antes de producción.
"""
import uuid
from dataclasses import dataclass, field
from typing import Optional

from .models import (
    Aliado, Cita, Consentimiento, Cotizacion, Escalamiento, Lead,
    Producto, Resultado, Seguimiento,
)


def nuevo_id(prefijo: str, largo: int = 8) -> str:
    return f"{prefijo}-{uuid.uuid4().hex[:largo]}"


# ---------------------------------------------------------------- aliados
ALIADOS: dict[str, Aliado] = {
    "tienda_electrico": Aliado(
        aliado_id="tienda_electrico",
        nombre="La Tienda del Eléctrico",
        sector="Material eléctrico",
        servicios=["Venta de material eléctrico", "Domicilio el mismo día en el Valle de Aburrá",
                   "Entregas programadas para contratistas"],
        requisitos="Entrega local dentro del Valle de Aburrá (hasta 8 km).",
        cobertura="Valle de Aburrá (zonas A, B y C)",
    ),
    "prismaticos": Aliado(
        aliado_id="prismaticos",
        nombre="Prismáticos",
        sector="Óptica",
        servicios=["Venta de productos ópticos", "Pedidos por WhatsApp sin registrarse"],
        requisitos="Entrega local en zonas A y B (hasta 5 km).",
        cobertura="Medellín, zonas A y B",
    ),
    "living57": Aliado(
        aliado_id="living57",
        nombre="Living57",
        sector="Asesoría de arriendos",
        servicios=["Asesoría para arrendar inmuebles"],
        requisitos="Presupuesto, zona y fecha de mudanza confirmados antes del contacto.",
        cobertura="El Retiro y Oriente Antioqueño",
    ),
}

# ---------------------------------------------------------------- catálogo (DEMO)
PRODUCTOS: dict[str, Producto] = {
    "ELEC-001": Producto(
        producto_id="ELEC-001", nombre="Ducha eléctrica", categoria="material eléctrico",
        aliado_id="tienda_electrico", perfil_ideal="ambos",
        beneficios=["Entrega el mismo día dentro del Valle de Aburrá"],
        precio_cop=94_000, condiciones="El domicilio se cobra según la zona."),
    "ELEC-002": Producto(
        producto_id="ELEC-002", nombre="Multitoma automático", categoria="material eléctrico",
        aliado_id="tienda_electrico", perfil_ideal="ambos",
        beneficios=["Entrega el mismo día dentro del Valle de Aburrá"],
        precio_cop=700_000, condiciones="El domicilio se cobra según la zona."),
    "LIV-001": Producto(
        producto_id="LIV-001", nombre="Asesoría de arriendo con Living57", categoria="inmobiliario",
        aliado_id="living57", perfil_ideal="persona",
        beneficios=["Asesor que conoce El Retiro y el Oriente Antioqueño"],
        precio_cop=None,
        condiciones="Antes de conectarte con el asesor se confirman presupuesto, zona y fecha de mudanza."),
    # TODO: cargar catálogo real de Prismáticos.
}

# ---------------------------------------------------------------- domicilios (de las propuestas)
# (zona, km_max, tarifa_total)
ZONAS = [("A", 3.0, 7_900), ("B", 5.0, 10_500), ("C", 8.0, 13_900)]
DOMICILIO_ALIADOS = {
    # aliado_id: (aporte del aliado, zonas habilitadas)
    "tienda_electrico": (4_500, {"A", "B", "C"}),
    "prismaticos": (4_500, {"A", "B"}),
}

# Distancia en km desde cada aliado hasta cada sector. DEMO: la completa el negocio con datos verificados.
# Ejemplo de formato:  "tienda_electrico": {"itagüí centro": 2.5}
DISTANCIAS_KM: dict[str, dict[str, float]] = {
    "tienda_electrico": {},
    "prismaticos": {},
}



def comision_lexa_interna(aliado_id: str, valor_compra: int) -> Optional[tuple[int, int]]:
    """Rango de comisión en pesos (mín, máx). USO INTERNO: Lexa nunca la revela.

    Según las propuestas vigentes; Living57 se calcula sobre la comisión de
    arriendo, que Lexa no conoce, por eso devuelve None.
    """
    if aliado_id == "prismaticos":
        c = round(valor_compra * 0.09)
        return c, c
    if aliado_id == "tienda_electrico":
        if valor_compra <= 150_000:
            return round(valor_compra * 0.07), round(valor_compra * 0.10)
        if valor_compra <= 500_000:
            c = round(valor_compra * 0.05)
            return c, c
        c = min(round(valor_compra * 0.04), 30_000)
        return c, c
    return None


# ---------------------------------------------------------------- sesión y almacén
@dataclass
class Sesion:
    cliente_id: str
    canal: str
    consentimiento: bool = False
    confirmacion_vigente: bool = False  # la decide el agente, no el modelo de lenguaje
    productos_ofrecidos: set = field(default_factory=set)
    alternativas_ofrecidas: int = 0
    despedida: bool = False


@dataclass
class Almacen:
    consentimientos: dict[str, Consentimiento] = field(default_factory=dict)
    leads: dict[str, Lead] = field(default_factory=dict)
    cotizaciones: dict[str, Cotizacion] = field(default_factory=dict)
    enlaces_pago: dict[str, dict] = field(default_factory=dict)
    citas: dict[str, Cita] = field(default_factory=dict)
    escalamientos: dict[str, Escalamiento] = field(default_factory=dict)
    resultados: list[Resultado] = field(default_factory=list)
    seguimientos: list[Seguimiento] = field(default_factory=list)
    sesiones: dict[str, Sesion] = field(default_factory=dict)

    def sesion(self, cliente_id: str, canal: str = "whatsapp") -> Sesion:
        if cliente_id not in self.sesiones:
            self.sesiones[cliente_id] = Sesion(cliente_id=cliente_id, canal=canal)
        return self.sesiones[cliente_id]
