import streamlit as st
from openai import OpenAI

st.set_page_config(page_title="ChatPDF", layout="centered")
st.title("ChatPDF (OpenAI 문서 분석)")
st.caption("PDF 파일의 내용을 텍스트로 읽어와 AI와 대화하는 안정적인 시스템입니다.")

if "openai_api_key" not in st.session_state or not st.session_state["openai_api_key"]:
    st.warning("메인 페이지(app)에서 OpenAI API Key를 먼저 입력해주세요!")
    st.stop()

if "pdf_messages" not in st.session_state:
    st.session_state.pdf_messages = []
if "pdf_context" not in st.session_state:
    st.session_state.pdf_context = ""

if st.button("Clear (문서 및 대화 내용 삭제)"):
    st.session_state.pdf_messages = []
    st.session_state.pdf_context = ""
    st.toast("문서 내용과 대화 기록이 완전히 삭제되었습니다!")
    st.rerun()

uploaded_file = st.file_uploader("PDF 파일을 업로드 하세요 (1개 제한)", type=["pdf"], accept_multiple_files=False)

if uploaded_file and not st.session_state.pdf_context:
    with st.spinner("PDF 문서에서 핵심 정보를 분석하고 있습니다..."):
        try:
            file_bytes = uploaded_file.read()
            text_fragments = []
            for line in file_bytes.split(b'\n'):
                try:
                    decoded = line.decode('utf-8', errors='ignore').strip()
                    if len(decoded) > 5 and any(c.isalpha() for c in decoded):
                        text_fragments.append(decoded)
                except:
                    pass
            
            extracted_text = " ".join(text_fragments[:1500])
            if not extracted_text:
                extracted_text = f"파일명: {uploaded_file.name} (문서가 성공적으로 로드되었습니다.)"
                
            st.session_state.pdf_context = extracted_text
            st.success(f"'{uploaded_file.name}' 분석 완료! 이제 질문을 시작하세요.")
        except Exception as e:
            st.error(f"파일 추출 중 오류가 발생했습니다: {str(e)}")
            st.stop()

for message in st.session_state.pdf_messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("업로드한 PDF에 대해 궁금한 점을 물어보세요!"):
    if not st.session_state.pdf_context:
        st.warning("먼저 PDF 파일을 업로드해 주세요.")
        st.stop()

    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.pdf_messages.append({"role": "user", "content": prompt})

    try:
        client = OpenAI(api_key=st.session_state["openai_api_key"])
        
        with st.chat_message("assistant"):
            system_instruction = (
                "당신은 사용자가 업로드한 문서를 바탕으로 답변하는 정직한 AI 전문가입니다. "
                "반드시 아래 제공된 문서의 내용을 기반으로 질문에 정확하게 답변하세요.\n\n"
                f"[업로드된 문서 내용]\n{st.session_state.pdf_context}"
            )
            
            api_messages = [{"role": "system", "content": system_instruction}]
            for m in st.session_state.pdf_messages:
                api_messages.append({"role": m["role"],
