import streamlit as st
from datetime import datetime
from streamlit.runtime.scriptrunner import get_script_run_ctx

# 初始化会话状态
if "messages" not in st.session_state:
    st.session_state.messages = []
if "user_input" not in st.session_state:  # 使用独立键存储输入值
    st.session_state.user_input = ""

# 获取并存储 session_id
if "session_id" not in st.session_state:
    ctx = get_script_run_ctx()
    st.session_state.session_id = ctx.session_id if ctx else "unknown"

# 页面设置
st.set_page_config(
    page_title="Streamlit 聊天室",
    page_icon="💬",
    layout="centered"
)

# 生成用户ID
def generate_user_id():
    session_id = st.session_state.session_id
    return f"用户_{hash(session_id) % 10000:04d}"

# 页面标题
st.title("💬 简易聊天室")

# 聊天记录容器
chat_container = st.container()

# 输入区域
with st.container():
    cols = st.columns([5, 1])
    with cols[0]:
        user_input = st.chat_input(
            "输入消息...",
            key="input",  # 仅用于绑定小部件
            on_submit=lambda: clear_input()  # 通过回调清空输入
        )
    with cols[1]:
        send_button = st.button("发送", on_click=lambda: clear_input())

# 清空输入的回调函数
def clear_input():
    st.session_state.user_input = ""  # 修改独立键

# 处理消息发送
if send_button or user_input:
    current_input = st.session_state.user_input or user_input
    if current_input:
        new_message = {
            "content": current_input,
            "time": datetime.now().strftime("%H:%M:%S"),
            "user": generate_user_id()
        }
        st.session_state.messages.append(new_message)
        clear_input()  # 清空输入

# 显示聊天记录
with chat_container:
    for msg in st.session_state.messages:
        with st.chat_message(name=msg["user"]):
            cols = st.columns([4, 1])
            cols[0].write(msg["content"])
            cols[1].caption(msg["time"])

    # 自动滚动到底部
    st.components.v1.html("""
    <script>
    window.addEventListener('load', function() {
        const container = window.parent.document.querySelector('.stChatMessage');
        container.scrollTop = container.scrollHeight;
    });
    </script>
    """)