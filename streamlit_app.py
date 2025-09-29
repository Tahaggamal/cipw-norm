# app.py
"""
Single-file Streamlit app (self-contained, corrected for st.rerun())
- Embedded CIPW normative calculation (simplified, returns final normative wt% only)
- Slim-left / wide-right dashboard layout
- CSV template download + upload (one-row)
- Save / Load / Delete saved analyses
- Excel & PDF download (direct)
- Reset all inputs button
- English UI
"""
import streamlit as st
import pandas as pd
import numpy as np
import os
import json
import io
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from datetime import datetime
from typing import Dict, Tuple

# -----------------------
# App configuration
# -----------------------
APP_TITLE = "CIPW Normative Minerals Calculator"
APP_SUBTITLE = "An interactive Streamlit app for geochemical analysis and normative mineral computation"
DEVELOPER = "Developed by Taha Gamal"

DATA_DIR = "data"
SAVED_JSON = os.path.join(DATA_DIR, "saved_analyses.json")
CSV_TEMPLATE_NAME = "CIPW_input_template.csv"

os.makedirs(DATA_DIR, exist_ok=True)
OXIDES = ["SiO2", "Al2O3", "Fe2O3", "FeO", "MgO", "CaO", "Na2O", "K2O", "TiO2", "P2O5"]

# -----------------------
# CIPW algorithm (simplified)
# -----------------------
MW_FE2O3 = 159.69
MW_FEO = 71.844

def calculate_cipw(oxides: Dict[str, float]) -> Tuple[Dict[str, float], Dict[str, str]]:
    SiO2 = float(oxides.get("SiO2", 0.0))
    Al2O3 = float(oxides.get("Al2O3", 0.0))
    Fe2O3 = float(oxides.get("Fe2O3", 0.0))
    FeO = float(oxides.get("FeO", 0.0))
    MgO = float(oxides.get("MgO", 0.0))
    CaO = float(oxides.get("CaO", 0.0))
    Na2O = float(oxides.get("Na2O", 0.0))
    K2O = float(oxides.get("K2O", 0.0))
    TiO2 = float(oxides.get("TiO2", 0.0))
    P2O5 = float(oxides.get("P2O5", 0.0))

    if FeO <= 0 and Fe2O3 > 0:
        FeO = Fe2O3 * ((2 * MW_FEO) / MW_FE2O3)

    raw = {
        'Quartz (Q)': max(0.0, SiO2 - (Al2O3 * 2.0 + CaO + MgO)),
        'Orthoclase (Or)': K2O * 6.58,
        'Albite (Ab)': Na2O * 8.52,
        'Anorthite (An)': CaO * 2.35,
        'Diopside (Di)': (CaO + MgO) * 1.1,
        'Olivine (Ol)': (MgO + FeO) * 0.9,
        'Magnetite (Mt)': Fe2O3 * 1.43,
        'Ilmenite (Il)': TiO2 * 1.89,
        'Apatite (Ap)': P2O5 * 3.33
    }

    total_raw = sum(raw.values())
    minerals = {k: round((v / total_raw) * 100.0, 4) if total_raw > 0 else 0.0 for k, v in raw.items()}

    descriptions = {
        'Quartz (Q)': 'Silicon dioxide — common in acidic and felsic rocks.',
        'Orthoclase (Or)': 'Potassium feldspar (KAlSi3O8) — common in silicic rocks.',
        'Albite (Ab)': 'Sodium feldspar (NaAlSi3O8) — typical in many silicic rocks.',
        'Anorthite (An)': 'Calcium feldspar (CaAl2Si2O8) — indicates higher Ca content.',
        'Diopside (Di)': 'Calcium–magnesium pyroxene — common in mafic to intermediate rocks.',
        'Olivine (Ol)': 'Mg–Fe silicate — typical of mafic and ultramafic rocks.',
        'Magnetite (Mt)': 'Iron oxide — an indicator of oxidation state (Fe3+).',
        'Ilmenite (Il)': 'Titanium–iron oxide — indicator of Ti presence.',
        'Apatite (Ap)': 'Calcium phosphate — phosphorus carrier.'
    }

    return minerals, descriptions

# -----------------------
# Utility functions
# -----------------------
def load_saved_analyses():
    if not os.path.exists(SAVED_JSON):
        return {}
    try:
        with open(SAVED_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except:
        return {}

def write_saved_analyses(d):
    with open(SAVED_JSON, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)

def df_to_excel_bytes(df: pd.DataFrame, meta: dict) -> bytes:
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="CIPW_Norm")
        pd.DataFrame([meta]).to_excel(writer, index=False, sheet_name="Metadata")
    return out.getvalue()

def df_to_pdf_bytes(df: pd.DataFrame, meta: dict) -> bytes:
    out = io.BytesIO()
    with PdfPages(out) as pp:
        fig, ax = plt.subplots(figsize=(8.27, 11.69))
        ax.axis('off')
        ax.text(0.5, 0.95, APP_TITLE, ha='center', va='center', fontsize=14, weight='bold')
        ax.text(0.5, 0.92, APP_SUBTITLE, ha='center', va='center', fontsize=10)
        ax.text(0.02, 0.87, f"Name: {meta.get('name','')}")
        ax.text(0.02, 0.85, f"Date: {meta.get('date','')}")
        ax.text(0.02, 0.83, f"Note: {meta.get('note','')}")
        table_text = "\n".join([f"{row['Mineral']}: {row['Normative wt%']}%" for _, row in df.iterrows()])
        ax.text(0.02, 0.70, table_text, fontsize=10, family='monospace')
        pp.savefig(fig, bbox_inches='tight')
        plt.close(fig)
    return out.getvalue()

def csv_template_bytes() -> bytes:
    return (",".join(OXIDES) + "\n").encode("utf-8")

# -----------------------
# Streamlit UI
# -----------------------
st.set_page_config(page_title=APP_TITLE, layout="wide")
st.markdown(f"# {APP_TITLE}")
st.markdown(f"**{APP_SUBTITLE}**  \n*{DEVELOPER}*")
st.write("---")

left_col, right_col = st.columns([1, 2.5])

saved_analyses = load_saved_analyses()
for ox in OXIDES:
    key = f"oxide_{ox}"
    if key not in st.session_state:
        st.session_state[key] = 0.0

with left_col:
    st.header("Inputs")
    st.markdown("**Enter oxide wt%**")
    for ox in OXIDES:
        st.session_state[f"oxide_{ox}"] = st.number_input(ox, min_value=0.0, value=float(st.session_state[f"oxide_{ox}"]), step=0.01, format="%.4f", key=f"input_{ox}")

    if st.button("Reset all inputs"):
        for ox in OXIDES:
            st.session_state[f"oxide_{ox}"] = 0.0
        st.success("All inputs reset to 0.0")
        st.rerun()

    st.markdown("---")
    st.subheader("CSV Input (single-row)")
    st.download_button("Download CSV template", data=csv_template_bytes(), file_name=CSV_TEMPLATE_NAME, mime="text/csv")
    uploaded = st.file_uploader("Upload a single-row CSV file (one analysis)", type=["csv"])
    if uploaded is not None:
        try:
            df_csv = pd.read_csv(uploaded)
            if df_csv.shape[0] != 1:
                st.error("CSV must contain exactly one row (one analysis).")
            else:
                missing = [c for c in OXIDES if c not in df_csv.columns]
                if missing:
                    st.error(f"Missing required columns: {missing}")
                else:
                    row = df_csv.iloc[0]
                    try:
                        for ox in OXIDES:
                            st.session_state[f"oxide_{ox}"] = float(row[ox])
                        st.success("Values loaded from CSV successfully")
                        st.rerun()
                    except:
                        st.error("CSV contains non-numeric value(s) in oxide columns.")
        except Exception as e:
            st.error(f"Failed to read CSV: {e}")

    st.markdown("---")
    if st.button("Calculate CIPW Normative Minerals"):
        oxide_values = {ox: float(st.session_state.get(f"oxide_{ox}", 0.0)) for ox in OXIDES}
        minerals, descriptions = calculate_cipw(oxide_values)
        results_df = pd.DataFrame([{"Mineral": k, "Normative wt%": v, "Description": descriptions.get(k, "")} for k, v in minerals.items()])
        st.session_state["last_results_df"] = results_df
        st.session_state["last_meta"] = {"name": f"Analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}", "date": datetime.now().isoformat(), "note": ""}
        st.success("Calculation done. See results on the right.")
        st.rerun()

# Right column: results
with right_col:
    st.header("Results")
    if "last_results_df" in st.session_state:
        df = st.session_state["last_results_df"]
        meta = st.session_state.get("last_meta", {})
        st.subheader("Normative minerals")
        st.dataframe(df[["Mineral", "Normative wt%", "Description"]], use_container_width=True)

        fig, ax = plt.subplots(figsize=(8, 4))
        ax.bar(df["Mineral"], df["Normative wt%"])
        ax.set_ylabel("wt%")
        ax.set_xticklabels(df["Mineral"], rotation=45, ha="right")
        st.pyplot(fig)

        st.write("---")
        st.write("Note:")
        note_val = st.text_area("Add a note to this run", value=meta.get("note",""))
        meta["note"] = note_val
        st.session_state["last_meta"] = meta

        export_df = df[["Mineral", "Normative wt%", "Description"]]
        st.download_button("Download Results (Excel)", data=df_to_excel_bytes(export_df, meta), file_name=f"{meta.get('name','CIPW')}_results.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        st.download_button("Download Results (PDF)", data=df_to_pdf_bytes(export_df, meta), file_name=f"{meta.get('name','CIPW')}_results.pdf", mime="application/pdf")

    else:
        st.info("No results yet. Enter inputs and press Calculate.")

st.write("---")
st.caption("Simplified CIPW normative calculator for education/research. For full CIPW, include Fe2+/Fe3+ allocation and full stoichiometry.")
