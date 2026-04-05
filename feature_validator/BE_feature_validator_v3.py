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

from google import genai
from langgraph.graph import StateGraph, END, START
from tavily import TavilyClient

# =========================
# CONFIG
# =========================
load_dotenv()

CACHE_FILE = "cache.json"

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
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
    res = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config={"temperature": 0}
    )
    return res.text


def safe_json_parse(text):
    try:
        return json.loads(text)
    except:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group())
        return {}


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
    cache = load_cache()
    key = f"{state['offer_name']}|{state['feature']}".lower()

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
    Return JSON:
    {{
      "pro": ["query1"],
      "anti": ["query1"]
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
    Return JSON:
    {{
      "summary": "..."
    }}

    PRO: {state['pro_docs']}
    ANTI: {state['anti_docs']}
    """

    res = call_llm(prompt)
    parsed = safe_json_parse(res)

    cache = load_cache()
    cache[state["cache_key"]] = parsed
    save_cache(cache)

    return {
        "result": parsed,
        "logs": [{
            "step": "verifier",
            "type": "sequential",
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


def run_graph(input_state):
    return graph.invoke(input_state)