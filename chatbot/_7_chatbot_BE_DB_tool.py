from langgraph.graph import StateGraph,START,END,add_messages
from typing import TypedDict,Annotated
from langchain_core.messages import BaseMessage,HumanMessage

# from langchain_community.chat_models import ChatOllama
from langchain_groq import ChatGroq
from dotenv import load_dotenv
import os

from dotenv import load_dotenv
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph.message import add_messages
import sqlite3

from langgraph.prebuilt import ToolNode,tools_condition #whenever any tool used
from langchain_community.tools import DuckDuckGoSearchRun # prebuilt tool to access web
from langchain_core.tools import tool #to make any custom tool eg cal,stock price using API
import requests #when api calls in custom tool
import random #

load_dotenv()

llm = ChatGroq(
    groq_api_key=os.getenv("GROQ_API_KEY"),
    model_name="llama-3.3-70b-versatile",
    streaming=True
)

#tools 
search_tool=DuckDuckGoSearchRun(region="us-en")

@tool # decorator to make custom tool
def calculator (first_num:float,second_num:float,operation:str)->dict:
    #whenever we create any custom tool write string to give LLM basic intro of tool
    """perform a basic arithmatic operation on two numbers.
       supported operations : add, sub , mul , div
    """
    try:
        if operation=="add":
            result=first_num+second_num
        elif operation=="sub":
            result=first_num-second_num
        elif operation=="mul":
            result=first_num*second_num
        elif operation=="div":
            if second_num==0:
                return{"error":"division by zero is not allowed"}
            result=first_num/second_num
        else:
            return {"error":f"unsupported operation'{operation}'"}
        
        return {"first_num":first_num,"second_num":second_num,"operation":operation,"result":result}
    except Exception as e:
        return {"error":str(e)}
    

@tool
def get_stock_price(symbol:str) -> dict:
    """
        Fetch latest stock price for a given symbol (e.g.'AAPL','TSLA')
        using Alpha vantage with API key in the URL
    """
    url=f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey=UFDF3RD10RH8OBBF"
    r= requests.get(url)
    return r.json()

# make tool list 
tools = [get_stock_price,search_tool,calculator]

# make LLM tool aware
llm_with_tool=llm.bind_tools(tools)



class ChatState(TypedDict):
    messages:Annotated [list[BaseMessage],add_messages]


def chat_node_python(state:ChatState):
    messages= state['messages']
    #here instead of LLM we call LLM with tools 
    response= llm_with_tool.invoke(messages)
    return {'messages':[response]}

# make tool node using built in func ToolNode and paas created tools list 
tool_node=ToolNode(tools)

conn=sqlite3.connect(database='chatbot.db',check_same_thread=False)
checkpointer=SqliteSaver(conn=conn)

graph= StateGraph(ChatState)
graph.add_node('chat_node',chat_node_python)
graph.add_node("tools",tool_node)


graph.add_edge(START,'chat_node')
#if llm ask for a tool got to tool node else finish 
graph.add_conditional_edges("chat_node",tools_condition )
#to make loop btw tool node and chat node to ensure polished o/p and make multistep task possible
graph.add_edge('tools','chat_node')

chatbot=graph.compile(checkpointer=checkpointer)


def retrieve_all_threads():
    all_threads=set()
    for checkpoint in checkpointer.list(None):
        all_threads.add(checkpoint.config['configurable']['thread_id'])

    return list(all_threads)




