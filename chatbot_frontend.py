import streamlit as st

with st.chat_message('user'):
    st.text('Hi')
with st.chat_message('assistant'):
    st.text('how can i help you?')
with st.chat_message('user'):
    st.text('my name is niteesh')

user_input= st.chat_input('type here')