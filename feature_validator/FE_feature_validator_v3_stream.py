# import streamlit as st
# from BE_feature_validator_v3_stream import stream_graph

# st.title("💬 AI Feature Validator")

# user_input = st.text_input("Ask something")

# if user_input:

#     with st.chat_message("user"):
#         st.write(user_input)

#     # ==========================================
#     # 🔥 ASSISTANT STREAM
#     # ==========================================
#     with st.chat_message("assistant"):

#         def token_stream():
#             input_state = {
#                 "offer_name": user_input,
#                 "vendor_name": "Zoom",
#                 "feature": "AI meeting summaries"
#             }

#             for event in stream_graph(input_state):

#                 for node, output in event.items():

#                     # ✅ STREAM TOKENS
#                     if "stream_token" in output:
#                         yield output["stream_token"]

#         # 🚀 STREAM LIKE CHATGPT
#         ai_message = st.write_stream(token_stream)

import streamlit as st
from BE_feature_validator_v3_stream import stream_graph

st.set_page_config(layout="wide")
st.title("🚀 AI Feature Validator")

# =========================
# INPUT FORM
# =========================
offer = st.text_input("Offer Name", "Zoom Workplace Pro")
vendor = st.text_input("Vendor Name", "Zoom")
feature = st.text_input("Feature", "AI meeting summaries")

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
        "feature": feature
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

