from langgraph.graph import StateGraph,START,END,add_messages
from typing import TypedDict,Annotated
from langchain_core.messages import BaseMessage,HumanMessage
from langchain_community.chat_models import ChatOllama
from dotenv import load_dotenv
#from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver #LangGraph state (checkpoints) into a SQLite database asyncly 
from langgraph.graph.message import add_messages
#import sqlite3
import aiosqlite # for async DB opr using await

from langgraph.prebuilt import ToolNode,tools_condition #whenever any tool used
from langchain_community.tools import DuckDuckGoSearchRun # prebuilt tool to access web
from langchain_core.tools import tool,BaseTool #to make any custom tool eg cal,stock price using API
import requests #when api calls in custom tool
import random #

from langchain_mcp_adapters.client import MultiServerMCPClient # lets app call tools from MCP server
import asyncio # run async func  
import threading #run code in separate thread i.e parallely 


load_dotenv()

# dedicated async loop for backend tasks
_ASYNC_LOOP=asyncio.new_event_loop()
_ASYNC_THREAD= threading.Thread(target=_ASYNC_LOOP.run_forever,daemon=True)
_ASYNC_THREAD.start()


def _submit_async(core):
    return asyncio.run_coroutine_threadsafe(coro=_ASYNC_LOOP)

def run_async(coro):
    return _submit_async(coro).result()

def submit_async_task(coro):
    """Schedule a coroutine on the backend event loop."""
    return _submit_async(coro)

 

llm= ChatOllama(model="llama3")

#tools 
search_tool=DuckDuckGoSearchRun(region="us-en")

# instead of cal tool we are using MCP(local) for cal and MCP(remote) for expenses 
# MCP client for FastMCP server
client = MultiServerMCPClient(
    {
        "arith": {
            "transport": "stdio",
            "command": "python",          
            "args": ["C:/Users/asifn/.vscode/LangGraph/myenv/_8_basic_chatbot_MCP_server.py"],
            
        },
        "expense": {
            "transport": "streamable_http",  # if this fails, try "sse"
            "url": "https://splendid-gold-dingo.fastmcp.app/mcp"
        }
    }
)

@tool
def get_stock_price(symbol:str) -> dict:
    """
        Fetch latest stock price for a given symbol (e.g.'AAPL','TSLA')
        using Alpha vantage with API key in the URL
    """
    url=f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey=UFDF3RD10RH8OBBF"
    r= requests.get(url)
    return r.json()
# fetch all mcp tools 
def load_mcp_tools()-> list[BaseTool]:
    try:
        return run_async(client.get_tools())
    except Exception:
        return []
mcp_tools=load_mcp_tools()
# make tool list 
tools = [get_stock_price,search_tool,*mcp_tools]
# make LLM tool aware
llm_with_tool=llm.bind_tools(tools) if tool else llm

class ChatState(TypedDict):
    messages:Annotated [list[BaseMessage],add_messages]

async def chat_node_python(state:ChatState):
    messages= state['messages']
    #here instead of LLM we call LLM with tools 
    response= await llm_with_tool.invoke(messages)
    return {'messages':[response]}

# make tool node using built in func ToolNode and paas created tools list 
tool_node=ToolNode(tools) if tools else None

# conn=sqlite3.connect(database='chatbot.db',check_same_thread=False)
# checkpointer=SqliteSaver(conn=conn)

async def _init_checkpointer():
    conn= await aiosqlite.connect(database="chatbot.db")
    return AsyncSqliteSaver(conn)

checkpointer =run_async(_init_checkpointer())


graph= StateGraph(ChatState)
graph.add_node('chat_node',chat_node_python)
graph.add_node("tools",tool_node)

if tool_node:
    graph.add_edge(START,'chat_node')
    #if llm ask for a tool got to tool node else finish 
    graph.add_conditional_edges("chat_node",tools_condition )
    #to make loop btw tool node and chat node to ensure polished o/p and make multistep task possible
    graph.add_edge('tools','chat_node')
else:
    graph.add_edge('chat_node',END)

chatbot=graph.compile(checkpointer=checkpointer)


# def retrieve_all_threads():
#     all_threads=set()
#     for checkpoint in checkpointer.list(None):
#         all_threads.add(checkpoint.config['configurable']['thread_id'])

#     return list(all_threads)

async def _alist_threads():
    all_threads =set()
    async for checkpoint in checkpointer.alist(None):
        all_threads.add(checkpoint.config['configurable']['thread_id'])
    return list (all_threads)

def retrieve_all_threads():
    return run_async(_alist_threads())



