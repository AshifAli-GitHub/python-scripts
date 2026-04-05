from langgraph.graph import StateGraph,START,END,add_messages
from typing import TypedDict,Annotated
from langchain_core.messages import BaseMessage,HumanMessage
from langchain_community.chat_models import ChatOllama
from dotenv import load_dotenv
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph.message import add_messages
import sqlite3

load_dotenv()

llm= ChatOllama(model="llama3")

class ChatState(TypedDict):
    messages:Annotated [list[BaseMessage],add_messages]
    # here we can also use list[str] but all human message , ai message, system message, tool message inherit from base msg  
    # if we dont use reducer previous msgs will be replaced
    # we can use , operator.add but add message is more efficient to add base messages in langgraph

def chat_node_python(state:ChatState):
    messages= state['messages']
    response= llm.invoke(messages)
    return {'messages':[response]}

conn=sqlite3.connect(database='chatbot.db',check_same_thread=False)
checkpointer=SqliteSaver(conn=conn)

graph= StateGraph(ChatState)


graph.add_node('chat_node',chat_node_python)

graph.add_edge(START,'chat_node')
graph.add_edge('chat_node',END)

chatbot=graph.compile(checkpointer=checkpointer)

# config={'configurable':{'thread_id':'thread_1'}}
# initial_state={'messages':[HumanMessage(content='hi my name is asif')]}
# response = chatbot.invoke(initial_state,config=config)
# print(response)

def retrieve_all_threads():
    all_threads=set()
    for checkpoint in checkpointer.list(None):
        all_threads.add(checkpoint.config['configurable']['thread_id'])

    return list(all_threads)

