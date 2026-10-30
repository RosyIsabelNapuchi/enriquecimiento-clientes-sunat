"""Une SAP + SUNAT + ventas, marca problemas de calidad y mide el mercado por región (con foco en selva)."""
from __future__ import annotations

import pandas as pd

from .rubros import region_natural, rubro_ciiu, ruc_valido


def estado_comercial(ventas: pd.DataFrame, corte: str) -> pd.DataFrame:
    """Nuevo, recurrente, reactivado o perdido, mirando los 12 meses al corte y los 12 anteriores."""
    v = ventas.assign(p=pd.PeriodIndex(ventas.mes, freq="M"))
    c = pd.Period(corte, freq="M")
    ult = v[v.p > c - 12].groupby("ruc").venta_usd.sum()
    prev = v[(v.p > c - 24) & (v.p <= c - 12)].groupby("ruc").venta_usd.sum()
    antes = v[v.p <= c - 12].groupby("ruc").venta_usd.sum()
    out = v.groupby("ruc").agg(primera_venta=("p", "min"), ultima_venta=("p", "max"), venta_total=("venta_usd", "sum"))
    out["venta_12m"] = ult.reindex(out.index).fillna(0.0)
    out["venta_12m_previos"] = prev.reindex(out.index).fillna(0.0)

    def clasificar(r):
        if r.venta_12m == 0:
            return "PERDIDO"
        if r.name not in antes.index:
            return "NUEVO"
        return "RECURRENTE" if r.venta_12m_previos > 0 else "REACTIVADO"

    out["estado_comercial"] = out.apply(clasificar, axis=1)
    out[["primera_venta", "ultima_venta"]] = out[["primera_venta", "ultima_venta"]].astype(str)
    return out.reset_index()


def enriquecer(maestro: pd.DataFrame, sunat: pd.DataFrame, ventas: pd.DataFrame, corte: str) -> pd.DataFrame:
    m = maestro.copy()
    m["ruc"] = m.ruc.astype(str).str.strip()
    m["ruc_valido"] = m.ruc.map(ruc_valido)
    m["ruc_duplicado"] = m.ruc.duplicated(keep=False)
    s = sunat.rename(columns={"RUC": "ruc"})
    df = m.merge(s, on="ruc", how="left").merge(estado_comercial(ventas, corte), on="ruc", how="left")
    df["tiene_ficha"] = df.Consulta.eq("OK")
    df["departamento_final"] = df.Departamento.where(df.Departamento.fillna("").ne(""), df.departamento.str.upper())
    df["provincia_final"] = df.Provincia.where(df.Provincia.fillna("").ne(""), df.provincia.str.upper())
    df["region"] = [region_natural(d, p) for d, p in zip(df.departamento_final.fillna(""), df.provincia_final.fillna(""))]
    df["direccion_sap_desactualizada"] = df.tiene_ficha & df.departamento.str.upper().ne(df.Departamento)
    df["rubro"] = df.CIIU.map(rubro_ciiu)
    df["alerta_credito"] = df.tiene_ficha & (df.Estado.ne("ACTIVO") | df.Condicion.ne("HABIDO")) & (df.saldo > 0)
    return df


def calidad(df: pd.DataFrame) -> pd.Series:
    return pd.Series({
        "clientes": len(df),
        "ruc_con_digito_invalido": int((~df.ruc_valido).sum()),
        "ruc_duplicado_en_sap": int(df.ruc_duplicado.sum()),
        "sin_ficha_sunat": int((~df.tiene_ficha).sum()),
        "direccion_sap_distinta_a_sunat": int(df.direccion_sap_desactualizada.sum()),
        "baja_o_no_habido_con_saldo": int(df.alerta_credito.sum()),
    })


def mercado_por_region(df: pd.DataFrame, ventas: pd.DataFrame) -> pd.DataFrame:
    reg = df.drop_duplicates("ruc").set_index("ruc").region
    v = ventas.assign(region=ventas.ruc.map(reg).fillna("SIN UBICACIÓN"), anio=ventas.mes.str[:4].astype(int))
    tabla = v.groupby(["anio", "region"]).agg(venta_usd=("venta_usd", "sum"), clientes=("ruc", "nunique")).reset_index()
    tabla["participacion"] = tabla.venta_usd / tabla.groupby("anio").venta_usd.transform("sum")
    return tabla


def foco_selva(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    selva = df[df.region.eq("SELVA")].drop_duplicates("ruc")
    por_estado = selva.groupby("estado_comercial").agg(clientes=("ruc", "nunique"), venta_12m=("venta_12m", "sum"),
                                                      venta_12m_previos=("venta_12m_previos", "sum"))
    por_rubro = selva.groupby("rubro").agg(clientes=("ruc", "nunique"), venta_12m=("venta_12m", "sum")).sort_values(
        "venta_12m", ascending=False)
    por_depto = selva.groupby("departamento_final").agg(clientes=("ruc", "nunique"), venta_12m=("venta_12m", "sum"),
                                                       venta_12m_previos=("venta_12m_previos", "sum"))
    por_depto["crecimiento"] = por_depto.venta_12m / por_depto.venta_12m_previos.replace(0, float("nan")) - 1
    importadores = int((selva.EsImportador == "SI").sum())
    return {"por_estado": por_estado, "por_rubro": por_rubro, "por_departamento": por_depto.sort_values("venta_12m", ascending=False),
            "resumen": pd.DataFrame({"clientes_selva": [len(selva)], "importadores_directos": [importadores]})}
