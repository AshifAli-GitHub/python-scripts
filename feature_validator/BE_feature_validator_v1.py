# ==========================================
# 1. IMPORTS
# ==========================================
import os
import json
import re
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from typing import TypedDict, List, Dict

import google.generativeai as genai
from langgraph.graph import StateGraph, END,START
from tavily import TavilyClient


# ==========================================
# 2. LOAD ENV + INIT GEMINI
# ==========================================
load_dotenv()

genai.configure(api_key=os.getenv("AIzaSyCf_XEAsyF48vmMD-82abe6ZQBN9qmRbcM"))

# ✅ USE WORKING MODEL
model = genai.GenerativeModel("gemini-2.5-flash")

# Tavily
tavily = TavilyClient(api_key=os.getenv("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"))


# ==========================================
# 3. SAFE JSON PARSER (VERY IMPORTANT)
# ==========================================
def safe_json_parse(text):
    try:
        return json.loads(text)
    except:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group())
        return {}


# ==========================================
# 4. STATE
# ==========================================
class State(TypedDict):
    offer_name: str
    vendor_name: str
    feature: str

    pro_queries: List[str]
    anti_queries: List[str]

    pro_urls: List[Dict]
    anti_urls: List[Dict]

    pro_docs: List[str]
    anti_docs: List[str]

    result: Dict


# ==========================================
# 5. GEMINI CALL
# ==========================================
def call_llm(prompt: str):
    response = model.generate_content(
        prompt,
        generation_config={
            "temperature": 0
        }
    )
    return response.text


# ==========================================
# 6. NODE 1: QUERY PLANNER
# ==========================================
def query_planner(state: State):
    prompt = f"""
    Return ONLY valid JSON. No explanation.

    Offer: {state['offer_name']}
    Feature: {state['feature']}

    Output:
    {{
      "pro": ["query1", "query2"],
      "anti": ["query1", "query2"]
    }}
    """

    res = call_llm(prompt)
    data = safe_json_parse(res)

    return {
        "pro_queries": data.get("pro", []),
        "anti_queries": data.get("anti", [])
    }


# ==========================================
# 7. SEARCH (TAVILY)
# ==========================================
def search_web(query):
    try:
        response = tavily.search(
            query=query,
            max_results=3
        )

        results = []
        for r in response["results"]:
            results.append({
                "url": r["url"],
                "title": r["title"],
                "snippet": r["content"]
            })

        return results

    except Exception as e:
        print("Search error:", e)
        return []


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

# ================================
# NODE 2a: PRO SEARCH
# ================================

def pro_search(state: State):
    results = []

    for q in state["pro_queries"]:
        res = tavily.search(q, max_results=2)
        results.extend(res["results"])

    return {"pro_urls": results}


# ================================
# NODE 2b: ANTI SEARCH
# ================================

def anti_search(state: State):
    results = []

    for q in state["anti_queries"]:
        res = tavily.search(q, max_results=2)
        results.extend(res["results"])

    return {"anti_urls": results}


# ==========================================
# 9. SCRAPER
# ==========================================
def scrape(url):
    try:
        res = requests.get(url, timeout=5)
        soup = BeautifulSoup(res.text, "html.parser")

        text = soup.get_text(separator=" ", strip=True)
        return text[:2000]

    except Exception as e:
        print("Scrape error:", e)
        return ""


# ==========================================
# 10. NODE 3: SCRAPE
# ==========================================
def scrape_node(state: State):
    pro_docs = [scrape(r["url"]) for r in state["pro_urls"]]
    anti_docs = [scrape(r["url"]) for r in state["anti_urls"]]

    return {
        "pro_docs": pro_docs,
        "anti_docs": anti_docs
    }


# ==========================================
# 11. NODE 4: VERIFY
# ==========================================
def verify_node(state: State):
    prompt = f"""
    Return ONLY JSON.

    Offer: {state['offer_name']}
    Feature: {state['feature']}

    PRO:
    {state['pro_docs']}

    ANTI:
    {state['anti_docs']}

    Output:
    {{
      "pro_confidence": number,
      "anti_confidence": number,
      "composite_score": number,
      "bundle_type": "Always/Limited/Add-on/Never",
      "summary": "short explanation"
    }}
    """

    res = call_llm(prompt)
    return {"result": safe_json_parse(res)}


# ==========================================
# 12. LANGGRAPH
# ==========================================
builder = StateGraph(State)

# builder.add_node("planner", query_planner)
# builder.add_node("search", search_node)
# builder.add_node("scrape", scrape_node)
# builder.add_node("verify", verify_node)

# builder.set_entry_point("planner")

# builder.add_edge("planner", "search")
# builder.add_edge("search", "scrape")
# builder.add_edge("scrape", "verify")
# builder.add_edge("verify", END)
# # Nodes
builder.add_node("planner", query_planner)
builder.add_node("pro_search", pro_search)
builder.add_node("anti_search", anti_search)
builder.add_node("scraper", scrape_node)
builder.add_node("verifier", verify_node)

# Edges (🔥 PARALLEL FAN-OUT)
builder.add_edge(START, "planner")

builder.add_edge("planner", "pro_search")
builder.add_edge("planner", "anti_search")

# Join both into scraper
builder.add_edge("pro_search", "scraper")
builder.add_edge("anti_search", "scraper")

builder.add_edge("scraper", "verifier")
builder.add_edge("verifier", END)

# graph = builder.compile()


graph = builder.compile()


# ==========================================
# 13. RUN TEST
# ==========================================
if __name__ == "__main__":
    input_state = {
        "offer_name": "Zoom Workplace Pro",
        "vendor_name": "Zoom",
        "feature": "AI meeting summaries"
    }

    result = graph.invoke(input_state)

    print("\n===== FINAL RESULT =====\n")
    print(json.dumps(result["result"], indent=2))
