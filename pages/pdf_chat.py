import streamlit as st
from openai import OpenAI
import time

st.set_page_config(page_title="ChatPDF", layout="centered")
st.title("ChatPDF (OpenAI File Search)")
st.caption("PDF 파일을 업로드하고 해당 문서에 대해 AI와 대화해보세요.")

if "openai_api_key" not in st.session_state or not st.session_state["openai_api_key"]:
    st.warning("메인 페이지(app)에서 OpenAI API Key를 먼저 입력해주세요!")
    st.stop()

client = OpenAI(api_key=st.session_state["openai_api_key"])

if "pdf_messages" not in st.session_state:
    st.session_state.pdf_messages = []
if "vector_store_id" not in st.session_state:
    st.session_state.vector_store_id = None
if "assistant_id" not in st.session_state:
    st.session_state.assistant_id = None
if "thread_id" not in st.session_state:
    st.session_state.thread_id = None
if "uploaded_file_id" not in st.session_state:
    st.session_state.uploaded_file_id = None

def clear_pdf_session():
    try:
        if st.session_state.assistant_id:
            client.beta.assistants.delete(st.session_state.assistant_id)
        if st.session_state.vector_store_id:
            if hasattr(client.beta, "vector_stores"):
                client.beta.vector_stores.delete(st.session_state.vector_store_id)
        if st.session_state.uploaded_file_id:
            client.files.delete(st.session_state.uploaded_file_id)
    except Exception:
        pass
    
    st.session_state.pdf_messages = []
    st.session_state.vector_store_id = None
    st.session_state.assistant_id = None
    st.session_state.thread_id = None
    st.session_state.uploaded_file_id = None
    st.toast("Vector Store와 대화 기록이 안전하게 삭제되었습니다!")

if st.button("Clear (Vector Store 및 대화 내용 삭제)"):
    clear_pdf_session()
    st.rerun()

uploaded_file = st.file_uploader("PDF 파일을 업로드 하세요 (1개 제한)", type=["pdf"], accept_multiple_files=False)

if uploaded_file and not st.session_state.vector_store_id:
    with st.spinner("OpenAI File Search 설정 중... 잠시만 기다려주세요."):
        try:
            file_response = client.files.create(
                file=(uploaded_file.name, uploaded_file.getvalue(), "application/pdf"),
                purpose="assistants"
            )
            st.session_state.uploaded_file_id = file_response.id

            if hasattr(client.beta, "vector_stores"):
                vs_client = client.beta.vector_stores
            else:
                from openai.resources.beta import VectorStores
                vs_client = VectorStores(client)

            vector_store = vs_client.create(name=f"VS_{uploaded_file.name}")
            st.session_state.vector_store_id = vector_store.id
            
            vs_client.file_batches.create_and_poll(
                vector_store_id=vector_store.id,
                file_ids=[file_response.id]
            )

            assistant = client.beta.assistants.create(
                name="PDF Helper",
                instructions="당신은 사용자가 업로드한 PDF 문서를 기반으로 정확하게 답변하는 AI 전문가입니다. 파일 서치 기능을 활용해 문서 내에 있는 내용을 근거로 답변하세요.",
                model="gpt-4o-mini",
                tools=[{"type": "file_search"}],
                tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}}
            )
            st.session_state.assistant_id = assistant.id

            thread = client.beta.threads.create()
            st.session_state.thread_id = thread.id
            
            st.success(f"'{uploaded_file.name}' 분석 완료! 이제 대화를 시작하세요.")

        except Exception as e:
            st.error(f"파일 처리 중 오류가 발생했습니다: {str(e)}")
            st.stop()

for message in st.session_state.pdf_messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("업로드한 PDF에 대해 궁금한 점을 물어보세요!"):
    if not st.session_state.vector_store_id:
        st.warning("먼저 PDF 파일을 업로드해 주세요.")
        st.stop()

    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.pdf_messages.append({"role": "user", "content": prompt})

    try:
        client.beta.threads.messages.create(
            thread_id=st.session_state.thread_id,
            role="user",
            content=prompt
        )

        with st.chat_message("assistant"):
            with st.spinner("문서를 분석하여 답변을 생성하는 중입니다..."):
                run = client.beta.threads.runs.create_and_poll(
                    thread_id=st.session_state.thread_id,
                    assistant_id=st.session_state.assistant_id
                )

                if run.status == 'completed':
                    messages = client.beta.threads.messages.list(
                        thread_id=st.session_state.thread_id
                    )
                    assistant_response = messages.data[0].content[0].text.value
                    st.markdown(assistant_response)
                    st.session_state.pdf_messages.append({"role": "assistant", "content": assistant_response})
                else:
                    st.error(f"답변 생성 실패 (Status: {run.status})")

    except Exception as e:
        st.error(f"오류가 발생했습니다: {str(e)}")
