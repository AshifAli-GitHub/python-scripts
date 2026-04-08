# 🚀 AI Feature Validator

A production-grade system to **validate product features** using LLM reasoning, web search, scraping, and structured workflows.

---

## 🔹 Project Overview

This tool helps product teams assess whether a feature should be included in an offer by combining:

- **LLM reasoning**: Groq LLM to analyze pro/anti queries.
- **Web search & scraping**: Tavily and BeautifulSoup for real-world evidence collection.
- **Workflow orchestration**: LangGraph to manage parallel, sequential, and conditional execution.
- **Observability**: Langfuse for execution tracing at the node level.
- **Caching & reliability**: JSON enforcement, cache modes, and fallback parsing for deterministic results.

---

## 📦 Features

- **Flexible cache management**:
  - `Use Cache`, `Ignore Cache`, `Refresh Cache`.
- **Query planning**:
  - Automatically generates pro/anti queries for a feature.
- **Search & scrape**:
  - Collects URLs from Tavily and extracts textual content safely.
- **Feature verification**:
  - Evaluates pro vs anti evidence.
  - Produces JSON output including confidence scores, composite score, bundle type, verdict, reasons, risks, and summary.
  - Streams tokens in real-time for interactive UI feedback.
- **Structured logging**:
  - Node-level logs for debugging and analysis.
  - Live execution flow in Streamlit dashboard.
- **End-to-end results**:
  - Real-time token streaming.
  - JSON output with verdict, scores, reasons, risks, and summary.
  - Trace and flow visualization in Streamlit.

---

## 🖥 UI Preview

![Feature Validator UI](sample_output.png)

---

## ⚙️ How to Run

1. Clone the repository:
```bash
git clone <your-repo-url>
cd agentic-groq-feature-validator

2. Install dependencies:
pip install -r requirements.txt

3. Set up environment variables:
cp .env.example .env
# Fill in your GROQ_API_KEY and TAVILY_API_KEY

4. Run the Streamlit app:
streamlit run frontend.py

5. Use the UI to:
Enter Offer Name, Vendor Name, and Feature.
Select Cache Mode.
Click Run Analysis to see real-time AI results.

6. 🛠 Tech Stack
Python
Groq LLM – AI reasoning
Tavily – Search API
BeautifulSoup – Web scraping
LangGraph – Workflow orchestration
Langfuse – Observability
Streamlit – Interactive dashboard
JSON & SQLite – Caching and state management

📂 Project Structure
agentic-groq-feature-validator/
├── backend.py              # Core feature validator logic
├── frontend.py             # Streamlit UI
├── chatbot.db              # SQLite for state checkpoints
├── requirements.txt        # Python dependencies
├── .env.example            # Template for API keys
├── README.md               # Project documentation
└── sample_output.png       # UI screenshot



⚡ How it Works
Check cache: Skip computation if a valid cached result exists.
Query planner: Generate pro and anti queries for the feature.
Search & scrape: Collect evidence from web results.
Verifier: Use LLM to analyze evidence and produce JSON verdict.
Streaming & logging: Tokens, logs, and flow are streamed live to Streamlit.
Cache save: Final verdict is saved for future runs.




💡 Notes
Supports multiple cache modes for flexible testing.
Safe JSON parsing ensures LLM outputs are reliable.
Designed for multi-step analysis with full observability.