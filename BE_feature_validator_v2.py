# ==========================================
# 1. IMPORTS
# ==========================================
import warnings
warnings.filterwarnings("ignore")
import os
import json
import re
import time
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from typing import TypedDict, List, Dict, Annotated

from google import genai
from langgraph.graph import StateGraph, END, START
from tavily import TavilyClient


# ==========================================
# 2. CONFIG
# ==========================================
CACHE_FILE = "cache.json"

load_dotenv()

# genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
# model = genai.GenerativeModel("gemini-2.5-flash")

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))


# ==========================================
# 3. REDUCER (🔥 IMPORTANT FIX)
# ==========================================
def merge_logs(a, b):
    if a is None:
        return b or []
    if b is None:
        return a
    return a + b


# ==========================================
# 4. CACHE UTILS
# ==========================================
def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    return {}


def save_cache(cache):
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)


# ==========================================
# 5. SAFE JSON PARSER
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
# 6. STATE (🔥 FIXED WITH ANNOTATED)
# ==========================================
class State(TypedDict):
    offer_name: str
    vendor_name: str
    feature: str

    cache_hit: bool
    cache_key: str

    pro_queries: List[str]
    anti_queries: List[str]

    pro_urls: List[Dict]
    anti_urls: List[Dict]

    pro_docs: List[str]
    anti_docs: List[str]

    result: Dict

    logs: Annotated[List[Dict], merge_logs]   # 🔥 FIX


# ==========================================
# 7. LLM CALL
# ==========================================
def call_llm(prompt: str):
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config={
            "temperature": 0
        }
    )
    return response.text


# ==========================================
# 8. NODE: CACHE CHECK
# ==========================================
def check_cache(state: State):
    start = time.time()

    cache = load_cache()
    key = f"{state['offer_name']}|{state['feature']}".lower()

    if key in cache:
        duration = time.time() - start
        return {
            "cache_hit": True,
            "cache_key": key,
            "result": cache[key],
            "logs": [{
                "step": "cache_hit",
                "time_sec": round(duration, 4),
                "timestamp": str(datetime.now())
            }]
        }

    duration = time.time() - start
    return {
        "cache_hit": False,
        "cache_key": key,
        "logs": [{
            "step": "cache_miss",
            "time_sec": round(duration, 4),
            "timestamp": str(datetime.now())
        }]
    }


# ==========================================
# 9. NODE: QUERY PLANNER
# ==========================================
def query_planner(state: State):
    start = time.time()

    prompt = f"""
    Return ONLY valid JSON.

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

    duration = time.time() - start

    return {
        "pro_queries": data.get("pro", []),
        "anti_queries": data.get("anti", []),
        "logs": [{
            "step": "planner",
            "time_sec": round(duration, 4),
            "timestamp": str(datetime.now())
        }]
    }


# ==========================================
# 10. NODE: PRO SEARCH
# ==========================================
def pro_search(state: State):
    start = time.time()

    results = []
    for q in state["pro_queries"]:
        res = tavily.search(q, max_results=2)
        results.extend(res["results"])

    duration = time.time() - start

    return {
        "pro_urls": results,
        "logs": [{
            "step": "pro_search",
            "time_sec": round(duration, 4),
            "timestamp": str(datetime.now())
        }]
    }


# ==========================================
# 11. NODE: ANTI SEARCH
# ==========================================
def anti_search(state: State):
    start = time.time()

    results = []
    for q in state["anti_queries"]:
        res = tavily.search(q, max_results=2)
        results.extend(res["results"])

    duration = time.time() - start

    return {
        "anti_urls": results,
        "logs": [{
            "step": "anti_search",
            "time_sec": round(duration, 4),
            "timestamp": str(datetime.now())
        }]
    }


# ==========================================
# 12. SCRAPER
# ==========================================
def scrape(url):
    try:
        res = requests.get(url, timeout=5)
        soup = BeautifulSoup(res.text, "html.parser")
        return soup.get_text(separator=" ", strip=True)[:2000]
    except:
        return ""


# ==========================================
# 13. NODE: SCRAPER
# ==========================================
def scrape_node(state: State):
    start = time.time()

    pro_docs = [scrape(r["url"]) for r in state["pro_urls"]]
    anti_docs = [scrape(r["url"]) for r in state["anti_urls"]]

    duration = time.time() - start

    return {
        "pro_docs": pro_docs,
        "anti_docs": anti_docs,
        "logs": [{
            "step": "scraper",
            "time_sec": round(duration, 4),
            "timestamp": str(datetime.now())
        }]
    }


# ==========================================
# 14. NODE: VERIFY
# ==========================================
def verify_node(state: State):
    start = time.time()

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
    parsed = safe_json_parse(res)

    # Save cache
    cache = load_cache()
    cache[state["cache_key"]] = parsed
    save_cache(cache)

    duration = time.time() - start

    return {
        "result": parsed,
        "logs": [{
            "step": "verify",
            "time_sec": round(duration, 4),
            "timestamp": str(datetime.now())
        }]
    }


# ==========================================
# 15. ROUTER
# ==========================================
def route_cache(state: State):
    if state["cache_hit"]:
        return END
    return "planner"


# ==========================================
# 16. BUILD GRAPH
# ==========================================
builder = StateGraph(State)

builder.add_node("cache_check", check_cache)
builder.add_node("planner", query_planner)
builder.add_node("pro_search", pro_search)
builder.add_node("anti_search", anti_search)
builder.add_node("scraper", scrape_node)
builder.add_node("verifier", verify_node)

builder.add_edge(START, "cache_check")
builder.add_conditional_edges("cache_check", route_cache)

builder.add_edge("planner", "pro_search")
builder.add_edge("planner", "anti_search")

builder.add_edge("pro_search", "scraper")
builder.add_edge("anti_search", "scraper")

builder.add_edge("scraper", "verifier")
builder.add_edge("verifier", END)

graph = builder.compile()


# ==========================================
# 17. RUN
# ==========================================
if __name__ == "__main__":
    # input_state = {
    #     "offer_name": "Zoom Workplace Pro",
    #     "vendor_name": "Zoom",
    #     "feature": "AI meeting summaries"
    # }

    input_state = {
        "offer_name": "Zoom Workplace Pro",
        "vendor_name": "Zoom",
        "feature": "AI meeting summaries"
    }

    result = graph.invoke(input_state)

    print("\n===== FINAL RESULT =====\n")
    print(json.dumps(result["result"], indent=2))

    print("\n===== LOGS =====\n")
    for log in result["logs"]:
        print(log)