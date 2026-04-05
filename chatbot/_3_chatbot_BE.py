from langgraph.graph import StateGraph,START,END,add_messages
from typing import TypedDict,Annotated
from langchain_core.messages import BaseMessage,HumanMessage
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.message import add_messages


load_dotenv()

llm= ChatOpenAI()

class ChatState(TypedDict):
    messages:Annotated [list[BaseMessage],add_messages]
    # here we can also use list[str] but all human message , ai message, system message, tool message inherit from base msg  
    # if we dont use reducer previous msgs will be replaced
    # we can use , operator.add but add message is more efficient to add base messages in langgraph

def chat_node_python(state:ChatState):
    messages= state['messages']
    response= llm.invoke(messages)
    return {'messages':[response]}

checkpointer=InMemorySaver()

graph= StateGraph(ChatState)


graph.add_node('chat_node',chat_node_python)

graph.add_edge(START,'chat_node')
graph.add_edge('chat_node',END)

chatbot=graph.compile(checkpointer=checkpointer)


