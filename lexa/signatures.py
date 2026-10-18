"""Signatures de DSPy: qué entra y qué sale en cada paso del agente."""
from typing import Literal

import dspy

from .prompts import INSTRUCCIONES_LEXA


class LexaVentas(dspy.Signature):
    """Placeholder: las instrucciones reales se inyectan abajo con with_instructions."""

    mensaje_cliente: str = dspy.InputField(desc="Último mensaje escrito por el cliente")
    historial: str = dspy.InputField(desc="Transcripción de los turnos anteriores: 'Cliente: ...' y 'Lexa: ...'")
    contexto: str = dspy.InputField(desc="Fecha, canal y alertas internas (por ejemplo, límite de alternativas)")
    respuesta: str = dspy.OutputField(desc="Mensaje final para el cliente, breve, cálido y veraz")


LexaVentas = LexaVentas.with_instructions(INSTRUCCIONES_LEXA)


class DetectarConfirmacion(dspy.Signature):
    """Decide si el cliente acaba de aceptar de forma clara y explícita lo que Lexa le propuso en su
    último mensaje (pagar, agendar, recibir la propuesta). Un 'tal vez', una duda o una pregunta NO es confirmar."""

    ultima_respuesta_lexa: str = dspy.InputField()
    mensaje_cliente: str = dspy.InputField()
    confirma: bool = dspy.OutputField()


class ClasificarEstado(dspy.Signature):
    """Clasifica el estado comercial del turno para el CRM. Este bloque nunca lo ve el cliente.
    Usa listo_para_comprar solo si el cliente pidió pagar, cotizar o agendar. Si se escaló a un asesor por falta de opciones, la etapa es despedida y la intención es objecion
    """

    mensaje_cliente: str = dspy.InputField()
    respuesta_lexa: str = dspy.InputField()
    herramientas_usadas: list[str] = dspy.InputField()
    productos_consultados: list[str] = dspy.InputField(desc="Ids de productos que Lexa consultó en este turno")
    alternativas_previas: int = dspy.InputField(desc="Alternativas ofrecidas antes de este turno")
    etapa: Literal["conectar", "descubrir", "proponer", "objecion", "cierre", "postventa", "despedida"] = dspy.OutputField()
    intencion_cliente: Literal["exploracion", "interes", "objecion", "listo_para_comprar", "rechazo_definitivo"] = dspy.OutputField()
    tipo_objecion: Literal["precio", "tiempo", "confianza", "necesidad", "competencia", "autoridad", "ninguna"] = dspy.OutputField()
    alternativas_ofrecidas: int = dspy.OutputField(desc="Total acumulado, contando las de este turno")
    productos_mencionados: list[str] = dspy.OutputField(desc="Ids de producto mencionados, por ejemplo ELEC-001")
    siguiente_accion: str = dspy.OutputField(desc="Frase corta con el siguiente paso")


class ReescribirSegura(dspy.Signature):
    """Reescribe el mensaje corrigiendo SOLO los problemas indicados, sin cambiar hechos, cifras ni la
    intención. Mantén el tono cercano y un máximo de 4 frases."""

    mensaje: str = dspy.InputField()
    problemas: list[str] = dspy.InputField()
    mensaje_corregido: str = dspy.OutputField()
