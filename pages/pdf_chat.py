import streamlit as st
from openai import OpenAI
import time

st.set_page_config(page_title="ChatPDF", layout="centered")
st.title("ChatPDF (OpenAI File Search 정석)")
st.caption("OpenAI 고유의 File Search(Vector Store) 기능을 사용하는 페이지입니다.")

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

def clear_openai_vector_store():
    try:
        if st.session_state.assistant_id:
            client.beta.assistants.delete(st.session_state.assistant_id)
        if st.session_state.vector_store_id:
            client.request(
                method="DELETE",
                cast_to=dict,
                options={"url": f"/v1/vector_stores/{st.session_state.vector_store_id}"}
            )
        if st.session_state.uploaded_file_id:
            client.files.delete(st.session_state.uploaded_file_id)
    except Exception:
        pass
    
    st.session_state.pdf_messages = []
    st.session_state.vector_store_id = None
    st.session_state.assistant_id = None
    st.session_state.thread_id = None
    st.session_state.uploaded_file_id = None
    st.toast("OpenAI Vector Store와 대화 기록이 안전하게 완전 삭제되었습니다!")

if st.button("Clear (Vector Store 및 대화 내용 삭제)"):
    clear_openai_vector_store()
    st.rerun()

uploaded_file = st.file_uploader("PDF 파일을 업로드 하세요 (1개 제한)", type=["pdf"], accept_multiple_files=False)

if uploaded_file and not st.session_state.vector_store_id:
    with st.spinner("OpenAI 공식 File Search 기능 활성화 중... (약 10초 소요)"):
        try:
            file_response = client.files.create(
                file=(uploaded_file.name, uploaded_file.getvalue(), "application/pdf"),
                purpose="assistants"
            )
            st.session_state.uploaded_file_id = file_response.id

            vs_response = client.request(
                method="POST",
                cast_to=dict,
                options={
                    "url": "/v1/vector_stores",
                    "json": {"name": f"VS_{uploaded_file.name}"}
                }
            )
            st.session_state.vector_store_id = vs_response["id"]
            
            client.request(
                method="POST",
                cast_to=dict,
                options={
                    "url": f"/v1/vector_stores/{st.session_state.vector_store_id}/file_batches",
                    "json": {"file_ids": [file_response.id]}
                }
            )
            time.sleep(3)

            assistant = client.beta.assistants.create(
                name="PDF AI Expert",
                instructions="당신은 사용자가 제출한 PDF 문서를 기반으로 답변하는 챗봇입니다. 반드시 탑재된 'file_search' 기능을 사용해 Vector Store 내의 데이터를 근거로 답변하세요.",
                model="gpt-4o-mini",
                tools=[{"type": "file_search"}],
                tool_resources={"file_search": {"vector_store_ids": [st.session_state.vector_store_id]}}
            )
            st.session_state.assistant_id = assistant.id

            thread = client.beta.threads.create()
            st.session_state.thread_id = thread.id
            
            st.success(f"OpenAI File Search 준비 완료! '{uploaded_file.name}' 기반 대화를 시작합니다.")

        except Exception as e:
            st.error(f"파일 처리 중 오류가 발생했습니다: {str(e)}")
            st.stop()

for message in st.session_state.pdf_messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("업로드한 PDF에 대해 OpenAI File Search 기능으로 질문하기"):
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
            with st.spinner("OpenAI 가 Vector Store 에서 정보를 검색하는 중..."):
                run = client.beta.threads.runs.create_and_poll(
                    thread_id=st.session_state.thread_id,
                    assistant_id=st.session_state.assistant_id
                )

                if run.status == 'completed':
                    messages = client.beta.threads.messages.list(thread_id=st.session_state.thread_id)
                    assistant_response = messages.data[0].content[0].text.value
                    st.markdown(assistant_response)
                    st.session_state.pdf_messages.append({"role": "assistant", "content": assistant_response})
                else:
                    st.error(f"답변 생성 실패 (OpenAI Status: {run.status})")

    except Exception as e:
        st.error(f"오류가 발생했습니다: {str(e)}")
