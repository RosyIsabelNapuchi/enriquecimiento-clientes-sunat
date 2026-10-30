"""Convierte el texto de la ficha "Consulta RUC" de SUNAT en columnas estructuradas.

El parser trabaja sobre TEXTO, así sirve igual con la página web, un PDF copiado o un archivo guardado.
"""
from __future__ import annotations

import re
import unicodedata

DEPARTAMENTOS = ["AMAZONAS", "ANCASH", "APURIMAC", "AREQUIPA", "AYACUCHO", "CAJAMARCA", "CALLAO", "CUSCO",
                 "HUANCAVELICA", "HUANUCO", "ICA", "JUNIN", "LA LIBERTAD", "LAMBAYEQUE", "LIMA", "LORETO",
                 "MADRE DE DIOS", "MOQUEGUA", "PASCO", "PIURA", "PUNO", "SAN MARTIN", "TACNA", "TUMBES", "UCAYALI"]
_DEPTOS_ORD = sorted(DEPARTAMENTOS, key=len, reverse=True)       # "MADRE DE DIOS" antes que "DIOS"

ETIQUETAS = {
    "NUMERO DE RUC": "ruc_razon", "TIPO CONTRIBUYENTE": "tipo", "PROFESION U OFICIO": "profesion",
    "NOMBRE COMERCIAL": "nombre_comercial", "FECHA DE INSCRIPCION": "f_inscripcion",
    "FECHA DE INICIO DE ACTIVIDADES": "f_inicio", "ESTADO DEL CONTRIBUYENTE": "estado", "FECHA DE BAJA": "f_baja",
    "CONDICION DEL CONTRIBUYENTE": "condicion", "DOMICILIO FISCAL": "domicilio",
    "SISTEMA EMISION DE COMPROBANTE": "sist_emision", "ACTIVIDAD COMERCIO EXTERIOR": "com_exterior",
    "SISTEMA CONTABILIDAD": "sist_contab", "ACTIVIDAD(ES) ECONOMICA(S)": "actividades",
    "COMPROBANTES DE PAGO C/AUT. DE IMPRESION (F. 806 U 816)": "_ignorar", "SISTEMA DE EMISION ELECTRONICA": "_ignorar",
    "EMISOR ELECTRONICO DESDE": "_ignorar", "COMPROBANTES ELECTRONICOS": "comp_elec", "AFILIADO AL PLE DESDE": "_ignorar",
    "PADRONES": "_ignorar", "FECHA CONSULTA": "f_consulta",
}
CAMPOS = ["RazonSocial", "TipoContribuyente", "NombreComercial", "FechaInscripcion", "FechaInicioActividades",
          "Estado", "Condicion", "FechaBaja", "Domicilio", "Departamento", "Provincia", "Distrito", "ComercioExterior",
          "EsImportador", "CIIU", "ActividadPrincipal", "ActividadesSecundarias", "FechaConsultaSUNAT"]


def normaliza(s: str) -> str:
    if not isinstance(s, str):
        return ""
    s = unicodedata.normalize("NFKD", s.upper().strip())
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return re.sub(r"[ \t]{2,}", " ", s)


def _etiqueta(linea: str) -> tuple[str | None, str | None]:
    for etq, campo in ETIQUETAS.items():
        if linea.startswith(etq):
            resto = linea[len(etq):].strip()
            if resto.startswith(":"):
                return campo, resto[1:].strip()
            if resto == "":
                return campo, ""
    return None, None


def parsear_ficha(texto: str) -> dict[str, str]:
    out = {c: "" for c in CAMPOS}
    if not texto:
        return out
    bloques: dict[str, list[str]] = {}
    actual = None
    for linea in texto.replace("\r", "").split("\n"):
        ln = normaliza(linea)
        if not ln:
            continue
        campo, resto = _etiqueta(ln)
        if campo is not None:
            actual = campo
            bloques.setdefault(actual, [])
            if resto:
                bloques[actual].append(resto)
        elif actual is not None:
            bloques[actual].append(ln)

    def g(c: str) -> str:
        v = " ".join(bloques.get(c, [])).strip()
        return "" if v == "-" else v

    m = re.match(r"(\d{11})\s*-\s*(.+)", g("ruc_razon"))
    out["RazonSocial"] = m.group(2).strip() if m else ""
    for campo, clave in [("TipoContribuyente", "tipo"), ("NombreComercial", "nombre_comercial"),
                         ("FechaInscripcion", "f_inscripcion"), ("FechaInicioActividades", "f_inicio"),
                         ("Estado", "estado"), ("Condicion", "condicion"), ("FechaBaja", "f_baja"),
                         ("FechaConsultaSUNAT", "f_consulta")]:
        out[campo] = g(clave)

    # Domicilio "... DEPARTAMENTO - PROVINCIA - DISTRITO"
    dom = g("domicilio")
    out["Domicilio"] = dom
    partes = [p.strip() for p in dom.split(" - ")]
    if len(partes) >= 3:
        out["Provincia"], out["Distrito"] = partes[-2], partes[-1]
        for d in _DEPTOS_ORD:
            if partes[-3] == d or partes[-3].endswith(" " + d):
                out["Departamento"] = d
                break

    ce = g("com_exterior")
    out["ComercioExterior"] = ce
    out["EsImportador"] = "SI" if "IMPORTADOR" in ce else ("NO" if ce else "")

    acts = " ".join(bloques.get("actividades", []))
    pri = re.search(r"PRINCIPAL\s*-\s*(\d{4})\s*-\s*(.+?)(?=\s*SECUNDARIA\s*\d+\s*-|$)", acts)
    if pri:
        out["CIIU"], out["ActividadPrincipal"] = pri.group(1), pri.group(2).strip()
    secs = re.findall(r"SECUNDARIA\s*\d+\s*-\s*(\d{4})\s*-\s*(.+?)(?=\s*SECUNDARIA\s*\d+\s*-|$)", acts)
    out["ActividadesSecundarias"] = " | ".join(f"{c} - {d.strip()}" for c, d in secs)
    return out
