"""Extracción del maestro de clientes desde SAP Business One (HANA) sin credenciales ni rutas en el código."""
from __future__ import annotations

import os
import re
from pathlib import Path

import pandas as pd

SQL_PATH = Path(__file__).parents[2] / "sql" / "maestro_clientes_sap_b1.sql"


def render_query(schema: str, path: Path = SQL_PATH) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_]+", schema or ""):
        raise ValueError("Nombre de esquema inválido (solo letras, números y guion bajo)")
    return path.read_text(encoding="utf-8").replace("{ESQUEMA}", schema)


def run_query(connection, sql: str) -> pd.DataFrame:
    """Funciona con cualquier conexión DB-API (hdbcli en producción, DuckDB en las pruebas)."""
    cursor = connection.cursor()
    try:
        cursor.execute(sql)
        columns = [d[0] for d in cursor.description]
        return pd.DataFrame(cursor.fetchall(), columns=columns)
    finally:
        cursor.close()


def connect_hana():                                     # pragma: no cover - requiere un SAP real
    """Credenciales desde variables de entorno (SAP_HOST, SAP_PORT, SAP_USER, SAP_PASSWORD)."""
    from hdbcli import dbapi

    return dbapi.connect(address=os.environ["SAP_HOST"], port=int(os.getenv("SAP_PORT", "30015")),
                         user=os.environ["SAP_USER"], password=os.environ["SAP_PASSWORD"])


def direccion_principal(maestro: pd.DataFrame) -> pd.DataFrame:
    """Una fila por cliente: la dirección de facturación predeterminada (o la primera disponible)."""
    orden = maestro.assign(
        _p=(maestro.tipo_direccion.eq("FACTURACION") & maestro.direccion_predeterminada.eq("SI")).astype(int) * 2
           + maestro.tipo_direccion.eq("FACTURACION").astype(int))
    return (orden.sort_values(["codigo_cliente", "_p"], ascending=[True, False])
                 .drop_duplicates("codigo_cliente").drop(columns="_p").reset_index(drop=True))
