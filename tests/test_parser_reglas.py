import pytest

from enriquecimiento.rubros import con_digito, region_natural, rubro_ciiu, ruc_valido
from enriquecimiento.sunat_parser import parsear_ficha

FICHA = """Resultado de la Búsqueda
Número de RUC:
20999123454 - TRANSPORTES RÍO VERDE S.A.C.
Tipo Contribuyente:
SOCIEDAD ANONIMA CERRADA
Nombre Comercial:
-
Estado del Contribuyente:
ACTIVO
Condición del Contribuyente:
NO HABIDO
Domicilio Fiscal:
JR. LOS CEDROS 120 MADRE DE DIOS - TAMBOPATA - TAMBOPATA
Actividad Comercio Exterior:
IMPORTADOR/EXPORTADOR
Actividad(es) Económica(s):
Principal - 4923 - TRANSPORTE DE CARGA POR CARRETERA
Secundaria 1 - 4659 - VENTA AL POR MAYOR DE MAQUINARIA
Secundaria 2 - 7110 - ACTIVIDADES DE INGENIERIA
Fecha consulta: 20/10/2026 10:00"""


def test_parser_extrae_campos_clave():
    f = parsear_ficha(FICHA)
    assert f["RazonSocial"] == "TRANSPORTES RIO VERDE S.A.C."
    assert f["NombreComercial"] == ""                          # "-" se trata como vacío
    assert f["Condicion"] == "NO HABIDO"
    assert (f["Departamento"], f["Provincia"], f["Distrito"]) == ("MADRE DE DIOS", "TAMBOPATA", "TAMBOPATA")
    assert f["EsImportador"] == "SI"
    assert f["CIIU"] == "4923" and f["ActividadPrincipal"] == "TRANSPORTE DE CARGA POR CARRETERA"
    assert f["ActividadesSecundarias"].count("|") == 1


def test_parser_texto_vacio():
    assert set(parsear_ficha("").values()) == {""}


def test_validacion_ruc():
    ruc = con_digito("2099912345")
    assert ruc_valido(ruc)
    malo = ruc[:-1] + str((int(ruc[-1]) + 1) % 10)
    assert not ruc_valido(malo)
    assert not ruc_valido("12345") and not ruc_valido("99999999999")


@pytest.mark.parametrize("ciiu,rubro", [("0311", "PESCA"), ("0729", "MINERÍA E HIDROCARBUROS"), ("4290", "CONSTRUCCIÓN"),
                                        ("1610", "INDUSTRIA MANUFACTURERA"), ("", "SIN CLASIFICAR")])
def test_rubro_por_ciiu(ciiu, rubro):
    assert rubro_ciiu(ciiu) == rubro


def test_region_natural():
    assert region_natural("LORETO", "MAYNAS") == "SELVA"
    assert region_natural("JUNIN", "SATIPO") == "SELVA"           # selva alta en departamento andino
    assert region_natural("JUNIN", "HUANCAYO") == "SIERRA"
    assert region_natural("PIURA") == "COSTA"
    assert region_natural("") == "SIN UBICACIÓN"
