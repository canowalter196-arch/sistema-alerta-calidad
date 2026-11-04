import re
from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="Antecedentes de calidad", page_icon="🧪", layout="wide")

st.title("Sistema de antecedentes y alertas de calidad")
st.caption("Consulta de órdenes SAP y desvíos históricos por código de material")

def normalize(value):
    if pd.isna(value):
        return ""
    return re.sub(r"\s+", "", str(value)).strip()

def split_codes(value):
    if pd.isna(value):
        return []
    # Los códigos múltiples de la fuente se separan por guion, coma, punto y coma o barra.
    # Comparación por token completo para evitar falsos positivos.
    return [normalize(x) for x in re.split(r"\s*[-;,/]\s*", str(value)) if normalize(x)]

@st.cache_data(show_spinner=False)
def load_data(file_bytes):
    from io import BytesIO
    xls = pd.ExcelFile(BytesIO(file_bytes))
    required = {"Ordenes procesadas", "Desvios"}
    if not required.issubset(set(xls.sheet_names)):
        raise ValueError(f"Faltan hojas requeridas: {required - set(xls.sheet_names)}")
    orders = pd.read_excel(xls, sheet_name="Ordenes procesadas", dtype=str)
    deviations = pd.read_excel(xls, sheet_name="Desvios", dtype=str)
    orders.columns = [str(c).strip() for c in orders.columns]
    deviations.columns = [str(c).strip() for c in deviations.columns]
    if "Número material" not in orders.columns or "Código" not in deviations.columns:
        raise ValueError("No se encontraron las columnas clave 'Número material' y/o 'Código'.")
    orders["codigo_norm"] = orders["Número material"].map(normalize)
    deviations["codigos_norm"] = deviations["Código"].map(split_codes)
    return orders, deviations

with st.sidebar:
    st.header("Fuente de datos")
    uploaded = st.file_uploader("Cargar archivo Excel", type=["xlsx"])
    st.info("La aplicación trabaja con una copia cargada por el usuario. No modifica el archivo fuente.")

default_path = Path(__file__).with_name("BASE DE DATOS PARA PRUEBAS..xlsx")
if uploaded:
    file_bytes = uploaded.getvalue()
elif default_path.exists():
    file_bytes = default_path.read_bytes()
else:
    st.warning("Cargá el archivo Excel original desde el panel lateral para comenzar.")
    st.stop()

try:
    orders, deviations = load_data(file_bytes)
except Exception as exc:
    st.error(f"No se pudo procesar el archivo: {exc}")
    st.stop()

materials = set(orders["codigo_norm"].dropna()) | {
    code for codes in deviations["codigos_norm"] for code in codes
}
materials.discard("")
open_mask = deviations.get("Status", pd.Series(index=deviations.index, dtype=str)).fillna("").str.lower().str.contains("investigar|abierto|pendiente", regex=True)
k1,k2,k3,k4 = st.columns(4)
k1.metric("Órdenes procesadas", f"{len(orders):,}")
k2.metric("Desvíos registrados", f"{len(deviations):,}")
k3.metric("Materiales identificados", f"{len(materials):,}")
k4.metric("Desvíos pendientes*", f"{int(open_mask.sum()):,}")
st.caption("*Clasificación orientativa por texto del estado; validar el catálogo oficial de estados.")

st.divider()
st.subheader("Consulta por material")
query = st.text_input("Código de material", placeholder="Ej.: 3702784").strip()
if query:
    code = normalize(query)
    order_hits = orders[orders["codigo_norm"] == code].copy()
    dev_hits = deviations[deviations["codigos_norm"].map(lambda xs: code in xs)].copy()

    product = ""
    if not order_hits.empty and "Texto breve material" in order_hits:
        product = str(order_hits.iloc[0]["Texto breve material"])
    elif not dev_hits.empty and "Producto" in dev_hits:
        product = str(dev_hits.iloc[0]["Producto"])

    a,b,c = st.columns(3)
    a.metric("Producto", product or "No identificado")
    b.metric("Órdenes SAP", len(order_hits))
    c.metric("Desvíos asociados", len(dev_hits))

    if len(dev_hits):
        st.error("ALERTA: el material tiene antecedentes de desvíos. Revisar los registros antes de continuar.")
    elif len(order_hits):
        st.success("Sin desvíos asociados en la base suministrada.")
    else:
        st.warning("Código no encontrado en ninguna de las dos hojas.")

    tab1,tab2,tab3 = st.tabs(["Desvíos", "Órdenes SAP", "Análisis"])
    with tab1:
        if dev_hits.empty:
            st.info("No hay desvíos asociados a este material.")
        else:
            display_cols = [c for c in ["Nº","Producto","Orden","Lote","Código","Nº de Orden","Fecha de Notificación","Clasificación","Status","DESCRIPCION","Clasif. causa raíz","Equipo ","CAPA","Responsable","Fecha estimada","Fecha de cierre"] if c in dev_hits.columns]
            st.dataframe(dev_hits[display_cols], use_container_width=True, hide_index=True)
    with tab2:
        if order_hits.empty:
            st.info("No hay órdenes SAP asociadas.")
        else:
            display_cols = [c for c in ["Fecha liberac.real","Fecha de fin real","Centro","Orden","Número material","Texto breve material","Lote","Cantidad orden (GMEIN)","Cantidad entregada (GMEIN)","Status de sistema"] if c in order_hits.columns]
            st.dataframe(order_hits[display_cols], use_container_width=True, hide_index=True)
    with tab3:
        if not dev_hits.empty and "Clasif. causa raíz" in dev_hits:
            counts = dev_hits["Clasif. causa raíz"].fillna("Sin clasificar").value_counts().rename_axis("Causa raíz").reset_index(name="Cantidad")
            st.plotly_chart(px.bar(counts, x="Causa raíz", y="Cantidad", title="Desvíos por causa raíz"), use_container_width=True)
        if not dev_hits.empty and "Status" in dev_hits:
            st.write("Distribución por estado")
            st.dataframe(dev_hits["Status"].fillna("Sin estado").value_counts().rename_axis("Estado").reset_index(name="Cantidad"), hide_index=True, use_container_width=True)
else:
    st.info("Ingresá un código de material para consultar su historial.")
    left,right = st.columns(2)
    with left:
        st.subheader("Desvíos por causa raíz")
        if "Clasif. causa raíz" in deviations:
            counts = deviations["Clasif. causa raíz"].fillna("Sin clasificar").value_counts().rename_axis("Causa raíz").reset_index(name="Cantidad")
            st.plotly_chart(px.bar(counts, x="Causa raíz", y="Cantidad"), use_container_width=True)
    with right:
        st.subheader("Desvíos por estado")
        if "Status" in deviations:
            counts = deviations["Status"].fillna("Sin estado").value_counts().rename_axis("Estado").reset_index(name="Cantidad")
            st.plotly_chart(px.pie(counts, names="Estado", values="Cantidad", hole=.45), use_container_width=True)

with st.expander("Alcance, supuestos y controles"):
    st.markdown("""
    - La clave de relación es **Número material** (órdenes SAP) ↔ **Código** (desvíos).
    - La columna Código puede contener varios materiales separados por guiones, comas, punto y coma o barras; cada token se compara de forma exacta.
    - No se infiere que un material esté liberado o bloqueado: la alerta indica antecedentes y requiere evaluación de Calidad.
    - La clasificación de estados pendientes es orientativa y debe validarse con el procedimiento interno.
    - Antes de usar en producción, definir responsable de actualización, frecuencia, trazabilidad, permisos y validación de datos.
    """)
