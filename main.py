"""Chat de consola para probar a Lexa.   python main.py [--debug]"""
import argparse

import dspy

from lexa.agent import LexaAgent, configurar_lm


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--debug", action="store_true", help="muestra el estado interno y las herramientas usadas")
    args = ap.parse_args()

    configurar_lm()
    lexa = LexaAgent(cliente_id="cliente-consola", canal="consola")
    print("Lexa lista. Escribe 'salir' para terminar.\n")
    while True:
        texto = input("Tú: ").strip()
        if texto.lower() in {"salir", "exit"}:
            break
        if not texto:
            continue
        out = lexa(mensaje_cliente=texto)
        print(f"\nLexa: {out.respuesta}\n")
        if args.debug:
            print("[estado_interno]", out.estado_interno.model_dump_json(indent=2))
            dspy.inspect_history(n=6)


if __name__ == "__main__":
    main()
