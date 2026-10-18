"""Herramientas de Lexa (las del prompt v0.1), listas para dspy.ReAct.

Reglas de dspy.ReAct que se respetan aquí (tutorial customer_service_agent):
  1. Cada función tiene docstring que explica qué hace.
  2. Cada argumento tiene tipo, para que el modelo genere bien los parámetros.
  3. Los errores se lanzan con ValueError y un mensaje claro: ReAct se lo
     devuelve al modelo como observación para que se corrija o escale.

Decisiones propias:
  - `cliente_id` y `canal` NO los decide el modelo: se enlazan por sesión
    con una fábrica (closure). Menos parámetros, menos errores.
  - Las herramientas [REQUIERE_CONFIRMACION] no confían en el modelo: leen
    `sesion.confirmacion_vigente`, que el agente calcula con el mensaje real
    del cliente.
"""
from datetime import datetime, timedelta
from typing import Callable, Literal, Optional
import unicodedata


from .config import SETTINGS
from .data import (
    ALIADOS, DOMICILIO_ALIADOS, PRODUCTOS, ZONAS, Almacen, comision_lexa_interna, nuevo_id, DISTANCIAS_KM
)
from .models import (
    Cita, Consentimiento, Cotizacion, Escalamiento, ItemCotizacion, Lead,
    Resultado, Seguimiento,
)

_ASESOR_DEMO = "Asesor Nexa (por asignar)"  # DEMO: reemplazar por agenda real


def _ahora() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M")


def _validar_fecha(fecha: str) -> str:
    try:
        return datetime.fromisoformat(fecha).strftime("%Y-%m-%dT%H:%M")
    except ValueError:
        raise ValueError("Fecha inválida. Usa el formato AAAA-MM-DDTHH:MM, por ejemplo 2026-10-16T09:00.")


def crear_herramientas(almacen: Almacen, cliente_id: str, canal: str = "whatsapp") -> list[Callable]:
    sesion = almacen.sesion(cliente_id, canal)

    def _exigir_confirmacion(accion: str) -> None:
        if not sesion.confirmacion_vigente:
            raise ValueError(
                f"REQUIERE_CONFIRMACION: el cliente aún no ha confirmado '{accion}'. "
                "Resume lo que vas a hacer, pregúntale si está de acuerdo y termina el turno. "
                "No vuelvas a llamar esta herramienta hasta que él confirme."
            )

    # ------------------------------------------------------------ conocimiento
    def consultar_catalogo(
        consulta: str,
        tipo_cliente: Literal["persona", "empresa"] = "persona",
        presupuesto_max: Optional[int] = None,
        categoria: Optional[str] = None,
    ) -> list[dict]:
        """Busca productos y servicios del ecosistema Nexa según la necesidad, el tipo de cliente
        y el presupuesto máximo en pesos. Devuelve id, nombre, aliado, beneficios, precio y
        condiciones. Si devuelve una lista vacía, no inventes: ofrece un asesor humano."""
        palabras = [_normalizar(p) for p in consulta.split() if len(p) > 2]
        resultados = []
        for p in PRODUCTOS.values():
            if p.perfil_ideal not in ("ambos", tipo_cliente):
                continue
            if categoria and _normalizar(categoria) not in _normalizar(p.categoria):
                continue
            if presupuesto_max is not None and p.precio_cop is not None and p.precio_cop > presupuesto_max:
                continue
            texto = _normalizar(" ".join([p.nombre, p.categoria, ALIADOS[p.aliado_id].nombre, *p.beneficios]))
            puntaje = sum(1 for w in palabras if w in texto)
            if puntaje or not palabras:
                resultados.append((puntaje, p))
        resultados.sort(key=lambda t: -t[0])
        return [
            {**p.model_dump(), "aliado": ALIADOS[p.aliado_id].nombre}
            for _, p in resultados[:5]
        ]

    def consultar_aliado(aliado: str) -> dict:
        """Obtiene sector, servicios, requisitos y cobertura de un aliado de la red Nexa.
        Recibe el identificador o el nombre del aliado."""
        buscado = aliado.lower().strip()
        for a in ALIADOS.values():
            if buscado in (a.aliado_id, a.nombre.lower()) or buscado in a.nombre.lower():
                return a.model_dump()
        raise ValueError("No encontré ese aliado. Revisa el nombre o escala a un asesor.")

    def calcular_domicilio(aliado_id: str, sector_cliente: str) -> dict:
        """Calcula la tarifa de domicilio local y cuánto paga el cliente, según el aliado y el barrio,
        comuna o municipio del cliente. Si el sector no está en la tabla de distancias, NO estimes:
        ofrece un asesor que lo confirme."""
        if aliado_id not in DOMICILIO_ALIADOS:
            raise ValueError("Este aliado no tiene domicilio local con Nexa.")
        tabla = {_normalizar(k): v for k, v in DISTANCIAS_KM.get(aliado_id, {}).items()}
        distancia_km = tabla.get(_normalizar(sector_cliente))
        if distancia_km is None:
            raise ValueError("No tengo verificada la distancia a ese sector, así que no puedo dar el costo "
                             "del domicilio. Dile al cliente que un asesor se lo confirma. No estimes distancias.")
        aporte, habilitadas = DOMICILIO_ALIADOS[aliado_id]
        for zona, km_max, tarifa in ZONAS:
            if distancia_km <= km_max:
                if zona not in habilitadas:
                    raise ValueError("Esa distancia queda fuera de la cobertura de este aliado. Ofrece un asesor.")
                return {"zona": zona, "tarifa_total_cop": tarifa,
                        "paga_cliente_cop": max(tarifa - aporte, 0)}
        raise ValueError("Esa distancia queda fuera de la cobertura de domicilios. Ofrece un asesor.")

    # ------------------------------------------------------------ datos personales
    def registrar_consentimiento(acepta: bool) -> str:
        """Registra si el cliente autorizó el tratamiento de sus datos personales (Ley 1581 de 2012).
        Llámala solo después de haberle pedido la autorización y de que haya respondido."""
        almacen.consentimientos[cliente_id] = Consentimiento(
            cliente_id=cliente_id, canal=sesion.canal, fecha_hora=_ahora(), acepta=acepta)
        sesion.consentimiento = acepta
        return "Autorización registrada." if acepta else "El cliente no autorizó; no guardes sus datos."

    def gestionar_lead(
        nombre: str, contacto: str, tipo_cliente: Literal["persona", "empresa"],
        necesidad: str, productos_interes: list[str], etapa: str, notas: str = "",
    ) -> str:
        """Crea o actualiza el registro del cliente potencial en el CRM. Requiere que el cliente
        ya haya autorizado el tratamiento de sus datos."""
        if not sesion.consentimiento:
            raise ValueError("Falta la autorización de tratamiento de datos. Pídela y usa registrar_consentimiento.")
        almacen.leads[cliente_id] = Lead(
            cliente_id=cliente_id, nombre=nombre, contacto=contacto, tipo_cliente=tipo_cliente,
            necesidad=necesidad, productos_interes=productos_interes, etapa=etapa, notas=notas)
        return "Cliente potencial guardado."

    # ------------------------------------------------------------ acciones [REQUIERE_CONFIRMACION]
    def generar_cotizacion(productos: list[ItemCotizacion]) -> dict:
        """[REQUIERE_CONFIRMACION] Genera una cotización formal con precios y condiciones oficiales.
        Recibe la lista de productos con id y cantidad."""
        _exigir_confirmacion("generar la cotización")
        total, condiciones = 0, set()
        for it in productos:
            item = it if isinstance(it, ItemCotizacion) else ItemCotizacion(**it)
            prod = PRODUCTOS.get(item.producto_id)
            if prod is None:
                raise ValueError(f"El producto {item.producto_id} no existe en el catálogo.")
            if prod.precio_cop is None:
                raise ValueError(f"{prod.nombre} no tiene precio fijo: conecta al cliente con un asesor.")
            total += prod.precio_cop * item.cantidad
            if prod.condiciones:
                condiciones.add(prod.condiciones)
        cot = Cotizacion(
            cotizacion_id=nuevo_id("COT"), cliente_id=cliente_id,
            items=[i if isinstance(i, ItemCotizacion) else ItemCotizacion(**i) for i in productos],
            total_cop=total, condiciones=" ".join(sorted(condiciones)),
            vigencia=(datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d"))  # DEMO: definir vigencia real
        almacen.cotizaciones[cot.cotizacion_id] = cot
        return cot.model_dump()

    def generar_enlace_pago(cotizacion_id: str, medio_pago: str) -> dict:
        """[REQUIERE_CONFIRMACION] Genera un enlace de pago seguro para una cotización ya creada.
        SIMULADO en esta versión: conectar a la pasarela de pagos real."""
        _exigir_confirmacion("generar el enlace de pago")
        if cotizacion_id not in almacen.cotizaciones:
            raise ValueError("No encuentro esa cotización. Genera primero la cotización.")
        enlace = {"url_pago": f"https://pagos.nexa.example/{nuevo_id('PAGO')}",
                  "fecha_expiracion": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M"),
                  "medio_pago": medio_pago}
        almacen.enlaces_pago[cotizacion_id] = enlace
        return enlace

    def agendar_cita(
        tipo: Literal["asesoria", "demo", "cierre", "postventa"],
        fecha_hora_preferida: str, modalidad: str, tema: str,
    ) -> dict:
        """[REQUIERE_CONFIRMACION] Agenda una reunión con un asesor humano o un aliado.
        La fecha va en formato AAAA-MM-DDTHH:MM."""
        _exigir_confirmacion("agendar la cita")
        cita = Cita(cita_id=nuevo_id("CITA"), cliente_id=cliente_id, tipo=tipo,
                    fecha_hora=_validar_fecha(fecha_hora_preferida), modalidad=modalidad,
                    tema=tema, asesor=_ASESOR_DEMO)
        almacen.citas[cita.cita_id] = cita
        return cita.model_dump()

    def enviar_propuesta(canal_envio: Literal["correo", "whatsapp"], mensaje_personalizado: str,
                         cotizacion_id: Optional[str] = None) -> str:
        """[REQUIERE_CONFIRMACION] Envía al cliente un resumen o propuesta por correo o WhatsApp.
        SIMULADO en esta versión: conectar a Gmail / WhatsApp."""
        _exigir_confirmacion("enviar la propuesta")
        if cotizacion_id and cotizacion_id not in almacen.cotizaciones:
            raise ValueError("No encuentro esa cotización.")
        return f"Propuesta enviada por {canal_envio}."

    # ------------------------------------------------------------ cierre y escalamiento
    def escalar_a_asesor(motivo: str, resumen_conversacion: str,
                         prioridad: Literal["baja", "media", "alta"] = "media") -> str:
        """Transfiere la conversación a un asesor humano con el contexto completo. Úsala si el cliente
        lo pide, si hay una queja o un tema legal o financiero, si se necesita un descuento fuera de
        política o si no tienes la información para responder con certeza."""
        esc = Escalamiento(escalamiento_id=nuevo_id("ESC"), cliente_id=cliente_id, motivo=motivo,
                           resumen_conversacion=resumen_conversacion, prioridad=prioridad)
        almacen.escalamientos[esc.escalamiento_id] = esc
        return f"Conversación transferida a un asesor ({esc.escalamiento_id})."

    def registrar_resultado(
        resultado: Literal["venta", "cita", "seguimiento", "rechazo", "sin_ajuste"],
        alternativas_ofrecidas: int = 0, motivo_rechazo: Optional[str] = None,
        fecha_seguimiento: Optional[str] = None,
    ) -> str:
        """Registra el cierre de la conversación para analítica y seguimiento. Úsala al despedirte."""
        almacen.resultados.append(Resultado(
            cliente_id=cliente_id, resultado=resultado, motivo_rechazo=motivo_rechazo,
            alternativas_ofrecidas=alternativas_ofrecidas, fecha_seguimiento=fecha_seguimiento))
        if resultado in ("rechazo", "sin_ajuste"):
            sesion.despedida = True
        return "Resultado registrado."

    def programar_seguimiento(fecha: str, canal_contacto: str, motivo: str, autorizado_por_cliente: bool) -> str:
        """Programa un recordatorio de contacto futuro. Solo si el cliente lo autorizó expresamente."""
        if not autorizado_por_cliente:
            raise ValueError("No programes seguimientos sin autorización del cliente.")
        almacen.seguimientos.append(Seguimiento(
            cliente_id=cliente_id, fecha=_validar_fecha(fecha), canal=canal_contacto, motivo=motivo))
        return "Seguimiento programado."

    return [
        consultar_catalogo, consultar_aliado, calcular_domicilio, registrar_consentimiento,
        gestionar_lead, generar_cotizacion, generar_enlace_pago, agendar_cita,
        enviar_propuesta, escalar_a_asesor, registrar_resultado, programar_seguimiento,
    ]

    
def _normalizar(texto: str) -> str:
    """Minúsculas y sin tildes, para que 'automático' y 'automatico' coincidan."""
    d = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in d if unicodedata.category(c) != "Mn")