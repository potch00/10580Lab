import streamlit as st
from openai import OpenAI

st.set_page_config(page_title="LLM Q&A 앱", layout="centered")

st.title("나만의 LLM 비서 앱")
st.caption("OpenAI API Key를 입력하고 질문을 던져보세요.")

# 1. session_state를 이용한 API Key 관리 (페이지 이동/새로고침 시 유지)
if "openai_api_key" not in st.session_state:
    st.session_state["openai_api_key"] = ""

# API Key 입력 받기 (비밀번호 타입)
api_key_input = st.text_input(
    "OpenAI API Key를 입력하세요", 
    value=st.session_state["openai_api_key"], 
    type="password",
    placeholder="sk-..."
)

# 입력값이 변경되면 session_state 업데이트
if api_key_input:
    st.session_state["openai_api_key"] = api_key_input

# 2. @st.cache_data를 이용한 LLM 호출 결과 캐싱
# 입력(api_key, prompt)이 변하지 않으면 재실행 시 저장된 결과를 반환합니다.
@st.cache_data(show_spinner="AI가 답변을 생각하는 중입니다...")
def get_llm_response(api_key, prompt):
    try:
        # OpenAI 클라이언트 초기화
        client = OpenAI(api_key=api_key)
        
        # GPT-4o-mini 모델 호출 (가볍고 빠른 기본 모델)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "당신은 친절하고 유능한 AI 어시스턴트입니다."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"오류가 발생했습니다: {str(e)}"

# 3. 사용자 질문 입력 및 실행 영역
user_question = st.text_area("질문을 입력하세요:", placeholder="예: Streamlit이 무엇인가요?")

if st.button("질문하기"):
    if not st.session_state["openai_api_key"]:
        st.warning("먼저 OpenAI API Key를 입력해주세요.")
    elif not user_question.strip():
        st.warning("질문을 입력해주세요.")
    else:
        # 캐싱된 함수 호출
        answer = get_llm_response(st.session_state["openai_api_key"], user_question)
        
        st.markdown("---")
        st.subheader("답변")
        st.write(answer)
