"""LexaAgent: módulo de DSPy que orquesta una conversación completa.

Por turno:
  1. DetectarConfirmacion -> decide si las herramientas [REQUIERE_CONFIRMACION] pueden ejecutarse.
  2. dspy.ReAct(LexaVentas, tools=...) -> razona, usa herramientas y redacta la respuesta.
  3. Revisión de la respuesta (reglas del prompt) y reescritura si hace falta.
     (Se hace DESPUÉS de ReAct y no con dspy.Refine, porque Refine volvería a ejecutar
     herramientas con efectos: cotizaciones, citas, escalamientos.)
  4. ClasificarEstado -> bloque oculto para CRM/analítica.
"""
from typing import Optional

import dspy

from .config import SETTINGS
from .data import Almacen
from .models import EstadoInterno
from .prompts import detectar_violaciones
from .signatures import ClasificarEstado, DetectarConfirmacion, LexaVentas, ReescribirSegura
from .tools import crear_herramientas


class LexaAgent(dspy.Module):
    def __init__(self, almacen: Optional[Almacen] = None, cliente_id: str = "cliente-demo",
                 canal: str = "whatsapp", max_iters: int = SETTINGS.max_iters):
        super().__init__()
        self.almacen = almacen or Almacen()
        self.canal = canal
        self.sesion = self.almacen.sesion(cliente_id, canal)
        self.turnos: list[tuple[str, str]] = []

        self.react = dspy.ReAct(
            LexaVentas, tools=crear_herramientas(self.almacen, cliente_id, canal), max_iters=max_iters)
        self.detectar_confirmacion = dspy.Predict(DetectarConfirmacion)
        self.clasificar_estado = dspy.Predict(ClasificarEstado)
        self.reescribir = dspy.Predict(ReescribirSegura)

    # ------------------------------------------------------------------ utilidades
    def _contexto(self) -> str:
        from datetime import date

        partes = [f"Hoy es {date.today().isoformat()}.", f"Canal: {self.canal}."]
        if self.sesion.consentimiento:
            partes.append("El cliente ya autorizó el tratamiento de sus datos.")
        if self.sesion.alternativas_ofrecidas >= SETTINGS.max_alternativas:
            partes.append(
                f"ALERTA: ya ofreciste {self.sesion.alternativas_ofrecidas} alternativas. No ofrezcas más: "
                "despídete con gratitud y usa registrar_resultado.")
        return " ".join(partes)

    def _confirmo(self, mensaje: str) -> bool:
        if not self.turnos:
            return False
        ultima = self.turnos[-1][1]
        return bool(self.detectar_confirmacion(ultima_respuesta_lexa=ultima, mensaje_cliente=mensaje).confirma)

    def _revisar(self, respuesta: str) -> str:
        problemas = detectar_violaciones(respuesta, SETTINGS.max_emojis)
        if not problemas:
            return respuesta
        return self.reescribir(mensaje=respuesta, problemas=problemas).mensaje_corregido

    @staticmethod
    def _herramientas_usadas(trayectoria: dict) -> list[str]:
        return [v for k, v in trayectoria.items() if k.startswith("tool_name_") and v != "finish"]

    @staticmethod
    def _productos_vistos(trayectoria: dict) -> list[str]:
        ids = []
        for k, obs in trayectoria.items():
            if k.startswith("observation_") and isinstance(obs, list):
                ids += [i["producto_id"] for i in obs if isinstance(i, dict) and "producto_id" in i]
        return list(dict.fromkeys(ids))

    # ------------------------------------------------------------------ turno
    def forward(self, mensaje_cliente: str) -> dspy.Prediction:
        self.sesion.confirmacion_vigente = self._confirmo(mensaje_cliente)

        pred = self.react(mensaje_cliente=mensaje_cliente, historial=self._transcripcion(),
                          contexto=self._contexto())
        respuesta = self._revisar(pred.respuesta)

        estado = self.clasificar_estado(
            mensaje_cliente=mensaje_cliente, respuesta_lexa=respuesta,
            herramientas_usadas=self._herramientas_usadas(pred.trajectory),
            productos_consultados=self._productos_vistos(pred.trajectory),
            alternativas_previas=self.sesion.alternativas_ofrecidas)
        # alternativas = max(self.sesion.alternativas_ofrecidas,
        #                    min(int(estado.alternativas_ofrecidas), SETTINGS.max_alternativas + 1))
        # self.sesion.alternativas_ofrecidas = alternativas
        self.sesion.productos_ofrecidos.update(self._productos_vistos(pred.trajectory))
        alternativas = max(0, len(self.sesion.productos_ofrecidos) - 1)
        self.sesion.alternativas_ofrecidas = alternativas

        interno = EstadoInterno(
            etapa=estado.etapa, intencion_cliente=estado.intencion_cliente,
            tipo_objecion=estado.tipo_objecion, alternativas_ofrecidas=alternativas,
            productos_mencionados=estado.productos_mencionados, siguiente_accion=estado.siguiente_accion)

        self.turnos.append((mensaje_cliente, respuesta))
        return dspy.Prediction(respuesta=respuesta, estado_interno=interno, trajectory=pred.trajectory)

    def _transcripcion(self, ultimos: int = 8) -> str:
        if not self.turnos:
            return "(conversación nueva)"
        return "\n".join(f"Cliente: {c}\nLexa: {l}" for c, l in self.turnos[-ultimos:])


def configurar_lm(modelo: str = SETTINGS.modelo) -> None:
    """Configura el modelo de lenguaje global de DSPy (la clave va en ANTHROPIC_API_KEY)."""
    dspy.configure(lm=dspy.LM(modelo, temperature=SETTINGS.temperatura, max_tokens=1500))
