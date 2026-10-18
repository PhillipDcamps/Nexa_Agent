from lexa.agent import LexaAgent


def test_productos_vistos_extrae_ids_unicos_de_observaciones():
    trayectoria = {
        "observation_0": [
            {"producto_id": "ELEC-001"},
            {"producto_id": "LIV-001"},
            {"producto_id": "ELEC-001"},
            "dato no estructurado",
        ],
        "observation_1": [{"nombre": "sin id"}],
        "observation_2": "no es una lista",
        "tool_name_0": "consultar_catalogo",
    }

    assert LexaAgent._productos_vistos(trayectoria) == ["ELEC-001", "LIV-001"]
