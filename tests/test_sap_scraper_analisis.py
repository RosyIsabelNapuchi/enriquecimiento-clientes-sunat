import pandas as pd
import pytest

from enriquecimiento.analisis import estado_comercial
from enriquecimiento.sap import direccion_principal, render_query, run_query
from enriquecimiento.sunat_scraper import consultar_lote
from enriquecimiento.synthetic import make_data
from run import sap_demo


def test_render_query_bloquea_inyeccion():
    assert '"SBO_DEMO".OCRD' in render_query("SBO_DEMO")
    with pytest.raises(ValueError):
        render_query('X"; DROP TABLE OCRD; --')


def test_consulta_sap_real_sobre_tablas_demo():
    data = make_data(n=40)
    tablas = {k: data[k] for k in ("OCRD", "CRD1", "OSLP", "OCRG", "OCST", "OCRY")}
    df = run_query(sap_demo(tablas), render_query("SBO_DEMO"))
    assert {"codigo_cliente", "ruc", "departamento", "direccion_completa", "direccion_predeterminada"} <= set(df.columns)
    assert len(df) == 2 * len(data["OCRD"])                        # una fila por dirección (facturación + entrega)
    principal = direccion_principal(df)
    assert principal.codigo_cliente.is_unique
    assert (principal.tipo_direccion == "FACTURACION").all()


def test_scraper_guarda_avance_y_retoma(tmp_path):
    progreso = tmp_path / "progreso.csv"
    llamadas = []
    fichas = {"20999000011": "Número de RUC:\n20999000011 - EMPRESA UNO S.A.C.", "20999000022": None}

    def fetch(ruc):
        llamadas.append(ruc)
        if fichas.get(ruc) is None:
            raise TimeoutError("sin respuesta")
        return fichas[ruc]

    r1 = consultar_lote(list(fichas), fetch, progreso, pausa=0, reintentos=2)
    assert dict(zip(r1.RUC, r1.Consulta)) == {"20999000011": "OK", "20999000022": "ERROR"}
    llamadas.clear()
    fichas["20999000022"] = "Número de RUC:\n20999000022 - EMPRESA DOS S.A."
    r2 = consultar_lote(list(fichas), fetch, progreso, pausa=0)
    assert llamadas == ["20999000022"]                              # no repite lo que ya estaba OK
    assert set(r2.Consulta) == {"OK"}


def test_estado_comercial():
    v = pd.DataFrame({"ruc": ["A", "A", "B", "C", "D", "D"],
                      "mes": ["2025-03", "2026-05", "2026-03", "2024-01", "2023-01", "2026-02"],
                      "venta_usd": [10, 10, 10, 10, 10, 10]})
    e = estado_comercial(v, "2026-09").set_index("ruc").estado_comercial
    assert e["B"] == "NUEVO" and e["C"] == "PERDIDO" and e["D"] == "REACTIVADO" and e["A"] == "RECURRENTE"
