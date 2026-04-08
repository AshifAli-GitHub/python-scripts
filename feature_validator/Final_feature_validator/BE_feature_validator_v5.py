# backend.py

import os
import json
import re
import time
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from typing import TypedDict, List, Dict, Annotated

from groq import Groq
from langgraph.graph import StateGraph, END, START
from tavily import TavilyClient

# from langfuse import Langfuse
load_dotenv()
# langfuse = Langfuse()


os.environ["OTEL_SERVICE_NAME"] = "feature-validator"

# =========================
# CONFIG
# =========================


CACHE_FILE = "cache.json"

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))


# =========================
# REDUCER
# =========================
def merge_logs(a, b):
    if a is None:
        return b or []
    if b is None:
        return a
    return a + b


# =========================
# STATE
# =========================
class State(TypedDict):
    offer_name: str
    vendor_name: str
    feature: str

    cache_hit: bool
    cache_key: str
    cache_mode: str 

    pro_queries: List[str]
    anti_queries: List[str]

    pro_urls: List[Dict]
    anti_urls: List[Dict]

    pro_docs: List[str]
    anti_docs: List[str]

    result: Dict
    logs: Annotated[List[Dict], merge_logs]


# =========================
# UTILS
# =========================

def call_llm(prompt: str):
    res = groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        response_format={"type": "json_object"}  # critical fix
    )
    return res.choices[0].message.content


def call_llm_stream(prompt: str):
    stream = groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0,
        stream=True
    )

    for chunk in stream:
        if chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content



# =========================
# SAFE JSON PARSER (FIXED)
# =========================
def safe_json_parse(text):
    try:
        return json.loads(text)
    except:
        pass

    matches = re.findall(r"\{.*?\}", text, re.DOTALL)

    for m in matches:
        try:
            return json.loads(m)
        except:
            continue

    return {
        "summary": "Failed to parse JSON",
        "raw_output": text[:500]
    }

def load_cache():
    if os.path.exists(CACHE_FILE):
        return json.load(open(CACHE_FILE))
    return {}


def save_cache(cache):
    json.dump(cache, open(CACHE_FILE, "w"), indent=2)


# =========================
# NODES
# =========================

def check_cache(state: State):
    start = time.time()

    mode = state.get("cache_mode", "Use Cache")

    # 🚫 IGNORE CACHE
    if mode == "Ignore Cache":
        return {
            "cache_hit": False,
            "cache_key": "",
            "logs": [{
                "step": "cache_ignored",
                "type": "system",
                "time_sec": time.time() - start
            }]
        }

    cache = load_cache()
    key = f"{state['offer_name']}|{state['feature']}".lower()

    # 🔄 REFRESH CACHE
    if mode == "Refresh Cache":
        return {
            "cache_hit": False,
            "cache_key": key,
            "logs": [{
                "step": "cache_refresh",
                "type": "system",
                "time_sec": time.time() - start
            }]
        }

    # ✅ USE CACHE
    if key in cache:
        return {
            "cache_hit": True,
            "cache_key": key,
            "result": cache[key],
            "logs": [{
                "step": "cache_hit",
                "type": "system",
                "time_sec": time.time() - start
            }]
        }

    return {
        "cache_hit": False,
        "cache_key": key,
        "logs": [{
            "step": "cache_miss",
            "type": "system",
            "time_sec": time.time() - start
        }]
    }


def query_planner(state: State):
    start = time.time()

    prompt = f"""
    # Return JSON:
    # {{
    #   "pro": ["query1"],
    #   "anti": ["query1"]
    # }}
    Return ONLY JSON.

    {{
        "pro": ["query1", "query2"],
        "anti": ["query1", "query2"]
    }}
    Offer: {state['offer_name']}
    Feature: {state['feature']}
    """

    res = call_llm(prompt)
    data = safe_json_parse(res)

    return {
        "pro_queries": data.get("pro", []),
        "anti_queries": data.get("anti", []),
        "logs": [{
            "step": "planner",
            "type": "sequential",
            "output": data,
            "time_sec": time.time() - start
        }]
    }


def pro_search(state: State):
    start = time.time()

    results = []
    for q in state["pro_queries"]:
        results += tavily.search(q, max_results=2)["results"]

    return {
        "pro_urls": results,
        "logs": [{
            "step": "pro_search",
            "type": "parallel",
            "output_count": len(results),
            "time_sec": time.time() - start
        }]
    }


def anti_search(state: State):
    start = time.time()

    results = []
    for q in state["anti_queries"]:
        results += tavily.search(q, max_results=2)["results"]

    return {
        "anti_urls": results,
        "logs": [{
            "step": "anti_search",
            "type": "parallel",
            "output_count": len(results),
            "time_sec": time.time() - start
        }]
    }


def scrape(url):
    try:
        return BeautifulSoup(requests.get(url, timeout=5).text, "html.parser").get_text()[:2000]
    except:
        return ""


def scraper(state: State):
    start = time.time()

    pro_docs = [scrape(r["url"]) for r in state["pro_urls"]]
    anti_docs = [scrape(r["url"]) for r in state["anti_urls"]]

    return {
        "pro_docs": pro_docs,
        "anti_docs": anti_docs,
        "logs": [{
            "step": "scraper",
            "type": "join",
            "time_sec": time.time() - start
        }]
    }



def verifier(state: State):
    start = time.time()

    prompt = f"""
You are a product strategy analyst.

Evaluate whether a feature should be included in an offer.

Return ONLY a JSON object.
No markdown.
No explanation.
No extra text:

{{
  "pro_confidence": number (0-100),
  "anti_confidence": number (0-100),
  "composite_score": number (0-100),
  "bundle_type": "Always" | "Limited" | "Add-on" | "Never",
  "verdict": "Include" | "Avoid" | "Optional",
  "reasons": ["point1", "point2"],
  "risks": ["risk1", "risk2"],
  "summary": "final explanation"
}}

Scoring guidance:
- Strong pros, weak cons → Always
- Balanced → Limited
- Niche → Add-on
- Strong cons → Never

Offer: {state['offer_name']}
Vendor: {state['vendor_name']}
Feature: {state['feature']}

PRO EVIDENCE:
{state['pro_docs']}

ANTI EVIDENCE:
{state['anti_docs']}
"""

    full_text = ""

    # =========================
    # 🔥 STREAM TOKENS
    # =========================
    for token in call_llm_stream(prompt):
        full_text += token

        yield {
            "stream_token": token.replace("\n", " ")
        }

    # =========================
    # 🧠 PARSE FINAL OUTPUT
    # =========================
    parsed = safe_json_parse(full_text)

    # =========================
    # 🛡️ FALLBACK SAFETY
    # =========================
    parsed.setdefault("pro_confidence", 0)
    parsed.setdefault("anti_confidence", 0)
    parsed.setdefault("composite_score", 0)
    parsed.setdefault("bundle_type", "Limited")
    parsed.setdefault("verdict", "Optional")
    parsed.setdefault("reasons", [])
    parsed.setdefault("risks", [])
    parsed.setdefault("summary", "No summary generated")

    # =========================
    # 💾 CACHE SAVE
    # =========================
    
    if state.get("cache_mode") != "Ignore Cache":
        cache = load_cache()
        cache[state["cache_key"]] = parsed
        save_cache(cache)

    # =========================
    # ✅ FINAL OUTPUT (MANDATORY YIELD)
    # =========================
    yield {
        "result": parsed,
        "logs": [{
            "step": "verifier",
            "type": "decision",
            "time_sec": time.time() - start
        }]
    }

def route_cache(state: State):
    return END if state["cache_hit"] else "planner"


# =========================
# GRAPH
# =========================
builder = StateGraph(State)

builder.add_node("cache", check_cache)
builder.add_node("planner", query_planner)
builder.add_node("pro", pro_search)
builder.add_node("anti", anti_search)
builder.add_node("scraper", scraper)
builder.add_node("verifier", verifier)

builder.add_edge(START, "cache")
builder.add_conditional_edges("cache", route_cache)

builder.add_edge("planner", "pro")
builder.add_edge("planner", "anti")

builder.add_edge("pro", "scraper")
builder.add_edge("anti", "scraper")

builder.add_edge("scraper", "verifier")
builder.add_edge("verifier", END)

graph = builder.compile()


from langfuse import get_client

lf = get_client()

def stream_graph(input_state):

    with lf.start_as_current_observation(
        name="feature_validator_run"
    ) as span:

        span.update(input=input_state)

        final_output = None

        for event in graph.stream(input_state):

            if event:
                for node, output in event.items():

                    #  ONLY capture final result safely
                    if isinstance(output, dict) and "result" in output:
                        final_output = output["result"]

                yield event

        #  set output (fix undefined)
        span.update(output=final_output or {"status": "no_result"})

    lf.flush()
