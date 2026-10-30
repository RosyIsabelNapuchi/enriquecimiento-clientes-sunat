"""Pipeline: SAP (simulado en DuckDB) → fichas SUNAT → enriquecimiento → calidad → mercado por región.

Uso:  python run.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "src"))

from enriquecimiento.analisis import calidad, enriquecer, foco_selva, mercado_por_region  # noqa: E402
from enriquecimiento.graficos import figuras  # noqa: E402
from enriquecimiento.sap import direccion_principal, render_query, run_query  # noqa: E402
from enriquecimiento.sunat_scraper import consultar_lote  # noqa: E402
from enriquecimiento.synthetic import make_data  # noqa: E402

CORTE = "2026-09"
DATA, OUT = ROOT / "data", ROOT / "reports"


def sap_demo(tablas: dict[str, pd.DataFrame], esquema: str = "SBO_DEMO") -> duckdb.DuckDBPyConnection:
    """Base DuckDB con la MISMA estructura de tablas de SAP B1, para ejecutar la consulta real sin un SAP."""
    con = duckdb.connect()
    con.execute(f'CREATE SCHEMA "{esquema}"')
    for nombre, df in tablas.items():
        df = df.copy()
        for c in df.columns:                              # duckdb no acepta numpy.str_ dentro de columnas object
            if not pd.api.types.is_numeric_dtype(df[c]):
                df[c] = pd.Series([None if pd.isna(x) else str(x) for x in df[c]], index=df.index, dtype=object)
        con.register("tmp", df)
        con.execute(f'CREATE TABLE "{esquema}".{nombre} AS SELECT * FROM tmp')
        con.unregister("tmp")
    return con


def main() -> None:
    OUT.mkdir(exist_ok=True)
    data = make_data()
    tablas = {k: data[k] for k in ("OCRD", "CRD1", "OSLP", "OCRG", "OCST", "OCRY")}
    data["ventas"].to_csv(DATA / "ventas_mensuales_por_ruc.csv", index=False)

    # 1) SAP: la misma consulta SQL que en producción, sobre la base de demostración
    maestro_full = run_query(sap_demo(tablas), render_query("SBO_DEMO"))
    maestro_full.to_csv(DATA / "maestro_clientes_sap.csv", index=False)
    maestro = direccion_principal(maestro_full)

    # 2) SUNAT: mismo flujo de consulta con avance guardado; aquí el "navegador" lee fichas de ejemplo
    progreso = DATA / "sunat_progreso.csv"
    progreso.unlink(missing_ok=True)
    sunat = consultar_lote(maestro.ruc.drop_duplicates(), fetch=data["fichas"].get, progreso=progreso, pausa=0)

    # 3) Enriquecimiento y análisis
    df = enriquecer(maestro, sunat, data["ventas"], CORTE)
    df.to_csv(OUT / "clientes_enriquecidos.csv", index=False)
    cal = calidad(df)
    cal.to_csv(OUT / "calidad_de_datos.csv", header=["valor"])
    mercado = mercado_por_region(df, data["ventas"])
    mercado.to_csv(OUT / "mercado_por_region.csv", index=False)
    selva = foco_selva(df)
    for nombre, tabla in selva.items():
        tabla.to_csv(OUT / f"selva_{nombre}.csv")
    figuras(mercado, selva, cal, OUT / "figures")

    pd.set_option("display.width", 200)
    print("=== Calidad de datos ===\n", cal.to_string())
    print("\n=== Participación de la selva en la venta ===\n",
          mercado[mercado.region == "SELVA"][["anio", "venta_usd", "clientes", "participacion"]].round(3).to_string(index=False))
    for nombre in ("por_estado", "por_departamento", "por_rubro"):
        print(f"\n=== Selva {nombre} ===\n", selva[nombre].round(2).to_string())


if __name__ == "__main__":
    main()
