import streamlit as st
from datetime import datetime
from streamlit.runtime.scriptrunner import get_script_run_ctx
import hashlib
from streamlit_server_state import server_state, server_state_lock

# ========== 服务器状态初始化 ==========
if "global_messages" not in server_state:
    server_state.global_messages = []
if "users" not in server_state:
    server_state.users = {}


# ========== 用户会话管理 ==========
def init_user_session():
    ctx = get_script_run_ctx()
    session_id = ctx.session_id if ctx else "unknown_" + str(datetime.now().timestamp())
    current_time = datetime.now().timestamp()
    with server_state_lock["users"]:
        # 清理5分钟未活动的用户
        inactive_users = [k for k, v in server_state.users.items() if current_time - v["last_active"] > 300]
        for user_id in inactive_users:
            del server_state.users[user_id]
        # 注册新用户或更新活动时间
        if session_id not in server_state.users:
            user_hash = hashlib.sha256(session_id.encode()).hexdigest()[:8]
            server_state.users[session_id] = {
                "id": user_hash,
                "color": f"hsl({hash(user_hash) % 360}, 70%, 50%)",
                "name": f"用户_{user_hash}",
                "last_active": current_time
            }
        else:
            server_state.users[session_id]["last_active"] = current_time
        return server_state.users[session_id]


# ========== 页面配置 ==========
st.set_page_config(
    page_title="多用户聊天室",
    page_icon="💬",
    layout="centered"
)
current_user = init_user_session()

# ========== 轮询刷新机制 ==========
if "refresh_counter" not in st.session_state:
    st.session_state.refresh_counter = 0

# 隐藏的刷新触发器（使用固定aria-label）
refresh_trigger = st.number_input(
    'refresh',
    value=0,
    key='refresh_trigger',
    label_visibility='hidden',
    args={"aria-label": "refresh_trigger"}
)

# ========== 界面布局 ==========
st.title("💬 实时群聊室")
chat_container = st.container()

# 在线用户侧边栏
with st.sidebar:
    st.subheader("在线用户")
    with server_state_lock["users"]:
        current_time = datetime.now().timestamp()
        active_users = {k: v for k, v in server_state.users.items() if current_time - v["last_active"] <= 300}
        for user in active_users.values():
            st.markdown(
                f"<span style='color:{user['color']}'>● {user['name']}</span>",
                unsafe_allow_html=True
            )

# ========== 消息处理 ==========
user_input = st.chat_input("输入消息...")
if user_input:
    new_message = {
        "content": user_input,
        "time": datetime.now().strftime("%H:%M:%S"),
        "user": current_user,
        "session_id": get_script_run_ctx().session_id
    }
    with server_state_lock["global_messages"]:
        server_state.global_messages.append(new_message)

# ========== 消息显示 ==========
with chat_container:
    with server_state_lock["global_messages"]:
        for msg in server_state.global_messages:
            is_current_user = msg["session_id"] == get_script_run_ctx().session_id
            user_name = "我" if is_current_user else msg["user"]["name"]
            with st.chat_message(name=user_name):
                message_style = (
                    f"background: {msg['user']['color']}; color: white;"
                    if not is_current_user
                    else "background: #e3f2fd; color: black;"
                )
                st.markdown(
                    f"<div style='border-radius: 15px; padding: 10px; {message_style}'>"
                    f"{msg['content']}<br>"
                    f"<small>{msg['time']}</small>"
                    "</div>",
                    unsafe_allow_html=True
                )

# ========== 自动刷新逻辑 ==========
st.components.v1.html("""
<script>
// 等待页面加载完成
document.addEventListener('DOMContentLoaded', function() {
    // 自动滚动逻辑
    const scrollObserver = new MutationObserver(() => {
        const chatContainer = window.parent.document.querySelector('.stChatMessage');
        if (chatContainer) chatContainer.scrollTop = chatContainer.scrollHeight;
    });
    scrollObserver.observe(document.body, { childList: true, subtree: true });

    // 1秒轮询刷新逻辑
    setInterval(() => {
        // 使用固定aria-label选择器
        const input = window.parent.document.querySelector('input[aria-label="refresh_trigger"]');
        if (input) {
            // 正确修改变量顺序
            const currentValue = parseInt(input.value) || 0;
            input.value = currentValue + 1;

            // 创建并触发事件
            const event = new Event('input', {
                bubbles: true,
                cancelable: true,
            });
            input.dispatchEvent(event);
        }
    }, 1000);
});
</script>
""")

# 刷新检测逻辑
if st.session_state.refresh_trigger != st.session_state.refresh_counter:
    st.session_state.refresh_counter = st.session_state.refresh_trigger
    st.rerun()
