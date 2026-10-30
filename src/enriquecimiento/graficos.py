from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

SURFACE, INK2, GRID = "#fcfcfb", "#52514e", "#e6e5e0"
COL = {"COSTA": "#2a78d6", "SIERRA": "#eb6834", "SELVA": "#1baf7a"}


def _style():
    plt.rcParams.update({"figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
                         "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
                         "axes.titleweight": "bold", "axes.titlesize": 11, "axes.spines.top": False, "axes.spines.right": False,
                         "axes.grid": True, "grid.color": GRID, "axes.axisbelow": True, "legend.frameon": False,
                         "lines.linewidth": 2, "font.size": 9.5})


def figuras(mercado, selva, cal, out: Path) -> None:
    _style()
    out.mkdir(parents=True, exist_ok=True)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 4.2))
    m = mercado[(mercado.anio < 2026) & mercado.region.isin(COL)]
    for reg, c in COL.items():
        g = m[m.region == reg]
        a1.plot(g.anio, g.participacion * 100, color=c, marker="o", markersize=5, label=reg.title())
        a1.text(g.anio.iloc[-1] + 0.12, g.participacion.iloc[-1] * 100, reg.title(), color=INK2, va="center")
    a1.set(title="Participación de cada región en la venta (años completos)", ylabel="% de la venta")
    a1.legend(loc="center left", ncol=3)
    a1.set_xlim(m.anio.min() - 0.3, m.anio.max() + 0.9)
    est = selva["por_estado"].reindex(["RECURRENTE", "NUEVO", "REACTIVADO", "PERDIDO"]).fillna(0)
    a2.bar(est.index.str.title(), est.clientes, color=COL["SELVA"], width=0.6)
    for x, v in enumerate(est.clientes):
        a2.text(x, v + 0.3, f"{int(v)}", ha="center", color=INK2)
    a2.set(title="Clientes de la selva según su comportamiento (corte sep-2026)", ylabel="Clientes")
    a2.grid(axis="x", visible=False)
    fig.tight_layout()
    fig.savefig(out / "01_region_y_selva.png", dpi=160)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 3.6))
    c = cal.drop("clientes").sort_values()
    nombres = {"ruc_con_digito_invalido": "RUC con dígito verificador inválido", "ruc_duplicado_en_sap": "RUC duplicado en SAP",
               "sin_ficha_sunat": "Sin ficha en SUNAT", "direccion_sap_distinta_a_sunat": "Departamento en SAP ≠ SUNAT",
               "baja_o_no_habido_con_saldo": "Baja o no habido, con saldo por cobrar"}
    labels = [nombres.get(s, s) for s in c.index]
    ax.barh(labels, c.values, color=COL["COSTA"], height=0.55)
    for y, v in enumerate(c.values):
        ax.text(v + 0.2, y, str(int(v)), va="center", color=INK2)
    ax.set(title=f"Problemas de calidad encontrados en {int(cal['clientes'])} clientes", xlabel="Clientes")
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    fig.savefig(out / "02_calidad_de_datos.png", dpi=160)
    plt.close(fig)
