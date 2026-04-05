#first impot streamlit
import streamlit as st
#import chatbot obj from backend 
from _3_chatbot_BE import chatbot
#import human_message
from langchain_core.messages import HumanMessage

#********************************** Session setup ************************

#define msg history
if 'msg_history' not in st.session_state:
    st.session_state['msg_history']=[]

#********************************** Main UI ******************************

#first print all stored msgs from msg history 
for msg in st.session_state['msg_history']:
    with st.chat_message(msg['role']):
        st.text(msg['content'])
        
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
#show user i/p as from assistance
    with st.chat_message('assistant'):
        #to stream any generator obj in streamlit 
        #st.write_stream(generator)
        ai_message= st.write_stream(
            message_chunk.content for message_chunk ,metadata in chatbot.stream(
                {'messages': [HumanMessage(content=user_input)]},
                config=config,
                stream_mode = 'messages'
            )
        )
#add msg in msg history with role
    st.session_state['msg_history'].append({'role':'assistant','content':ai_message})

