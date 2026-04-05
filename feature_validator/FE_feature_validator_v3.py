# app.py

import streamlit as st
import json
from backend import run_graph

st.set_page_config(page_title="Feature Validator", layout="wide")

st.title("🧠 AI Feature Validator")

# =========================
# INPUTS
# =========================
offer = st.text_input("Offer Name", "Zoom Workplace Pro")
vendor = st.text_input("Vendor Name", "Zoom")
feature = st.text_input("Feature", "AI meeting summaries")

if st.button("Run Analysis"):

    with st.spinner("Running graph..."):
        result = run_graph({
            "offer_name": offer,
            "vendor_name": vendor,
            "feature": feature
        })

    # =========================
    # RESULT
    # =========================
    st.subheader("✅ Final Result")
    st.json(result["result"])

    # =========================
    # TRACE
    # =========================
    st.subheader("📊 Execution Trace")

    for log in result["logs"]:
        with st.expander(f"{log['step']} ({log['type']})"):
            st.json(log)

    # =========================
    # VISUAL FLOW
    # =========================
    st.subheader("🔁 Flow Summary")

    flow = " → ".join([log["step"] for log in result["logs"]])
    st.code(flow)