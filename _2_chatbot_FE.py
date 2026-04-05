# #sample code 1: basic i/p chatbot

# #first import streamlit
# import streamlit as st
# #who is messaging : what is msg
# with st.chat_message('user'):
#     st.text('Hi')
# with st.chat_message('assistant'):
#     st.text('how can i help you?')
# with st.chat_message('user'):
#     st.text('my name is niteesh')

# #to have chat input  -> only box appear to type -> no implementation further
# user_input= st.chat_input('type here')

# #to show typed msg as user next chat_message
# if user_input:
#     with st.chat_message('user'):
#         st.text(user_input)

#sample code 2 : copy chatbot

#first impot streamlit
import streamlit as st
#define msg history
#msg_history=[]
#above dict also gets reset everytime enter pressed -> all stored msg gone
#hence above simple python dict doesnot work 
#we use dict from streamlit which will remain intact untill we manually press refresh
#that dict is call session_state
#in session_state (dict) we will store our msg history (dict)
if 'msg_history' not in st.session_state:
    st.session_state['msg_history']=[]
   
#first print all stored msgs from msg history 
for message in st.session_state['msg_history']:
    with st.chat_message(message['role']):
        st.text(message['content'])\
        
#take i/p from user
user_input=st.chat_input('Type here')

#check user i/p 
if user_input:
#add msg in msg history with role
    st.session_state['msg_history'].append({'role':'user','content': user_input})
#show user i/p as from user
    with st.chat_message('user'):
        st.text(user_input)

#add msg in msg history with role
    st.session_state['msg_history'].append({'role':'assistant','content': user_input})
#show user i/p as from assistance
    with st.chat_message('assistant'):
        st.text(user_input)



#first impot streamlit
import streamlit as st
#import chatbot obj from backend 
from _2_chatbot_BE import chatbot
#import human_message
from langchain_core.messages import HumanMessage

#define msg history
if 'msg_history' not in st.session_state:
    st.session_state['msg_history']=[]
   
#first print all stored msgs from msg history 
for message in st.session_state['msg_history']:
    with st.chat_message(message['role']):
        st.text(message['content'])\
        
#take i/p from user
user_input=st.chat_input('Type here')

#check user i/p 
if user_input:
#add msg in msg history with role
    st.session_state['msg_history'].append({'role':'user','content': user_input})
#show user i/p as from user
    with st.chat_message('user'):
        st.text(user_input)
        
    config = {'configurable':{'thread_id':'thread-1'}}
    response = chatbot.invoke({'messages':[HumanMessage(content=user_input)]},config=config) 
    ai_message = response ['messages'][-1].content
#add msg in msg history with role
    st.session_state['msg_history'].append({'role':'assistant','content': ai_message })
#show ai_message as from assistance
    with st.chat_message('assistant'):
        st.text(ai_message)



