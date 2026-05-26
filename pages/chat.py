import streamlit as st
from openai import OpenAI

st.set_page_config(page_title="AI 챗봇", layout="centered")
st.title("실시간 AI 챗봇 페이지")
st.caption("이전 대화를 기억하는 스마트한 챗봇입니다.")

if "openai_api_key" not in st.session_state or not st.session_state["openai_api_key"]:
    st.warning("메인 페이지(app)에서 OpenAI API Key를 먼저 입력해주세요!")
    st.stop()

if "messages" not in st.session_state:
    st.session_state.messages = []

if st.button("Clear (대화 내용 삭제)"):
    st.session_state.messages = []
    st.rerun()

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("챗봇에게 메시지를 보내보세요!"):
    
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    try:
        client = OpenAI(api_key=st.session_state["openai_api_key"])
        
        with st.chat_message("assistant"):
            stream = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.messages
                ],
                stream=True,
            )
            response = st.write_stream(stream)
            
        st.session_state.messages.append({"role": "assistant", "content": response})
        
    except Exception as e:
        st.error(f"오류가 발생했습니다: {str(e)}")
