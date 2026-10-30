-- Maestro de clientes con todas sus direcciones desde SAP Business One (HANA).
-- Tablas estándar de SAP B1: OCRD (socios de negocio), CRD1 (direcciones), OSLP (vendedores),
-- OCRG (grupos), OCST (departamentos), OCRY (países).
-- {ESQUEMA} se reemplaza en tiempo de ejecución con la variable de entorno SAP_SCHEMA.
-- Solo lectura: usar un usuario de base de datos con permiso SELECT.
SELECT
    T0."CardCode"                                   AS "codigo_cliente",
    T0."CardName"                                   AS "razon_social",
    T0."LicTradNum"                                 AS "ruc",
    T0."Phone1"                                     AS "telefono",
    T0."E_Mail"                                     AS "correo",
    T3."GroupName"                                  AS "grupo_cliente",
    T2."SlpName"                                    AS "vendedor",
    T0."Currency"                                   AS "moneda",
    T0."Balance"                                    AS "saldo",
    T0."CreditLine"                                 AS "linea_credito",
    CASE WHEN T0."validFor" = 'Y' THEN 'Activo' ELSE 'Inactivo' END AS "estado_cliente",
    CASE WHEN T1."AdresType" = 'B' THEN 'FACTURACION'
         WHEN T1."AdresType" = 'S' THEN 'ENTREGA'
         ELSE T1."AdresType" END                    AS "tipo_direccion",
    T1."Address"                                    AS "id_direccion",
    T1."City"                                       AS "distrito",
    T1."County"                                     AS "provincia",
    T4."Name"                                       AS "departamento",
    T5."Name"                                       AS "pais",
    IFNULL(T1."Street", '')
        || CASE WHEN IFNULL(T1."StreetNo", '') <> '' THEN ' ' || T1."StreetNo" ELSE '' END
        || CASE WHEN IFNULL(T1."City", '')     <> '' THEN ', ' || T1."City"     ELSE '' END
        || CASE WHEN IFNULL(T1."County", '')   <> '' THEN ', ' || T1."County"   ELSE '' END
        || CASE WHEN IFNULL(T4."Name", '')     <> '' THEN ', ' || T4."Name"     ELSE '' END
        || CASE WHEN IFNULL(T5."Name", '')     <> '' THEN ', ' || T5."Name"     ELSE '' END
                                                    AS "direccion_completa",
    CASE WHEN (T1."AdresType" = 'B' AND T1."Address" = T0."BillToDef")
           OR (T1."AdresType" = 'S' AND T1."Address" = T0."ShipToDef")
         THEN 'SI' ELSE 'NO' END                    AS "direccion_predeterminada"
FROM "{ESQUEMA}".OCRD T0
LEFT JOIN "{ESQUEMA}".CRD1 T1 ON T0."CardCode" = T1."CardCode"
LEFT JOIN "{ESQUEMA}".OSLP T2 ON T0."SlpCode" = T2."SlpCode"
LEFT JOIN "{ESQUEMA}".OCRG T3 ON T0."GroupCode" = T3."GroupCode"
LEFT JOIN "{ESQUEMA}".OCST T4 ON T1."State" = T4."Code" AND T1."Country" = T4."Country"
LEFT JOIN "{ESQUEMA}".OCRY T5 ON T1."Country" = T5."Code"
WHERE T0."CardType" = 'C'
ORDER BY T0."CardName", T1."AdresType", T1."Address"
