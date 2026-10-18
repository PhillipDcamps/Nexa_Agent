# Lexa · agente comercial de Sistema Nexa (DSPy)

Primera versión del agente, construida con `dspy.ReAct` siguiendo el tutorial *customer_service_agent*.

## Estructura
| Archivo | Qué contiene | Equivale en el tutorial a |
|---|---|---|
| `lexa/models.py` | Modelos pydantic (aliado, producto, lead, cotización, cita…) | "Define Data Structure" |
| `lexa/data.py` | Almacén en memoria + datos de demostración (aliados, catálogo, tarifas) | "Create Dummy Data" |
| `lexa/tools.py` | 12 herramientas con docstring y tipos | "Define the Tools" |
| `lexa/prompts.py` | Instrucciones de Lexa (prompt v0.1) y reglas de revisión | docstring de la Signature |
| `lexa/signatures.py` | `LexaVentas`, `DetectarConfirmacion`, `ClasificarEstado`, `ReescribirSegura` | "Create ReAct Agent" |
| `lexa/agent.py` | `LexaAgent(dspy.Module)`: un turno completo | `dspy.ReAct(...)` |
| `main.py` | Chat de consola (`--debug` muestra estado interno y prompts) | "Use the Agent" |
| `tests/test_tools.py` | Pruebas sin modelo de lenguaje | — |

## Uso
```bash
pip install -r requirements.txt
cp .env.example .env      # poner ANTHROPIC_API_KEY
python -m pytest -q       # herramientas, sin costo
python main.py --debug
```

## Decisiones de diseño
1. **`cliente_id` y `canal` se enlazan por sesión**, no los decide el modelo.
2. **Confirmación real**: las herramientas `[REQUIERE_CONFIRMACION]` leen una bandera que calcula `DetectarConfirmacion` con el mensaje del cliente, no un parámetro que el modelo pueda poner en `True`.
3. **Consentimiento** (Ley 1581): `gestionar_lead` falla si no hay autorización registrada.
4. **Revisión de la respuesta después de ReAct**, no con `dspy.Refine` (repetiría herramientas con efectos).
5. **Comisiones**: `comision_lexa_interna` existe para analítica y nunca se expone al modelo, porque el prompt prohíbe revelarlas.
6. **Estado interno** (`EstadoInterno`) sale aparte de `respuesta`; la plataforma nunca lo mezcla con el mensaje al cliente.

## Pendientes antes de producción
- Reemplazar datos DEMO: catálogo real (Prismáticos no tiene productos cargados), vigencia de cotización, agenda de asesores, umbral de venta corporativa.
- Conectar `generar_enlace_pago` y `enviar_propuesta` (hoy simulados) y persistir el almacén (CRM / base de datos).
- Alinear carpetas y nombres con el repositorio `dspy-test-agent`.
- Definir conjunto de pruebas con el modelo y métrica para optimizar con GEPA/MIPROv2.
