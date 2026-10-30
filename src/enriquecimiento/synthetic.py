"""Datos SINTÉTICOS: tablas estilo SAP Business One, ventas mensuales por cliente y fichas SUNAT en texto.

Los RUC son ficticios (rango 20999…), las razones sociales son inventadas y se siembran errores de
calidad a propósito: RUC con dígito verificador incorrecto, RUC duplicado, dirección de SAP distinta a la
de SUNAT, contribuyentes con baja o "no habido", y RUC sin ficha.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .rubros import con_digito

DEPTOS = {  # departamento: (peso, provincias)
    "LIMA": (.42, ["LIMA", "HUAURA", "CAÑETE"]), "CALLAO": (.06, ["CALLAO"]), "AREQUIPA": (.07, ["AREQUIPA", "ISLAY"]),
    "LA LIBERTAD": (.06, ["TRUJILLO"]), "PIURA": (.06, ["PIURA", "PAITA", "SULLANA"]), "ANCASH": (.05, ["SANTA", "HUARAZ"]),
    "CUSCO": (.03, ["CUSCO", "LA CONVENCION"]), "JUNIN": (.04, ["HUANCAYO", "SATIPO", "CHANCHAMAYO"]),
    "CAJAMARCA": (.03, ["CAJAMARCA", "JAEN"]), "PUNO": (.02, ["PUNO"]), "MOQUEGUA": (.02, ["ILO", "MARISCAL NIETO"]),
    "LORETO": (.03, ["MAYNAS", "ALTO AMAZONAS"]), "UCAYALI": (.02, ["CORONEL PORTILLO"]),
    "SAN MARTIN": (.02, ["SAN MARTIN", "MOYOBAMBA"]), "MADRE DE DIOS": (.01, ["TAMBOPATA"]), "AMAZONAS": (.01, ["BAGUA"]),
}
CIIU = [("0311", "PESCA MARITIMA"), ("0322", "ACUICULTURA DE AGUA DULCE"), ("0729", "EXTRACCION DE OTROS MINERALES METALIFEROS NO FERROSOS"),
        ("0610", "EXTRACCION DE PETROLEO CRUDO"), ("1020", "ELABORACION Y CONSERVACION DE PESCADO"), ("1610", "ASERRADO Y ACEPILLADURA DE MADERA"),
        ("2511", "FABRICACION DE PRODUCTOS METALICOS PARA USO ESTRUCTURAL"), ("4100", "CONSTRUCCION DE EDIFICIOS"),
        ("4290", "CONSTRUCCION DE OTRAS OBRAS DE INGENIERIA CIVIL"), ("4659", "VENTA AL POR MAYOR DE OTROS TIPOS DE MAQUINARIA Y EQUIPO"),
        ("4923", "TRANSPORTE DE CARGA POR CARRETERA"), ("0126", "CULTIVO DE FRUTOS OLEAGINOSOS"), ("3510", "GENERACION, TRANSMISION Y DISTRIBUCION DE ENERGIA ELECTRICA"),
        ("7110", "ACTIVIDADES DE ARQUITECTURA E INGENIERIA")]
SELVA_CIIU = ["0322", "1610", "0126", "0610", "4923", "4659", "4100"]
PREFIJOS = ["Inversiones", "Corporación", "Servicios", "Comercial", "Industrias", "Agroindustrial", "Transportes", "Constructora"]
NUCLEOS = ["Amazonía", "Río Verde", "Cumbre", "Horizonte", "Huallaga", "Pacífico", "Altiplano", "Mantaro", "Ucayali Norte",
           "Selva Viva", "Los Cedros", "Tres Ríos", "Andes", "Cóndor", "Marañón", "Bahía", "Sol Naciente", "Puerto Alegre"]
SUFIJOS = ["S.A.C.", "S.A.", "E.I.R.L.", "S.R.L."]


def make_data(n: int = 260, seed: int = 21) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    deptos = list(DEPTOS)
    pesos = np.array([DEPTOS[d][0] for d in deptos])
    clientes = []
    for i in range(n):
        depto = rng.choice(deptos, p=pesos / pesos.sum())
        prov = rng.choice(DEPTOS[depto][1])
        selva = depto in {"LORETO", "UCAYALI", "SAN MARTIN", "MADRE DE DIOS", "AMAZONAS"} or prov in {"SATIPO", "CHANCHAMAYO", "LA CONVENCION", "JAEN"}
        ciiu = rng.choice(SELVA_CIIU) if selva and rng.random() < .7 else CIIU[rng.integers(len(CIIU))][0]
        nombre = f"{rng.choice(PREFIJOS)} {rng.choice(NUCLEOS)} {rng.choice(SUFIJOS)}".upper()
        ruc = con_digito("20999" + f"{rng.integers(0, 10**5):05d}")
        clientes.append({"CardCode": f"C{i + 1:05d}", "CardName": nombre, "LicTradNum": ruc, "depto": depto,
                         "prov": prov, "ciiu": ciiu})
    cl = pd.DataFrame(clientes).drop_duplicates("LicTradNum").reset_index(drop=True)
    # --- errores sembrados
    cl.loc[3, "LicTradNum"] = cl.loc[3, "LicTradNum"][:-1] + str((int(cl.loc[3, "LicTradNum"][-1]) + 1) % 10)  # dígito mal
    dup = cl.iloc[[10]].copy()
    dup["CardCode"] = "C99001"                                                     # mismo RUC con dos códigos
    cl = pd.concat([cl, dup], ignore_index=True)

    ocrd = pd.DataFrame({
        "CardCode": cl.CardCode, "CardName": cl.CardName, "LicTradNum": cl.LicTradNum, "CardType": "C",
        "Phone1": [f"01-{rng.integers(2000000, 7999999)}" for _ in range(len(cl))], "E_Mail": "",
        "GroupCode": rng.choice([100, 101, 102], len(cl)), "SlpCode": rng.choice([1, 2, 3, 4], len(cl)), "Currency": "USD",
        "Balance": np.round(rng.gamma(1.2, 8000, len(cl)), 2), "CreditLine": rng.choice([0, 20000, 50000, 100000], len(cl)),
        "validFor": np.where(rng.random(len(cl)) < .92, "Y", "N"), "BillToDef": "FISCAL", "ShipToDef": "ALMACEN"})
    estados = {d: f"{i + 1:02d}" for i, d in enumerate(DEPTOS)}
    crd1 = []
    for r in cl.itertuples():
        depto_sap = r.depto
        if rng.random() < .07:                                                     # dirección desactualizada en SAP
            depto_sap = "LIMA" if r.depto != "LIMA" else "CALLAO"
        crd1.append((r.CardCode, "B", "FISCAL", f"AV. PRINCIPAL {rng.integers(100, 999)}", "", r.prov if depto_sap == r.depto else "LIMA",
                     r.prov if depto_sap == r.depto else "LIMA", estados[depto_sap], "PE"))
        crd1.append((r.CardCode, "S", "ALMACEN", f"CALLE {rng.integers(1, 99)}", "", "LIMA", "LIMA", estados["LIMA"], "PE"))
    crd1 = pd.DataFrame(crd1, columns=["CardCode", "AdresType", "Address", "Street", "StreetNo", "City", "County", "State", "Country"])
    tablas = {
        "OCRD": ocrd, "CRD1": crd1,
        "OSLP": pd.DataFrame({"SlpCode": [1, 2, 3, 4], "SlpName": ["Vendedor Norte", "Vendedor Sur", "Vendedor Lima", "Vendedor Oriente"]}),
        "OCRG": pd.DataFrame({"GroupCode": [100, 101, 102], "GroupName": ["Corporativo", "Mediana empresa", "Pequeña empresa"]}),
        "OCST": pd.DataFrame({"Code": list(estados.values()), "Country": "PE", "Name": list(estados)}),
        "OCRY": pd.DataFrame({"Code": ["PE"], "Name": ["Perú"]}),
    }

    # --- fichas SUNAT (texto, como se ve en la consulta web)
    fichas = {}
    nombres_ciiu = dict(CIIU)
    for r in cl.drop_duplicates("LicTradNum").itertuples():
        if rng.random() < .04:
            continue                                                               # sin ficha
        estado, condicion = "ACTIVO", "HABIDO"
        u = rng.random()
        if u < .05:
            estado = "BAJA DE OFICIO"
        elif u < .10:
            condicion = "NO HABIDO"
        comex = "IMPORTADOR/EXPORTADOR" if rng.random() < .25 else "SIN ACTIVIDAD"
        fichas[r.LicTradNum] = "\n".join([
            "Resultado de la Búsqueda", "Número de RUC:", f"{r.LicTradNum} - {r.CardName}", "Tipo Contribuyente:",
            "SOCIEDAD ANONIMA CERRADA", "Nombre Comercial:", "-", "Fecha de Inscripción:", f"{rng.integers(1, 28):02d}/03/{rng.integers(1995, 2020)}",
            "Fecha de Inicio de Actividades:", "01/04/2005", "Estado del Contribuyente:", estado, "Condición del Contribuyente:", condicion,
            "Domicilio Fiscal:", f"AV. PRINCIPAL {rng.integers(100, 999)} {r.depto} - {r.prov} - {r.prov}",
            "Sistema Emisión de Comprobante:", "COMPUTARIZADO", "Actividad Comercio Exterior:", comex,
            "Sistema Contabilidad:", "COMPUTARIZADO", "Actividad(es) Económica(s):", f"Principal - {r.ciiu} - {nombres_ciiu[r.ciiu]}",
            "Secundaria 1 - 4659 - VENTA AL POR MAYOR DE OTROS TIPOS DE MAQUINARIA Y EQUIPO",
            "Comprobantes Electrónicos:", "FACTURA (desde 01/01/2016)", "Fecha consulta: 20/10/2026 10:00"])

    # --- ventas mensuales por cliente (2019-2026): entradas, salidas y estacionalidad
    meses = pd.period_range("2019-01", "2026-09", freq="M")
    ventas = []
    for r in cl.drop_duplicates("LicTradNum").itertuples():
        nivel = rng.lognormal(8.5, 1.1)
        inicio = rng.integers(0, len(meses) - 3) if rng.random() < .45 else 0
        fin = rng.integers(inicio + 3, len(meses)) if rng.random() < .30 else len(meses)
        crec = rng.normal(0.02, 0.08)
        frecuencia = rng.choice([0.12, 0.4, 0.8], p=[0.3, 0.4, 0.3])              # compradores esporádicos y frecuentes
        for k in range(inicio, fin):
            if rng.random() < frecuencia:
                ventas.append((r.LicTradNum, str(meses[k]), round(nivel * (1 + crec) ** (k / 12) * rng.lognormal(0, .5), 2)))
    ventas = pd.DataFrame(ventas, columns=["ruc", "mes", "venta_usd"])
    return {**tablas, "fichas": fichas, "ventas": ventas}
