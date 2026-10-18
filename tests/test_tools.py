"""Pruebas de las herramientas (no llaman al modelo de lenguaje). Las pruebas con el modelo se definirán después."""
import pytest

from lexa.data import Almacen, DISTANCIAS_KM, comision_lexa_interna
from lexa.prompts import detectar_violaciones
from lexa.tools import crear_herramientas


@pytest.fixture
def ctx():
    almacen = Almacen()
    herramientas = {f.__name__: f for f in crear_herramientas(almacen, "c1")}
    return almacen, herramientas, almacen.sesion("c1")


def test_catalogo_filtra_por_presupuesto(ctx):
    _, h, _ = ctx
    assert any(p["producto_id"] == "ELEC-001" for p in h["consultar_catalogo"]("ducha eléctrica"))
    assert h["consultar_catalogo"]("ducha eléctrica", presupuesto_max=50_000) == []


def test_lead_exige_consentimiento(ctx):
    _, h, _ = ctx
    args = dict(nombre="Ana", contacto="300", tipo_cliente="persona", necesidad="arriendo",
                productos_interes=["LIV-001"], etapa="descubrir")
    with pytest.raises(ValueError):
        h["gestionar_lead"](**args)
    h["registrar_consentimiento"](True)
    assert "guardado" in h["gestionar_lead"](**args)


def test_cotizacion_exige_confirmacion_del_cliente(ctx):
    _, h, sesion = ctx
    items = [{"producto_id": "ELEC-001", "cantidad": 2}]
    with pytest.raises(ValueError, match="REQUIERE_CONFIRMACION"):
        h["generar_cotizacion"](items)
    sesion.confirmacion_vigente = True
    cot = h["generar_cotizacion"](items)
    assert cot["total_cop"] == 188_000
    assert "url_pago" in h["generar_enlace_pago"](cot["cotizacion_id"], "PSE")


def test_cotizacion_sin_precio_se_rechaza(ctx):
    _, h, sesion = ctx
    sesion.confirmacion_vigente = True
    with pytest.raises(ValueError):
        h["generar_cotizacion"]([{"producto_id": "LIV-001"}])


def test_domicilio_segun_propuestas(ctx, monkeypatch):
    monkeypatch.setitem(DISTANCIAS_KM, "prismaticos", {"cerca": 2, "lejos": 6})
    monkeypatch.setitem(DISTANCIAS_KM, "tienda_electrico", {"medio": 6})
    _, h, _ = ctx
    assert h["calcular_domicilio"]("prismaticos", "cerca")["paga_cliente_cop"] == 3_400
    assert h["calcular_domicilio"]("tienda_electrico", "medio")["paga_cliente_cop"] == 9_400
    with pytest.raises(ValueError):
        h["calcular_domicilio"]("prismaticos", "lejos")  # zona C no habilitada
    with pytest.raises(ValueError):
        h["calcular_domicilio"]("prismaticos", "sector desconocido") # calcular recargo x Km adicional


def test_comision_interna_coincide_con_propuesta():
    # Ejemplos de la propuesta: usted paga comisión + aporte de 4.500
    assert comision_lexa_interna("tienda_electrico", 700_000) == (28_000, 28_000)
    assert comision_lexa_interna("tienda_electrico", 2_000_000) == (30_000, 30_000)  # tope
    assert comision_lexa_interna("prismaticos", 100_000) == (9_000, 9_000)


def test_escalar_y_resultado(ctx):
    almacen, h, sesion = ctx
    h["escalar_a_asesor"]("queja", "resumen")
    assert len(almacen.escalamientos) == 1
    h["registrar_resultado"]("sin_ajuste", alternativas_ofrecidas=2)
    assert sesion.despedida


def test_revision_de_respuesta():
    assert "presión comercial" in detectar_violaciones("¡Última oportunidad, no te lo pierdas!")
    assert detectar_violaciones("Con gusto te cuento cómo funciona.") == []
