"""Reglas de negocio: validación de RUC, rubro por CIIU (Rev. 4) y región natural por ubicación."""
from __future__ import annotations

import re

# Dígito verificador del RUC (módulo 11): pesos sobre los 10 primeros dígitos.
_PESOS = (5, 4, 3, 2, 7, 6, 5, 4, 3, 2)


def ruc_valido(ruc: str) -> bool:
    ruc = re.sub(r"\D", "", str(ruc or ""))
    if len(ruc) != 11 or ruc[:2] not in {"10", "15", "16", "17", "20"}:
        return False
    resto = 11 - sum(int(d) * p for d, p in zip(ruc[:10], _PESOS)) % 11
    return int(ruc[10]) == {10: 0, 11: 1}.get(resto, resto)


def con_digito(base10: str) -> str:
    resto = 11 - sum(int(d) * p for d, p in zip(base10, _PESOS)) % 11
    return base10 + str({10: 0, 11: 1}.get(resto, resto))


# Rubro por división CIIU (2 primeros dígitos)
_RUBROS = [((1, 2), "AGROINDUSTRIA"), ((3, 3), "PESCA"), ((5, 9), "MINERÍA E HIDROCARBUROS"),
           ((10, 33), "INDUSTRIA MANUFACTURERA"), ((35, 39), "ENERGÍA Y SERVICIOS PÚBLICOS"), ((41, 43), "CONSTRUCCIÓN"),
           ((45, 47), "COMERCIO"), ((49, 53), "TRANSPORTE Y LOGÍSTICA"), ((55, 56), "HOTELES Y RESTAURANTES"),
           ((58, 82), "SERVICIOS EMPRESARIALES"), ((84, 84), "SECTOR PÚBLICO"), ((85, 99), "OTROS SERVICIOS")]


def rubro_ciiu(ciiu: str) -> str:
    m = re.match(r"^(\d{2})", str(ciiu or ""))
    if not m:
        return "SIN CLASIFICAR"
    div = int(m.group(1))
    return next((r for (lo, hi), r in _RUBROS if lo <= div <= hi), "SIN CLASIFICAR")


SELVA = {"LORETO", "UCAYALI", "MADRE DE DIOS", "SAN MARTIN", "AMAZONAS"}
# Provincias de selva alta en departamentos andinos (se puede ampliar)
SELVA_ALTA = {("JUNIN", "SATIPO"), ("JUNIN", "CHANCHAMAYO"), ("PASCO", "OXAPAMPA"), ("CUSCO", "LA CONVENCION"),
              ("HUANUCO", "LEONCIO PRADO"), ("PUNO", "SANDIA"), ("CAJAMARCA", "JAEN"), ("CAJAMARCA", "SAN IGNACIO")}
COSTA = {"TUMBES", "PIURA", "LAMBAYEQUE", "LA LIBERTAD", "ICA", "TACNA", "MOQUEGUA", "CALLAO", "LIMA", "ANCASH", "AREQUIPA"}


def region_natural(departamento: str, provincia: str = "") -> str:
    """Aproximación por departamento (y provincias de selva alta). Útil para segmentar, no es un límite oficial."""
    d, p = (departamento or "").upper(), (provincia or "").upper()
    if not d:
        return "SIN UBICACIÓN"
    if d in SELVA or (d, p) in SELVA_ALTA:
        return "SELVA"
    return "COSTA" if d in COSTA else "SIERRA"
