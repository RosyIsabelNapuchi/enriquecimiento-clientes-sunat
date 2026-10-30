"""Consulta de fichas RUC en la web de SUNAT, con avance guardado tras CADA consulta (se puede cortar y retomar).

- El captcha lo resuelve una persona (modo manual); este módulo no intenta saltarlo.
- Hay pausa entre consultas para no sobrecargar el servicio.
- Para estado, condición y ubicación de miles de RUC, conviene usar primero el padrón masivo que publica
  SUNAT y dejar esta consulta solo para lo que el padrón no trae (actividad económica, comercio exterior).
La lógica de avance (`consultar_lote`) no depende del navegador, así se prueba sin internet.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Callable, Iterable

import pandas as pd

from .sunat_parser import CAMPOS, parsear_ficha

URL = "https://e-consultaruc.sunat.gob.pe/cl-ti-itmrconsruc/FrameCriterioBusquedaWeb.jsp"
COLUMNAS = ["RUC", "Consulta", *CAMPOS]


def cargar_progreso(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=COLUMNAS)
    prog = pd.read_csv(path, dtype=str, encoding="utf-8-sig").fillna("")
    return prog.drop_duplicates("RUC", keep="last")                  # un reintento reemplaza al ERROR anterior


def consultar_lote(rucs: Iterable[str], fetch: Callable[[str], str | None], progreso: Path,
                   pausa: float = 1.2, reintentos: int = 3) -> pd.DataFrame:
    """Consulta solo los RUC pendientes y anexa cada resultado al CSV de progreso apenas llega."""
    hechos = set(cargar_progreso(progreso).query("Consulta in ['OK', 'SIN DATOS']").RUC)
    for ruc in (r for r in rucs if r not in hechos):
        texto = None
        for _ in range(reintentos):
            try:
                texto = fetch(ruc)
                break
            except Exception:                                       # noqa: BLE001 - se reintenta y se registra
                time.sleep(pausa)
        fila = {"RUC": ruc, **{c: "" for c in CAMPOS}}
        if texto is None:
            fila["Consulta"] = "ERROR"                              # se reintentará en la próxima corrida
        else:
            datos = parsear_ficha(texto)
            fila.update(datos)
            fila["Consulta"] = "OK" if datos["RazonSocial"] else "SIN DATOS"
        pd.DataFrame([fila], columns=COLUMNAS).to_csv(progreso, mode="a", header=not progreso.exists(),
                                                       index=False, encoding="utf-8-sig")
        time.sleep(pausa)
    return cargar_progreso(progreso)


class SunatWeb:                                                      # pragma: no cover - requiere navegador
    """Navegador Chrome (Selenium estándar). La persona resuelve el captcha cuando aparece."""

    def __init__(self, espera_captcha: int = 240):
        from selenium import webdriver
        from selenium.webdriver.support.ui import WebDriverWait

        self.driver = webdriver.Chrome()
        self.espera_captcha = espera_captcha
        self.wait = WebDriverWait(self.driver, 25)

    def fetch(self, ruc: str) -> str:
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.support.ui import WebDriverWait

        self.driver.get(URL)
        campo = self.wait.until(EC.element_to_be_clickable((By.ID, "txtRuc")))
        campo.clear()
        campo.send_keys(ruc)
        self.driver.find_element(By.XPATH, "//button[contains(normalize-space(.), 'Buscar')]").click()
        WebDriverWait(self.driver, self.espera_captcha).until(
            EC.presence_of_element_located((By.XPATH, "//*[contains(normalize-space(.), 'Resultado de la Búsqueda')]")))
        return self.driver.find_element(By.TAG_NAME, "body").text

    def close(self) -> None:
        self.driver.quit()
