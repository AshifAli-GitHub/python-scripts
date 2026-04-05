# # ==========================================
# # 1. IMPORTS
# # ==========================================
# import os
# import json
# import requests
# from bs4 import BeautifulSoup
# from dotenv import load_dotenv
# from typing import TypedDict, List, Dict

# #from langchain_openai import ChatOpenAI
# from langchain_ollama import ChatOllama

# from langgraph.graph import StateGraph, END
# from tavily import TavilyClient


# # ==========================================
# # 2. LOAD ENV + INITIALIZE SERVICES
# # ==========================================
# load_dotenv()

# # LLM
# # llm = ChatOpenAI(model="gpt-4o-mini",temperature=0)
# llm = ChatOllama(model="tinyllama",temperature=0)
# # Tavily Search
# tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

# #Ollama is NOT strict like OpenAI,So this line will BREAK sometimes: 
# #  data = json.loads(response.content)

# import re

# def safe_json_parse(text):
#     try:
#         return json.loads(text)
#     except:
#         # extract JSON manually
#         match = re.search(r"\{.*\}", text, re.DOTALL)
#         if match:
#             return json.loads(match.group())
#         return {}

# # ==========================================
# # 3. STATE DEFINITION
# # ==========================================
# class State(TypedDict):
#     offer_name: str
#     vendor_name: str
#     feature: str

#     pro_queries: List[str]
#     anti_queries: List[str]

#     pro_urls: List[Dict]
#     anti_urls: List[Dict]

#     pro_docs: List[str]
#     anti_docs: List[str]

#     result: Dict


# # ==========================================
# # 4. NODE 1: QUERY PLANNER
# # ==========================================
# def query_planner(state: State):
#     # only adding strict json detail because of ollama messy json o/p 
#     prompt = f"""
#     Generate search queries.
    
#     You must return only valid JSON 
#     Do not add explanation 

#     Offer: {state['offer_name']}
#     Vendor: {state['vendor_name']}
#     Feature: {state['feature']}

#     Output JSON:
#     {{
#         "pro": ["...", "..."],
#         "anti": ["...", "..."]
#     }}
#     """

#     response = llm.invoke(prompt)
#     #data = json.loads(response.content)
#     data = safe_json_parse(response.content)

#     return {
#         "pro_queries": data["pro"],
#         "anti_queries": data["anti"]
#     }


# # ==========================================
# # 5. SEARCH FUNCTION (TAVILY)
# # ==========================================
# def search_web(query):
#     try:
#         response = tavily.search(
#             query=query,
#             search_depth="basic",
#             max_results=3
#         )

#         results = []
#         for r in response["results"]:
#             results.append({
#                 "url": r["url"],
#                 "title": r["title"],
#                 "snippet": r["content"]
#             })

#         return results

#     except Exception as e:
#         print("Search error:", e)
#         return []


# # ==========================================
# # 6. NODE 2: SEARCH
# # ==========================================
# def search_node(state: State):
#     pro_urls = []
#     anti_urls = []

#     # PRO SEARCH
#     for q in state["pro_queries"]:
#         pro_urls.extend(search_web(q))

#     # ANTI SEARCH
#     for q in state["anti_queries"]:
#         anti_urls.extend(search_web(q))

#     # Deduplicate
#     pro_urls = list({r["url"]: r for r in pro_urls}.values())[:2]
#     anti_urls = list({r["url"]: r for r in anti_urls}.values())[:2]

#     return {
#         "pro_urls": pro_urls,
#         "anti_urls": anti_urls
#     }


# # ==========================================
# # 7. SCRAPER FUNCTION
# # ==========================================
# def scrape(url):
#     try:
#         res = requests.get(url, timeout=5)
#         soup = BeautifulSoup(res.text, "html.parser")

#         text = soup.get_text(separator=" ", strip=True)
#         return text[:2000]

#     except Exception as e:
#         print("Scrape error:", e)
#         return ""


# # ==========================================
# # 8. NODE 3: SCRAPER
# # ==========================================
# def scrape_node(state: State):
#     pro_docs = [scrape(r["url"]) for r in state["pro_urls"]]
#     anti_docs = [scrape(r["url"]) for r in state["anti_urls"]]

#     return {
#         "pro_docs": pro_docs,
#         "anti_docs": anti_docs
#     }


# # ==========================================
# # 9. NODE 4: VERIFICATION
# # ==========================================
# def verify_node(state: State):
#     #in this prompt also giving json strict guidance
#     prompt = f"""
#     You are a verification agent.

#     Offer: {state['offer_name']}
#     Feature: {state['feature']}

#     PRO DOCUMENTS:
#     {state['pro_docs']}

#     ANTI DOCUMENTS:
#     {state['anti_docs']}

#     Return JSON:
#     {{
#         "pro_confidence": 0-100,
#         "anti_confidence": 0-100,
#         "composite_score": 0-100,
#         "bundle_type": "Always/Limited/Add-on/Never",
#         "summary": "2-3 lines explanation"
#     }}
#     """

#     response = llm.invoke(prompt)
#     #return {"result": json.loads(response.content)}
#     return {"result": safe_json_parse(response.content)}

# # ==========================================
# # 10. BUILD LANGGRAPH
# # ==========================================
# builder = StateGraph(State)

# builder.add_node("planner", query_planner)
# builder.add_node("search", search_node)
# builder.add_node("scrape", scrape_node)
# builder.add_node("verify", verify_node)

# builder.set_entry_point("planner")

# builder.add_edge("planner", "search")
# builder.add_edge("search", "scrape")
# builder.add_edge("scrape", "verify")
# builder.add_edge("verify", END)

# graph = builder.compile()


# # ==========================================
# # 11. RUN TEST
# # ==========================================
# if __name__ == "__main__":
#     input_state = {
#         "offer_name": "Zoom Workplace Pro",
#         "vendor_name": "Zoom",
#         "feature": "AI meeting summaries"
#     }

#     result = graph.invoke(input_state)

#     print("\n===== FINAL RESULT =====\n")
#     print(json.dumps(result["result"], indent=2))

# # ==========================================
# # 1. IMPORTS
# # ==========================================
# import os
# import json
# import re
# import requests
# from bs4 import BeautifulSoup
# from dotenv import load_dotenv
# from typing import TypedDict, List, Dict

# import google.generativeai as genai
# from langgraph.graph import StateGraph, END
# from tavily import TavilyClient


# # ==========================================
# # 2. LOAD ENV + INIT GEMINI
# # ==========================================
# load_dotenv()

# genai.configure(api_key=os.getenv("AIzaSyCf_XEAsyF48vmMD-82abe6ZQBN9qmRbcM"))

# # ✅ USE WORKING MODEL
# model = genai.GenerativeModel("gemini-2.5-flash")

# # Tavily
# tavily = TavilyClient(api_key=os.getenv("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"))


# # ==========================================
# # 3. SAFE JSON PARSER (VERY IMPORTANT)
# # ==========================================
# def safe_json_parse(text):
#     try:
#         return json.loads(text)
#     except:
#         match = re.search(r"\{.*\}", text, re.DOTALL)
#         if match:
#             return json.loads(match.group())
#         return {}


# # ==========================================
# # 4. STATE
# # ==========================================
# class State(TypedDict):
#     offer_name: str
#     vendor_name: str
#     feature: str

#     pro_queries: List[str]
#     anti_queries: List[str]

#     pro_urls: List[Dict]
#     anti_urls: List[Dict]

#     pro_docs: List[str]
#     anti_docs: List[str]

#     result: Dict


# # ==========================================
# # 5. GEMINI CALL
# # ==========================================
# def call_llm(prompt: str):
#     response = model.generate_content(
#         prompt,
#         generation_config={
#             "temperature": 0
#         }
#     )
#     return response.text


# # ==========================================
# # 6. NODE 1: QUERY PLANNER
# # ==========================================
# def query_planner(state: State):
#     prompt = f"""
#     Return ONLY valid JSON. No explanation.

#     Offer: {state['offer_name']}
#     Feature: {state['feature']}

#     Output:
#     {{
#       "pro": ["query1", "query2"],
#       "anti": ["query1", "query2"]
#     }}
#     """

#     res = call_llm(prompt)
#     data = safe_json_parse(res)

#     return {
#         "pro_queries": data.get("pro", []),
#         "anti_queries": data.get("anti", [])
#     }


# # ==========================================
# # 7. SEARCH (TAVILY)
# # ==========================================
# def search_web(query):
#     try:
#         response = tavily.search(
#             query=query,
#             max_results=3
#         )

#         results = []
#         for r in response["results"]:
#             results.append({
#                 "url": r["url"],
#                 "title": r["title"],
#                 "snippet": r["content"]
#             })

#         return results

#     except Exception as e:
#         print("Search error:", e)
#         return []


# # ==========================================
# # 8. NODE 2: SEARCH
# # ==========================================
# def search_node(state: State):
#     pro_urls = []
#     anti_urls = []

#     for q in state["pro_queries"]:
#         pro_urls.extend(search_web(q))

#     for q in state["anti_queries"]:
#         anti_urls.extend(search_web(q))

#     # deduplicate
#     pro_urls = list({r["url"]: r for r in pro_urls}.values())[:2]
#     anti_urls = list({r["url"]: r for r in anti_urls}.values())[:2]

#     return {
#         "pro_urls": pro_urls,
#         "anti_urls": anti_urls
#     }


# # ==========================================
# # 9. SCRAPER
# # ==========================================
# def scrape(url):
#     try:
#         res = requests.get(url, timeout=5)
#         soup = BeautifulSoup(res.text, "html.parser")

#         text = soup.get_text(separator=" ", strip=True)
#         return text[:2000]

#     except Exception as e:
#         print("Scrape error:", e)
#         return ""


# # ==========================================
# # 10. NODE 3: SCRAPE
# # ==========================================
# def scrape_node(state: State):
#     pro_docs = [scrape(r["url"]) for r in state["pro_urls"]]
#     anti_docs = [scrape(r["url"]) for r in state["anti_urls"]]

#     return {
#         "pro_docs": pro_docs,
#         "anti_docs": anti_docs
#     }


# # ==========================================
# # 11. NODE 4: VERIFY
# # ==========================================
# def verify_node(state: State):
#     prompt = f"""
#     Return ONLY JSON.

#     Offer: {state['offer_name']}
#     Feature: {state['feature']}

#     PRO:
#     {state['pro_docs']}

#     ANTI:
#     {state['anti_docs']}

#     Output:
#     {{
#       "pro_confidence": number,
#       "anti_confidence": number,
#       "composite_score": number,
#       "bundle_type": "Always/Limited/Add-on/Never",
#       "summary": "short explanation"
#     }}
#     """

#     res = call_llm(prompt)
#     return {"result": safe_json_parse(res)}


# # ==========================================
# # 12. LANGGRAPH
# # ==========================================
# builder = StateGraph(State)

# builder.add_node("planner", query_planner)
# builder.add_node("search", search_node)
# builder.add_node("scrape", scrape_node)
# builder.add_node("verify", verify_node)

# builder.set_entry_point("planner")

# builder.add_edge("planner", "search")
# builder.add_edge("search", "scrape")
# builder.add_edge("scrape", "verify")
# builder.add_edge("verify", END)

# graph = builder.compile()


# # ==========================================
# # 13. RUN TEST
# # ==========================================
# if __name__ == "__main__":
#     input_state = {
#         "offer_name": "Zoom Workplace Pro",
#         "vendor_name": "Zoom",
#         "feature": "AI meeting summaries"
#     }

#     result = graph.invoke(input_state)

#     print("\n===== FINAL RESULT =====\n")
#     print(json.dumps(result["result"], indent=2))

# import json
# import requests
# from bs4 import BeautifulSoup
# from typing import TypedDict, List, Dict, Any

# from langgraph.graph import StateGraph, END
# from langchain_ollama import ChatOllama


# # -------------------------------
# # LLM SETUP (TinyLlama)
# # -------------------------------
# llm = ChatOllama(model="tinyllama",temperature=0)

# # -------------------------------
# # STATE SCHEMA
# # -------------------------------
# class State(TypedDict):
#     offer_name: str
#     vendor_name: str
#     feature: str

#     pro_queries: List[str]
#     anti_queries: List[str]

#     pro_urls: List[str]
#     anti_urls: List[str]

#     pro_docs: List[str]
#     anti_docs: List[str]

#     verification: Dict[str, Any]


# # -------------------------------
# # HELPER: SAFE LLM CALL
# # -------------------------------
# def safe_llm(prompt: str) -> str:
#     try:
#         res = llm.invoke(prompt)
#         return res.content
#     except Exception as e:
#         print("LLM ERROR:", e)
#         return ""


# # -------------------------------
# # NODE 1: QUERY PLANNER
# # -------------------------------
# def query_planner(state: State):
#     prompt = f"""
#     Generate 2 search queries to SUPPORT and 2 to OPPOSE:

#     Offer: {state['offer_name']}
#     Feature: {state['feature']}

#     Return plain text, each query in new line.
#     """

#     output = safe_llm(prompt)

#     lines = [l.strip() for l in output.split("\n") if l.strip()]

#     state["pro_queries"] = lines[:2]
#     state["anti_queries"] = lines[2:4]

#     return state


# # -------------------------------
# # NODE 2: SEARCH (DUMMY)
# # -------------------------------
# def search_node(state: State):
#     # ⚠️ No API → using mock URLs (safe for demo)
#     state["pro_urls"] = [
#         "https://example.com/pro1",
#         "https://example.com/pro2"
#     ]

#     state["anti_urls"] = [
#         "https://example.com/anti1",
#         "https://example.com/anti2"
#     ]

#     return state


# # -------------------------------
# # NODE 3: SCRAPER
# # -------------------------------
# def scrape_url(url):
#     try:
#         res = requests.get(url, timeout=5)
#         soup = BeautifulSoup(res.text, "html.parser")
#         return soup.get_text()[:1000]
#     except:
#         return ""


# def scraper_node(state: State):
#     state["pro_docs"] = [scrape_url(u) for u in state["pro_urls"]]
#     state["anti_docs"] = [scrape_url(u) for u in state["anti_urls"]]

#     return state


# # -------------------------------
# # NODE 4: VERIFICATION (HYBRID)
# # -------------------------------
# def verification_node(state: State):
#     pro_docs = state["pro_docs"]
#     anti_docs = state["anti_docs"]

#     # Simple deterministic scoring
#     pro_score = len([d for d in pro_docs if d]) * 30
#     anti_score = len([d for d in anti_docs if d]) * 20

#     pro_score = min(pro_score, 100)
#     anti_score = min(anti_score, 100)

#     composite = pro_score * (1 - anti_score / 100)

#     # LLM summary (light usage)
#     summary_prompt = f"""
#     Summarize evidence for:

#     Offer: {state['offer_name']}
#     Feature: {state['feature']}

#     Pro Evidence: {pro_docs}
#     Anti Evidence: {anti_docs}
#     """

#     summary = safe_llm(summary_prompt)

#     state["verification"] = {
#         "pro_confidence": pro_score,
#         "anti_confidence": anti_score,
#         "composite_confidence": round(composite, 2),
#         "predicted_bundle_type": "Limited",
#         "evidence_summary": summary.strip()[:300]
#     }

#     return state


# # -------------------------------
# # NODE 5: REPORT
# # -------------------------------
# def report_node(state: State):
#     print("\n===== FINAL RESULT =====\n")

#     v = state["verification"]

#     print(f"Offer: {state['offer_name']}")
#     print(f"Feature: {state['feature']}\n")

#     print(f"Pro Confidence: {v['pro_confidence']}")
#     print(f"Anti Confidence: {v['anti_confidence']}")
#     print(f"Composite Score: {v['composite_confidence']}")
#     print(f"Bundle Type: {v['predicted_bundle_type']}\n")

#     print("Summary:")
#     print(v["evidence_summary"])

#     return state


# # -------------------------------
# # BUILD GRAPH
# # -------------------------------
# builder = StateGraph(State)

# builder.add_node("planner", query_planner)
# builder.add_node("search", search_node)
# builder.add_node("scrape", scraper_node)
# builder.add_node("verify", verification_node)
# builder.add_node("report", report_node)

# builder.set_entry_point("planner")

# builder.add_edge("planner", "search")
# builder.add_edge("search", "scrape")
# builder.add_edge("scrape", "verify")
# builder.add_edge("verify", "report")
# builder.add_edge("report", END)

# graph = builder.compile()


# # -------------------------------
# # RUN
# # -------------------------------
# if __name__ == "__main__":
#     input_state = {
#         "offer_name": "Zoom Workplace Pro",
#         "vendor_name": "Zoom",
#         "feature": "AI meeting summaries"
#     }

#     result = graph.invoke(input_state)
# # ================================
# # IMPORTS
# # ================================
# import os
# import json
# import requests
# from bs4 import BeautifulSoup
# from typing import TypedDict, List, Dict

# from langgraph.graph import StateGraph, START, END
# from langchain_ollama import ChatOllama
# from tavily import TavilyClient


# from dotenv import load_dotenv
# import os

# load_dotenv()

# # ================================
# # SETUP
# # ================================

# # 🔹 Ollama TinyLlama
# llm = ChatOllama(
#     model="tinyllama",
#     temperature=0
# )

# # 🔹 Tavily
# tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))


# # ================================
# # STATE SCHEMA
# # ================================

# class State(TypedDict):
#     offer_name: str
#     vendor_name: str
#     feature: str

#     pro_queries: List[str]
#     anti_queries: List[str]

#     pro_urls: List[Dict]
#     anti_urls: List[Dict]

#     pro_docs: List[Dict]
#     anti_docs: List[Dict]

#     result: Dict


# # ================================
# # HELPER: LLM CALL
# # ================================

# # def call_llm(prompt: str):
# #     response = llm.invoke(prompt)
# #     return response.content

# def safe_llm(prompt: str, retries: int = 2) -> str:
#     for attempt in range(retries):
#         try:
#             res = llm.invoke(prompt)

#             if res and res.content:
#                 return res.content

#         except Exception as e:
#             print(f"LLM ERROR (attempt {attempt+1}):", e)

#     # final fallback
#     return "{}"
# ================================
# NODE 1: QUERY PLANNER
# ================================

# def query_planner(state: State):
#     prompt = f"""
# Generate JSON with:
# - pro_queries (3)
# - anti_queries (3)

# Offer: {state['offer_name']}
# Feature: {state['feature']}

# Output JSON only.
# """

#     res = call_llm(prompt)

#     try:
#         data = json.loads(res)
#     except:
#         data = {
#             "pro_queries": [f"{state['offer_name']} {state['feature']}"],
#             "anti_queries": [f"{state['offer_name']} missing {state['feature']}"]
#         }

#     return {
#         "pro_queries": data["pro_queries"],
#         "anti_queries": data["anti_queries"]
#     }

# def query_planner(state: State):
#     prompt = f"""
# Generate JSON:
# {{
#   "pro_queries": [3 queries],
#   "anti_queries": [3 queries]
# }}

# Offer: {state['offer_name']}
# Feature: {state['feature']}

# Only return JSON.
# """

#     res = safe_llm(prompt)

#     try:
#         data = json.loads(res)

#         # 🔥 SAFETY CHECK
#         if isinstance(data, dict):
#             return {
#                 "pro_queries": data.get("pro_queries", []),
#                 "anti_queries": data.get("anti_queries", [])
#             }

#         # ⚠️ if LLM returned list
#         elif isinstance(data, list):
#             return {
#                 "pro_queries": data,
#                 "anti_queries": []
#             }

#     except Exception as e:
#         print("JSON ERROR:", e)

#     # 🔥 FINAL FALLBACK
#     return {
#         "pro_queries": [f"{state['offer_name']} {state['feature']}"],
#         "anti_queries": [f"{state['offer_name']} missing {state['feature']}"]
#     }
# # ================================
# # NODE 2a: PRO SEARCH
# # ================================

# def pro_search(state: State):
#     results = []

#     for q in state["pro_queries"]:
#         res = tavily.search(q, max_results=2)
#         results.extend(res["results"])

#     return {"pro_urls": results}


# # ================================
# # NODE 2b: ANTI SEARCH
# # ================================

# def anti_search(state: State):
#     results = []

#     for q in state["anti_queries"]:
#         res = tavily.search(q, max_results=2)
#         results.extend(res["results"])

#     return {"anti_urls": results}


# # ================================
# # HELPER: SCRAPE
# # ================================

# def scrape_url(url):
#     try:
#         r = requests.get(url, timeout=5)
#         soup = BeautifulSoup(r.text, "html.parser")
#         text = soup.get_text(separator=" ", strip=True)
#         return text[:1500]
#     except:
#         return "Failed to fetch"


# # ================================
# # NODE 3: SCRAPER
# # ================================

# def scraper(state: State):
#     pro_docs = []
#     anti_docs = []

#     for item in state.get("pro_urls", [])[:2]:
#         content = scrape_url(item["url"])
#         pro_docs.append({
#             "url": item["url"],
#             "content": content
#         })

#     for item in state.get("anti_urls", [])[:2]:
#         content = scrape_url(item["url"])
#         anti_docs.append({
#             "url": item["url"],
#             "content": content
#         })

#     return {
#         "pro_docs": pro_docs,
#         "anti_docs": anti_docs
#     }


# # ================================
# # NODE 4: VERIFICATION
# # ================================

# def verifier(state: State):
#     prompt = f"""
# You are a strict evaluator.

# Feature: {state['feature']}
# Offer: {state['offer_name']}

# Pro Evidence:
# {state['pro_docs']}

# Anti Evidence:
# {state['anti_docs']}

# Return JSON:
# {{
#   "pro_score": number,
#   "anti_score": number,
#   "verdict": "Supported/Not Supported"
# }}
# """

#     res = call_llm(prompt)

#     try:
#         data = json.loads(res)
#     except:
#         data = {
#             "pro_score": 50,
#             "anti_score": 50,
#             "verdict": "Uncertain"
#         }

#     return {"result": data}


# # ================================
# # GRAPH BUILDING (IMPORTANT PART)
# # ================================

# builder = StateGraph(State)

# # Nodes
# builder.add_node("planner", query_planner)
# builder.add_node("pro_search", pro_search)
# builder.add_node("anti_search", anti_search)
# builder.add_node("scraper", scraper)
# builder.add_node("verifier", verifier)

# # Edges (🔥 PARALLEL FAN-OUT)
# builder.add_edge(START, "planner")

# builder.add_edge("planner", "pro_search")
# builder.add_edge("planner", "anti_search")

# # Join both into scraper
# builder.add_edge("pro_search", "scraper")
# builder.add_edge("anti_search", "scraper")

# builder.add_edge("scraper", "verifier")
# builder.add_edge("verifier", END)

# graph = builder.compile()


# # ================================
# # RUN TEST
# # ================================

# if __name__ == "__main__":
#     input_state = {
#         "offer_name": "Zoom Pro",
#         "vendor_name": "Zoom",
#         "feature": "AI meeting summary"
#     }

#     result = graph.invoke(input_state)

#     print("\n FINAL OUTPUT:\n")
#     print(json.dumps(result["result"], indent=2))


# # ================================
# # IMPORTS
# # ================================
# import os
# import json
# import requests
# from bs4 import BeautifulSoup
# from typing import TypedDict, List, Dict

# from dotenv import load_dotenv
# from langgraph.graph import StateGraph, START, END
# from tavily import TavilyClient
# from langchain_groq import ChatGroq


# # ================================
# # LOAD ENV
# # ================================
# load_dotenv()

# # ================================
# # LLM SETUP (GROQ)
# # ================================
# llm = ChatGroq(
#     model="llama-3.1-8b-instant",
#     temperature=0
# )

# # ================================
# # TAVILY SETUP
# # ================================
# tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))


# # ================================
# # STATE
# # ================================
# class State(TypedDict):
#     offer_name: str
#     vendor_name: str
#     feature: str

#     pro_queries: List[str]
#     anti_queries: List[str]

#     pro_urls: List[Dict]
#     anti_urls: List[Dict]

#     pro_docs: List[Dict]
#     anti_docs: List[Dict]

#     result: Dict


# # ================================
# # SAFE LLM
# # ================================
# # def safe_llm(prompt: str, retries: int = 2):
# #     for i in range(retries):
# #         try:
# #             res = llm.invoke(prompt)
# #             if res and res.content:
# #                 return res.content
# #         except Exception as e:
# #             print(f"LLM ERROR (attempt {i+1}):", e)

# #     return "{}"

# def safe_llm(prompt: str) -> str:
#     try:
#         res = llm.invoke(prompt)
#         print("\n--- LLM RAW OUTPUT ---")
#         print(res.content)
#         print("----------------------\n")
#         return res.content
#     except Exception as e:
#         print("LLM ERROR:", e)
#         return ""
# # ================================
# # NODE 1: QUERY PLANNER
# # ================================
# def query_planner(state: State):

#     prompt = f"""
# You MUST return valid JSON.

# Format:
# {{
#   "pro_queries": ["q1","q2","q3"],
#   "anti_queries": ["q1","q2","q3"]
# }}

# Offer: {state['offer_name']}
# Feature: {state['feature']}

# Return ONLY JSON.
# """

#     res = safe_llm(prompt)

#     try:
#         data = json.loads(res)

#         if isinstance(data, dict):
#             return {
#                 "pro_queries": data.get("pro_queries", []),
#                 "anti_queries": data.get("anti_queries", [])
#             }

#         elif isinstance(data, list):
#             return {
#                 "pro_queries": data,
#                 "anti_queries": []
#             }

#     except Exception as e:
#         print("Planner JSON ERROR:", e)

#     # fallback
#     return {
#         "pro_queries": [f"{state['offer_name']} {state['feature']}"],
#         "anti_queries": [f"{state['offer_name']} missing {state['feature']}"]
#     }


# # ================================
# # NODE 2a: PRO SEARCH
# # ================================
# def pro_search(state: State):
#     results = []

#     for q in state["pro_queries"]:
#         try:
#             res = tavily.search(q, max_results=2)
#             results.extend(res["results"])
#         except Exception as e:
#             print("Pro search error:", e)

#     return {"pro_urls": results}


# # ================================
# # NODE 2b: ANTI SEARCH
# # ================================
# def anti_search(state: State):
#     results = []

#     for q in state["anti_queries"]:
#         try:
#             res = tavily.search(q, max_results=2)
#             results.extend(res["results"])
#         except Exception as e:
#             print("Anti search error:", e)

#     return {"anti_urls": results}


# # ================================
# # SCRAPER
# # ================================
# def scrape_url(url):
#     try:
#         r = requests.get(url, timeout=5)
#         soup = BeautifulSoup(r.text, "html.parser")
#         text = soup.get_text(separator=" ", strip=True)
#         return text[:1500]
#     except:
#         return "Failed to fetch"


# # ================================
# # NODE 3: SCRAPER
# # ================================
# def scraper(state: State):

#     pro_docs = []
#     anti_docs = []

#     for item in state.get("pro_urls", [])[:2]:
#         content = scrape_url(item["url"])
#         pro_docs.append({
#             "url": item["url"],
#             "content": content
#         })

#     for item in state.get("anti_urls", [])[:2]:
#         content = scrape_url(item["url"])
#         anti_docs.append({
#             "url": item["url"],
#             "content": content
#         })

#     return {
#         "pro_docs": pro_docs,
#         "anti_docs": anti_docs
#     }


# # ================================
# # NODE 4: VERIFIER
# # ================================
# def verifier(state: State):

#     prompt = f"""
# You are a strict evaluator.

# Feature: {state['feature']}
# Offer: {state['offer_name']}

# Pro Evidence:
# {state['pro_docs']}

# Anti Evidence:
# {state['anti_docs']}

# Return JSON:
# {{
#   "pro_score": number,
#   "anti_score": number,
#   "verdict": "Supported/Not Supported",
#   "summary": "2 lines explanation"
# }}
# """

#     res = safe_llm(prompt)

#     try:
#         data = json.loads(res)
#     except:
#         data = {
#             "pro_score": 50,
#             "anti_score": 50,
#             "verdict": "Uncertain",
#             "summary": "LLM failed, fallback used"
#         }

#     return {"result": data}


# # ================================
# # GRAPH
# # ================================
# builder = StateGraph(State)

# builder.add_node("planner", query_planner)
# builder.add_node("pro_search", pro_search)
# builder.add_node("anti_search", anti_search)
# builder.add_node("scraper", scraper)
# builder.add_node("verifier", verifier)

# builder.add_edge(START, "planner")

# # 🔥 parallel fan-out
# builder.add_edge("planner", "pro_search")
# builder.add_edge("planner", "anti_search")

# # 🔥 join
# builder.add_edge("pro_search", "scraper")
# builder.add_edge("anti_search", "scraper")

# builder.add_edge("scraper", "verifier")
# builder.add_edge("verifier", END)

# graph = builder.compile()


# # ================================
# # RUN
# # ================================
# if __name__ == "__main__":

#     input_state = {
#         "offer_name": "Zoom Workplace Pro",
#         "vendor_name": "Zoom",
#         "feature": "AI meeting summaries"
#     }

#     result = graph.invoke(input_state)

#     print("\n FINAL OUTPUT:\n")
#     print(json.dumps(result["result"], indent=2))

# import os
# import re
# import json
# from typing import TypedDict, List
# from dotenv import load_dotenv

# from langgraph.graph import StateGraph, END
# from langchain_groq import ChatGroq
# from tavily import TavilyClient

# # -----------------------------
# # LOAD ENV
# # -----------------------------
# load_dotenv()

# # -----------------------------
# # LLM (Groq)
# # -----------------------------
# llm = ChatGroq(
#     model="llama-3.1-8b-instant",
#     temperature=0
# )

# # -----------------------------
# # TAVILY
# # -----------------------------
# tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

# # -----------------------------
# # STATE
# # -----------------------------
# class State(TypedDict):
#     offer: str
#     feature: str
#     pro_queries: List[str]
#     anti_queries: List[str]
#     pro_urls: List[str]
#     anti_urls: List[str]
#     pro_docs: List[str]
#     anti_docs: List[str]
#     result: dict


# # -----------------------------
# # SAFE LLM
# # -----------------------------
# def safe_llm(prompt: str) -> str:
#     try:
#         res = llm.invoke(prompt)
#         print("\n--- LLM RAW OUTPUT ---")
#         print(res.content)
#         print("----------------------\n")
#         return res.content
#     except Exception as e:
#         print("LLM ERROR:", e)
#         return ""


# # -----------------------------
# # JSON EXTRACTOR (CRITICAL)
# # -----------------------------
# def extract_json(text: str):
#     try:
#         text = re.sub(r"```json|```", "", text).strip()
#         match = re.search(r"\{.*\}", text, re.DOTALL)
#         if match:
#             return json.loads(match.group())
#     except Exception as e:
#         print("JSON ERROR:", e)
#     return None


# # -----------------------------
# # NODE 1: QUERY PLANNER
# # -----------------------------
# def query_planner(state: State):
#     prompt = f"""
# Generate search queries.

# Offer: {state['offer']}
# Feature: {state['feature']}

# Return JSON:
# {{
#   "pro_queries": [],
#   "anti_queries": []
# }}
# """

#     response = safe_llm(prompt)
#     data = extract_json(response)

#     if not data:
#         data = {
#             "pro_queries": [f"{state['offer']} {state['feature']}"],
#             "anti_queries": [f"{state['offer']} missing {state['feature']}"]
#         }

#     return {
#         "pro_queries": data["pro_queries"],
#         "anti_queries": data["anti_queries"]
#     }


# # -----------------------------
# # NODE 2a: PRO SEARCH
# # -----------------------------
# def pro_search(state: State):
#     urls = []

#     for q in state["pro_queries"]:
#         try:
#             res = tavily.search(q, max_results=2)
#             urls.extend([r["url"] for r in res["results"]])
#         except:
#             pass

#     return {"pro_urls": urls}


# # -----------------------------
# # NODE 2b: ANTI SEARCH
# # -----------------------------
# def anti_search(state: State):
#     urls = []

#     for q in state["anti_queries"]:
#         try:
#             res = tavily.search(q, max_results=2)
#             urls.extend([r["url"] for r in res["results"]])
#         except:
#             pass

#     return {"anti_urls": urls}


# # -----------------------------
# # NODE 3: SCRAPER (SIMPLIFIED)
# # -----------------------------
# def scraper(state: State):
#     # (POC: we skip real scraping for speed)
#     pro_docs = state["pro_urls"]
#     anti_docs = state["anti_urls"]

#     return {
#         "pro_docs": pro_docs,
#         "anti_docs": anti_docs
#     }


# # -----------------------------
# # NODE 4: VERIFICATION
# # -----------------------------
# def verify(state: State):
#     prompt = f"""
# Return ONLY JSON.

# {{
#   "pro_score": number,
#   "anti_score": number,
#   "verdict": "Always | Limited | Add-on | Never",
#   "summary": "short explanation"
# }}

# Pro Evidence:
# {state['pro_docs']}

# Anti Evidence:
# {state['anti_docs']}
# """

#     response = safe_llm(prompt)
#     data = extract_json(response)

#     if not data:
#         return {
#             "result": {
#                 "pro_score": 50,
#                 "anti_score": 50,
#                 "verdict": "Uncertain",
#                 "summary": "LLM parsing failed"
#             }
#         }

#     # validate verdict
#     valid = ["Always", "Limited", "Add-on", "Never"]
#     if data.get("verdict") not in valid:
#         data["verdict"] = "Limited"

#     return {"result": data}


# # -----------------------------
# # BUILD GRAPH
# # -----------------------------
# builder = StateGraph(State)

# builder.add_node("planner", query_planner)
# builder.add_node("pro_search", pro_search)
# builder.add_node("anti_search", anti_search)
# builder.add_node("scraper", scraper)
# builder.add_node("verify", verify)

# # FLOW
# builder.set_entry_point("planner")

# # fan-out (parallel)
# builder.add_edge("planner", "pro_search")
# builder.add_edge("planner", "anti_search")

# # join
# builder.add_edge("pro_search", "scraper")
# builder.add_edge("anti_search", "scraper")

# builder.add_edge("scraper", "verify")
# builder.add_edge("verify", END)

# graph = builder.compile()


# # -----------------------------
# # RUN
# # -----------------------------
# if __name__ == "__main__":
#     input_state = {
#         "offer": "Zoom Workplace Pro",
#         "feature": "AI meeting summaries"
#     }

#     result = graph.invoke(input_state)

#     print("\nFINAL OUTPUT:\n")
#     print(json.dumps(result["result"], indent=2))

# import os
# import re
# import json
# import requests
# from typing import TypedDict, List
# from dotenv import load_dotenv
# from bs4 import BeautifulSoup

# from langgraph.graph import StateGraph, END
# from langchain_groq import ChatGroq
# from tavily import TavilyClient

# # -----------------------------
# # LOAD ENV
# # -----------------------------
# load_dotenv()

# # -----------------------------
# # LLM (Groq)
# # -----------------------------
# llm = ChatGroq(
#     model="llama-3.1-8b-instant",
#     temperature=0
# )

# # -----------------------------
# # TAVILY
# # -----------------------------
# tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

# # -----------------------------
# # STATE
# # -----------------------------
# class State(TypedDict):
#     offer: str
#     feature: str
#     pro_queries: List[str]
#     anti_queries: List[str]
#     pro_urls: List[str]
#     anti_urls: List[str]
#     pro_docs: List[str]
#     anti_docs: List[str]
#     result: dict


# # -----------------------------
# # SAFE LLM
# # -----------------------------
# def safe_llm(prompt: str) -> str:
#     try:
#         res = llm.invoke(prompt)
#         print("\n--- LLM RAW OUTPUT ---")
#         print(res.content)
#         print("----------------------\n")
#         return res.content
#     except Exception as e:
#         print("LLM ERROR:", e)
#         return ""


# # -----------------------------
# # EXTRACT QUERIES (MULTI JSON)
# # -----------------------------
# def extract_queries(text: str):
#     pro, anti = [], []

#     text = re.sub(r"```json|```", "", text)
#     matches = re.findall(r"\{.*?\}", text, re.DOTALL)

#     for m in matches:
#         try:
#             data = json.loads(m)
#             if "pro_queries" in data:
#                 pro.extend(data["pro_queries"])
#             if "anti_queries" in data:
#                 anti.extend(data["anti_queries"])
#         except:
#             continue

#     return {
#         "pro_queries": pro[:3],   # ✅ LIMIT TO 3
#         "anti_queries": anti[:3]
#     }


# # -----------------------------
# # EXTRACT JSON (VERIFY)
# # -----------------------------
# # def extract_json(text: str):
# #     try:
# #         text = re.sub(r"```json|```", "", text)
# #         match = re.search(r"\{.*\}", text, re.DOTALL)
# #         if match:
# #             return json.loads(match.group())
# #     except:
# #         pass
# #     return None

# def extract_json(text: str):
#     try:
#         # find JSON block inside messy text
#         match = re.search(r'\{.*\}', text, re.DOTALL)
#         if match:
#             return json.loads(match.group())
#     except Exception as e:
#         print("JSON ERROR:", e)
#     return {}


# # -----------------------------
# # NODE 1: QUERY PLANNER
# # -----------------------------
# def query_planner(state: State):
#     prompt = f"""
# Generate search queries.

# Offer: {state['offer']}
# Feature: {state['feature']}

# Return JSON with pro_queries and anti_queries.
# """

#     response = safe_llm(prompt)
#     data = extract_queries(response)

#     # fallback
#     if not data["pro_queries"]:
#         data["pro_queries"] = [f"{state['offer']} {state['feature']}"]
#     if not data["anti_queries"]:
#         data["anti_queries"] = [f"{state['offer']} missing {state['feature']}"]

#     return data


# # -----------------------------
# # NODE 2a: PRO SEARCH
# # -----------------------------
# def pro_search(state: State):
#     urls = []

#     for q in state["pro_queries"]:
#         try:
#             res = tavily.search(q, max_results=2)
#             urls.extend([r["url"] for r in res["results"]])
#         except:
#             pass

#     return {"pro_urls": list(set(urls))[:3]}  # max 3


# # -----------------------------
# # NODE 2b: ANTI SEARCH
# # -----------------------------
# def anti_search(state: State):
#     urls = []

#     for q in state["anti_queries"]:
#         try:
#             res = tavily.search(q, max_results=2)
#             urls.extend([r["url"] for r in res["results"]])
#         except:
#             pass

#     return {"anti_urls": list(set(urls))[:3]}


# # -----------------------------
# # SCRAPER FUNCTION
# # -----------------------------
# def scrape_url(url: str) -> str:
#     try:
#         headers = {
#             "User-Agent": "Mozilla/5.0"
#         }
#         r = requests.get(url, headers=headers, timeout=5)

#         soup = BeautifulSoup(r.text, "html.parser")

#         # remove scripts/styles
#         for tag in soup(["script", "style", "noscript"]):
#             tag.extract()

#         text = soup.get_text(separator=" ")

#         # clean + truncate
#         text = " ".join(text.split())
#         return text[:2000]

#     except Exception as e:
#         print("SCRAPE ERROR:", url, e)
#         return ""


# # -----------------------------
# # NODE 3: SCRAPER
# # -----------------------------
# def scraper(state: State):
#     pro_docs = [scrape_url(url) for url in state["pro_urls"]]
#     anti_docs = [scrape_url(url) for url in state["anti_urls"]]

#     return {
#         "pro_docs": pro_docs,
#         "anti_docs": anti_docs
#     }


# # -----------------------------
# # NODE 4: VERIFICATION
# # -----------------------------
# def verify(state: State):
#     prompt = f"""
# Return ONLY JSON.

# {{
#   "pro_score": number,
#   "anti_score": number,
#   "verdict": "Always | Limited | Add-on | Never",
#   "summary": "short explanation"
# }}

# Pro Evidence:
# {state['pro_docs']}

# Anti Evidence:
# {state['anti_docs']}
# """

#     response = safe_llm(prompt)
#     data = extract_json(response)

#     if not data:
#         return {
#             "result": {
#                 "pro_score": 50,
#                 "anti_score": 50,
#                 "verdict": "Uncertain",
#                 "summary": "LLM parsing failed"
#             }
#         }

#     valid = ["Always", "Limited", "Add-on", "Never"]
#     if data.get("verdict") not in valid:
#         data["verdict"] = "Limited"

#     return {"result": data}


# # -----------------------------
# # GRAPH
# # -----------------------------
# builder = StateGraph(State)

# builder.add_node("planner", query_planner)
# builder.add_node("pro_search", pro_search)
# builder.add_node("anti_search", anti_search)
# builder.add_node("scraper", scraper)
# builder.add_node("verify", verify)

# builder.set_entry_point("planner")

# # parallel
# builder.add_edge("planner", "pro_search")
# builder.add_edge("planner", "anti_search")

# # join
# builder.add_edge("pro_search", "scraper")
# builder.add_edge("anti_search", "scraper")

# builder.add_edge("scraper", "verify")
# builder.add_edge("verify", END)

# graph = builder.compile()


# # -----------------------------
# # RUN
# # -----------------------------
# if __name__ == "__main__":
#     input_state = {
#         "offer": "Zoom Workplace Pro",
#         "feature": "AI meeting summaries"
#     }

#     result = graph.invoke(input_state)

#     print("\nFINAL OUTPUT:\n")
#     print(json.dumps(result["result"], indent=2))

# import os
# import re
# import json
# import requests
# from bs4 import BeautifulSoup
# from dotenv import load_dotenv

# from tavily import TavilyClient
# from langgraph.graph import StateGraph, END

# # ✅ NEW OLLAMA IMPORT (no deprecation)
# from langchain_ollama import ChatOllama

# # ==============================
# # 🔑 ENV SETUP
# # ==============================
# load_dotenv()

# tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

# llm = ChatOllama(
#     model="tinyllama",
#     temperature=0
# )

# # ==============================
# # 🛡️ SAFE LLM CALL
# # ==============================
# def safe_llm(prompt: str) -> str:
#     try:
#         res = llm.invoke(prompt)
#         return res.content
#     except Exception as e:
#         print("LLM ERROR:", e)
#         return ""

# # ==============================
# # 🧠 JSON EXTRACTION (STRICT)
# # ==============================
# def extract_queries(text: str):
#     try:
#         text = re.sub(r"```json|```", "", text)

#         match = re.search(r"\{.*\}", text, re.DOTALL)
#         if not match:
#             return {"pro_queries": [], "anti_queries": []}

#         data = json.loads(match.group())

#         def clean(q_list):
#             cleaned = []
#             for q in q_list[:3]:   # ✅ LIMIT TO 3
#                 if isinstance(q, dict):
#                     cleaned.append(q.get("query", ""))
#                 else:
#                     cleaned.append(q)
#             return cleaned

#         return {
#             "pro_queries": clean(data.get("pro_queries", [])),
#             "anti_queries": clean(data.get("anti_queries", []))
#         }

#     except Exception as e:
#         print("QUERY PARSE ERROR:", e)
#         return {"pro_queries": [], "anti_queries": []}

# # ==============================
# # 🌐 SAFE SEARCH
# # ==============================
# def safe_search(query):
#     try:
#         return tavily.search(query=query, max_results=2)
#     except Exception as e:
#         print("SEARCH ERROR:", e)
#         return {"results": []}

# # ==============================
# # 📰 SCRAPER (ROBUST)
# # ==============================
# def scrape_url(url):
#     try:
#         headers = {"User-Agent": "Mozilla/5.0"}
#         res = requests.get(url, headers=headers, timeout=10)

#         soup = BeautifulSoup(res.text, "html.parser")
#         paragraphs = soup.find_all("p")

#         text = " ".join([p.get_text() for p in paragraphs])
#         return text[:1500]

#     except Exception as e:
#         print("SCRAPE ERROR:", url, e)
#         return ""

# # ==============================
# # 🧠 NODE 1: QUERY PLANNER
# # ==============================
# def query_planner(state):
#     prompt = f"""
# Return ONLY JSON. No explanation.

# Format:
# {{
#   "pro_queries": ["q1","q2","q3"],
#   "anti_queries": ["q1","q2","q3"]
# }}

# Topic: {state['topic']}
# """

#     raw = safe_llm(prompt)
#     print("\n--- LLM RAW OUTPUT ---\n", raw)

#     data = extract_queries(raw)

#     return {
#         "pro_queries": data["pro_queries"],
#         "anti_queries": data["anti_queries"]
#     }

# # ==============================
# # 🔍 NODE 2: SEARCH PRO
# # ==============================
# def search_pro(state):
#     results = []

#     for q in state["pro_queries"]:
#         res = safe_search(q)
#         for r in res.get("results", []):
#             content = scrape_url(r.get("url", ""))
#             if content:
#                 results.append(content)

#     return {"pro_evidence": results}

# # ==============================
# # 🔍 NODE 3: SEARCH ANTI
# # ==============================
# def search_anti(state):
#     results = []

#     for q in state["anti_queries"]:
#         res = safe_search(q)
#         for r in res.get("results", []):
#             content = scrape_url(r.get("url", ""))
#             if content:
#                 results.append(content)

#     return {"anti_evidence": results}

# # ==============================
# # ⚖️ NODE 4: SCORER
# # ==============================
# def scorer(state):
#     pro_text = " ".join(state.get("pro_evidence", []))[:2000]
#     anti_text = " ".join(state.get("anti_evidence", []))[:2000]

#     prompt = f"""
# Return ONLY JSON:

# {{
#   "pro_score": int,
#   "anti_score": int,
#   "verdict": "Always | Limited | Uncertain",
#   "summary": "text"
# }}

# Pro Evidence:
# {pro_text}

# Anti Evidence:
# {anti_text}
# """

#     raw = safe_llm(prompt)
#     print("\n--- LLM RAW OUTPUT ---\n", raw)

#     try:
#         data = json.loads(re.search(r"\{.*\}", raw, re.DOTALL).group())
#         return data
#     except:
#         return {
#             "pro_score": 50,
#             "anti_score": 50,
#             "verdict": "Uncertain",
#             "summary": "LLM failed, fallback used"
#         }

# # ==============================
# # 🧩 GRAPH BUILDING
# # ==============================
# builder = StateGraph(dict)

# builder.add_node("planner", query_planner)
# builder.add_node("pro_search", search_pro)
# builder.add_node("anti_search", search_anti)
# builder.add_node("scorer", scorer)

# builder.set_entry_point("planner")

# # ✅ PARALLEL EDGES (IMPORTANT 🔥)
# builder.add_edge("planner", "pro_search")
# builder.add_edge("planner", "anti_search")

# builder.add_edge("pro_search", "scorer")
# builder.add_edge("anti_search", "scorer")

# builder.add_edge("scorer", END)

# graph = builder.compile()

# # ==============================
# # ▶️ RUN
# # ==============================
# if __name__ == "__main__":
#     input_state = {
#         "topic": "Zoom Workplace Pro AI meeting summaries"
#     }

#     result = graph.invoke(input_state)

#     print("\n\nFINAL OUTPUT:\n")
#     print(json.dumps(result, indent=2))