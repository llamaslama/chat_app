import streamlit as st
from datetime import datetime
from streamlit.runtime.scriptrunner import get_script_run_ctx
import hashlib

# ========== 全局状态管理 ==========
if "global_messages" not in st.session_state:  # 全局消息存储
    st.session_state.global_messages = []

if "users" not in st.session_state:  # 用户状态管理
    st.session_state.users = {}


# ========== 用户会话初始化 ==========
def init_user_session():
    ctx = get_script_run_ctx()
    session_id = ctx.session_id if ctx else "unknown_" + str(datetime.now().timestamp())

    if session_id not in st.session_state.users:
        # 生成唯一用户信息
        user_id = hashlib.sha256(session_id.encode()).hexdigest()[:8]
        color = f"hsl({hash(user_id) % 360}, 70%, 50%)"  # 根据ID生成颜色

        st.session_state.users[session_id] = {
            "id": user_id,
            "color": color,
            "name": f"用户_{user_id}",
            "active": True
        }

    return st.session_state.users[session_id]


# ========== 页面配置 ==========
st.set_page_config(
    page_title="多用户聊天室",
    page_icon="💬",
    layout="centered"
)
current_user = init_user_session()  # 初始化当前用户

# ========== 界面组件 ==========
st.title("💬 多用户聊天室")
chat_container = st.container()

# 用户列表侧边栏
with st.sidebar:
    st.subheader("在线用户")
    for user in st.session_state.users.values():
        st.markdown(
            f"<span style='color:{user['color']}'>● {user['name']}</span>",
            unsafe_allow_html=True
        )

# ========== 消息处理逻辑 ==========
with st.container():
    cols = st.columns([5, 1])
    with cols[0]:
        user_input = st.chat_input("输入消息...", key="input")
    with cols[1]:
        send_button = st.button("发送")

if send_button or user_input:
    if user_input:
        new_message = {
            "content": user_input,
            "time": datetime.now().strftime("%H:%M:%S"),
            "user": current_user,
            "session_id": get_script_run_ctx().session_id
        }
        st.session_state.global_messages.append(new_message)

# ========== 消息显示优化 ==========
with chat_container:
    for msg in st.session_state.global_messages:
        # 区分其他用户消息样式
        is_current_user = msg["session_id"] == get_script_run_ctx().session_id
        user_name = "我" if is_current_user else msg["user"]["name"]

        with st.chat_message(name=user_name):
            # 消息气泡样式
            style = f"""
            border-radius: 15px;
            padding: 10px;
            background: {msg['user']['color'] if not is_current_user else '#e3f2fd'};
            color: {'white' if not is_current_user else 'black'};
            margin: 5px;
            """
            st.markdown(
                f"<div style='{style}'>"
                f"{msg['content']}<br>"
                f"<small>{msg['time']}</small>"
                "</div>",
                unsafe_allow_html=True
            )

    # 自动滚动脚本
    st.components.v1.html("""
    <script>
    const observer = new MutationObserver(() => {
        const container = window.parent.document.querySelector('.stChatMessage');
        container.scrollTop = container.scrollHeight;
    });
    observer.observe(document.body, { childList: true, subtree: true });
    </script>
    """)
