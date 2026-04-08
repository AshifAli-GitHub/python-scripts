import streamlit as st
from BE_feature_validator_v4 import stream_graph

st.set_page_config(layout="wide")
st.title("🚀 AI Feature Validator")

# =========================
# INPUT FORM
# =========================
offer = st.text_input("Offer Name", "Zoom Workplace Pro")
vendor = st.text_input("Vendor Name", "Zoom")
feature = st.text_input("Feature", "AI meeting summaries")

cache_mode = st.radio("Cache Mode",["Use Cache", "Ignore Cache", "Refresh Cache"],horizontal=True)
run = st.button("Run Analysis")

# =========================
# PLACEHOLDERS
# =========================
result_box = st.empty()
trace_box = st.empty()
flow_box = st.empty()

if run:

    # Reset state
    logs = []
    flow = []

    input_state = {
        "offer_name": offer,
        "vendor_name": vendor,
        "feature": feature,
        "cache_mode": cache_mode
    }

    # =========================
    # TOKEN STREAM GENERATOR
    # =========================
    def token_stream():

        for event in stream_graph(input_state):

            for node, output in event.items():

                # 🔥 STREAM TOKENS (MAIN OUTPUT)
                if "stream_token" in output:
                    yield output["stream_token"]

                # ✅ FINAL RESULT
                if "result" in output:
                    result_box.success("✅ Completed")
                    result_box.json(output["result"])

                # 📊 TRACE LOGS
                if "logs" in output:
                    for log in output["logs"]:
                        logs.append(log)
                        flow.append(log["step"])

                        # Live Trace UI
                        with trace_box.container():
                            st.subheader("📊 Execution Trace")
                            for l in logs:
                                st.write(
                                    f"🔹 {l['step']} "
                                    f"({l['type']}) "
                                    f"⏱ {round(l.get('time_sec', 0), 2)}s"
                                )

                        # Flow UI
                        with flow_box.container():
                            st.subheader("🔁 Flow")
                            st.code(" → ".join(flow))

    # =========================
    # STREAM OUTPUT
    # =========================
    st.subheader("🧠 AI Output (Streaming)")
    st.write_stream(token_stream)