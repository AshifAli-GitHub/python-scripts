#first impot streamlit
import streamlit as st
#import chatbot obj from backend 
from _7_chatbot_BE_DB_tool import chatbot,retrieve_all_threads
#import human_message
from langchain_core.messages import HumanMessage,AIMessage
#for dynamic thread id generation 
import uuid

#************************** utility function ***************************************

def generate_thread_id():
    thread_id= uuid.uuid4() # gives random new thread id
    return thread_id

def reset_chat():
    thread_id= generate_thread_id()
    st.session_state['thread_id']=thread_id
    add_thread(st.session_state['thread_id'])
    st.session_state['msg_history']=[]

def add_thread(thread_id):
    if thread_id not in st.session_state ['chat_thread']:
        st.session_state['chat_thread'].append(thread_id)


def load_conversation(thread_id):
    config={'configurable':{'thread_id':thread_id}}
    return chatbot.get_state(config=config).values['messages']


#*************************** Session setup ******************************************

#define msg history
if 'msg_history' not in st.session_state:
    st.session_state['msg_history']=[]

if 'thread_id' not in st.session_state:
    st.session_state['thread_id'] = generate_thread_id()

if 'chat_thread' not in st.session_state:
    st.session_state['chat_thread']=retrieve_all_threads()

add_thread(st.session_state['thread_id'])


#*************************** side bar UI ********************************************
st.sidebar.title('langGraph Chatbot')

if st.sidebar.button('New chat'):
    reset_chat()

st.sidebar.header('My conversations')

for thread_id in st.session_state['chat_thread'][::-1]:     #[::-1] reverses the list-> newest comes on top
   if st.sidebar.button(str(thread_id)):
       st.session_state['thread_id']=thread_id
       messages=load_conversation(thread_id)

       temp_messages=[]
       for msg in messages :
            if isinstance(msg,HumanMessage):
               role='user'
            else:
               role='Assistance'
            temp_messages.append({'role':role,'content':msg.content})
      
       st.session_state['msg_history']=temp_messages


#***************************** Main UI ***********************************

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

# instead of thread_id as thread-1 manually we give thread_id from session state
#CONFIG = {'configurable':{'thread_id':st.session_state['thread_id']}}
    CONFIG = {
        'configurable':{'thread_id':st.session_state['thread_id']},
        'metadata':{'thread_id':st.session_state['thread_id']}
    }
   
#show user i/p as from assistance
    with st.chat_message('assistant'):
        #to stream any generator obj in streamlit 
        #st.write_stream(generator)
        # defining a fun which will return generator obj
        def ai_only_stream():
            for message_chunk, metadata in chatbot.stream(
                {'messages': [HumanMessage(content=user_input)]},
                config=CONFIG,
                stream_mode = 'messages'
                ):
                #yield only assistant tokens 
                if isinstance(message_chunk,AIMessage):
                    yield message_chunk.content
        
        ai_message= st.write_stream(ai_only_stream())

        # ai_message= st.write_stream(
        #     message_chunk.content for message_chunk ,metadata in chatbot.stream(
        #         {'messages': [HumanMessage(content=user_input)]},
        #         config=CONFIG,
        #         stream_mode = 'messages'
        #     )
        # )

#add msg in msg history with role
    st.session_state['msg_history'].append({'role':'assistant','content':ai_message})





    