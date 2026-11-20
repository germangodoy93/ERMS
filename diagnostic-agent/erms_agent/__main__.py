"""Console entry point of `erms-agente.exe`.

erms-agente.exe                      # asks for the code shown in ERMS
erms-agente.exe --server https://...  # another ERMS server (e.g. local tests)
"""

import argparse
import contextlib
import os
import sys

from erms_agent import VERSION, api, collect

DEFAULT_SERVER = "https://bubbly-upliftment-production-d22d405e.up.railway.app"

NOTICE = """\
Este programa recolecta SOLO información técnica del hardware de este equipo:
  - sistema operativo, fabricante, modelo y serial del equipo
  - procesador, memoria RAM y tarjeta de video
  - discos: modelo, capacidad, estado de salud y espacio libre
  - batería: capacidad de diseño, capacidad actual y ciclos
  - número de apagados inesperados y pantallazos azules de los últimos 30 días
  - con permisos de administrador: temperatura, desgaste y errores de los discos (SMART)

NO lee archivos, fotos, documentos, navegación, cuentas ni programas instalados.
NO borra, formatea ni cambia configuraciones o firmware.
Los datos se envían de forma cifrada solo a la orden de servicio indicada.
"""


def _pause() -> None:
    # Keeps the console window open when the .exe is launched with a double click.
    if sys.stdin and sys.stdin.isatty():
        with contextlib.suppress(EOFError):
            input("\nPresione Enter para salir...")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="erms-agente", description="Agente de diagnóstico ERMS")
    parser.add_argument("--server", default=os.environ.get("ERMS_SERVER", DEFAULT_SERVER))
    parser.add_argument("--code", help="Código de emparejamiento (si no, se pregunta)")
    parser.add_argument("--yes", action="store_true", help="Acepta el aviso sin preguntar")
    args = parser.parse_args(argv)
    # Windows consoles and redirected output may use a legacy code page: never crash on "→".
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")

    print(f"ERMS · Agente de diagnóstico {VERSION}\n")
    if not collect.running_on_windows():
        print("Este agente solo funciona en Windows.")
        return 2
    print(NOTICE)
    elevated = collect.is_elevated()
    if not elevated:
        print(
            "Sugerencia: para incluir SMART de los discos, cierre y ejecute el agente con "
            "clic derecho → 'Ejecutar como administrador'.\n"
        )
    if not args.yes and input("¿El cliente autoriza continuar? (S/N): ").strip().upper() != "S":
        print("Cancelado. No se recolectó ni se envió información.")
        return 1

    code = args.code or input("Código que muestra ERMS (ej. ABCD-1234): ").strip()
    try:
        session = api.pair(args.server, code)
    except api.ApiError as exc:
        print(f"\nNo se pudo vincular: {exc}")
        return 3
    print(f"\nOrden {session['work_order_number']} · {session['device']}")
    print("Recolectando información (puede tardar hasta un minuto)...")

    report = collect.collect(elevated=elevated, progress=lambda label: print(f"  - {label}"))
    try:
        result = api.send_report(args.server, session["token"], report)
    except api.ApiError as exc:
        print(f"\nNo se pudo enviar: {exc}")
        return 4

    missing = report.get("errors", {})
    print(f"\nListo: se registraron {result['results']} resultados en la orden.")
    if missing:
        print("Secciones que Windows no permitió leer: " + ", ".join(sorted(missing)))
    print("Puede cerrar esta ventana.")
    return 0


if __name__ == "__main__":
    exit_code = main()
    _pause()
    sys.exit(exit_code)
