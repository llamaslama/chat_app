import streamlit as st
from datetime import datetime
from streamlit.runtime.scriptrunner import get_script_run_ctx
import hashlib
from streamlit_server_state import server_state, server_state_lock
import asyncio
import threading
import websockets
import json
import time


# ========== 页面配置 ==========
st.set_page_config(
    page_title="多用户聊天室",
    page_icon="💬",
    layout="centered"
)

# ===== 隐藏按钮
hide_button = """
<style>
button[data-testid="stBaseButton-secondary"] {
    display: none !important;
}
</style>
"""
st.markdown(hide_button, unsafe_allow_html=True)
st.button("Rerun", key="rerun_button")

# ========== WebSocket 服务器 ==========
class WebSocketServer:
    def __init__(self):
        self.clients = set()
        self.loop = None
        self.thread = None

    async def handler(self, websocket):
        # 直接允许连接，不检查认证
        self.clients.add(websocket)
        try:
            async for message in websocket:
                if message == "ping":  # 心跳检测
                    await websocket.send("pong")
                # data = json.loads(message)
                # if data.get("type") == "rerun":
                #     # 直接触发重新运行
                #     st.rerun()
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.clients.remove(websocket)

    async def broadcast(self, message):
        if self.clients:
            await asyncio.wait([client.send(message) for client in self.clients])

    def start(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        async def server_main():
            async with websockets.serve(self.handler, "0.0.0.0", 8765):
                await asyncio.Future()  # 永久运行

        self.thread = threading.Thread(
            target=self.loop.run_until_complete,
            args=(server_main(),),
            daemon=True
        )
        self.thread.start()

    def stop(self):
        if self.loop:
            self.loop.call_soon_threadsafe(self.loop.stop)


# 初始化全局WebSocket服务器
if "websocket_server" not in server_state:
    server_state.websocket_server = WebSocketServer()
    server_state.websocket_server.start()
    print("WebSocket服务器已启动")  # 调试输出

# ========== 服务器状态初始化 ==========
if "global_messages" not in server_state:
    server_state.global_messages = []
if "users" not in server_state:
    server_state.users = {}


# ========== 用户会话管理 ==========
def init_user_session():
    ctx = get_script_run_ctx()
    session_id = ctx.session_id if ctx else "unknown_" + str(time.time())
    current_time = time.time()
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



current_user = init_user_session()

# ========== 界面布局 ==========
st.title("💬 实时群聊室")
chat_container = st.container()

# 在线用户侧边栏
with st.sidebar:
    st.subheader("在线用户")
    with server_state_lock["users"]:
        current_time = time.time()
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

    # 线程安全广播
    try:
        loop = server_state.websocket_server.loop
        if loop and loop.is_running():
            asyncio.run_coroutine_threadsafe(
                server_state.websocket_server.broadcast(
                    json.dumps({
                        "type": "new_message",
                        "count": len(server_state.global_messages)
                    })
                ),
                loop
            )
            print(f"广播成功，当前客户端数: {len(server_state.websocket_server.clients)}")
    except Exception as e:
        print("广播失败:", str(e))

# ========== 消息显示 ==========
with chat_container:
        # 使用 empty() 作为动态容器
        msg_container = st.empty()
        with msg_container.container():
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
                            f"</div>",
                            unsafe_allow_html=True
                        )

# ========== 客户端完整脚本 ==========
st.components.v1.html("""
<script>
function findAndClickButton() {
    const rerunButton = window.parent["document"].querySelector('.st-key-rerun_button button[data-testid="stBaseButton-secondary"]');
    if (rerunButton) {
        rerunButton.dispatchEvent(new MouseEvent('click', { bubbles: true }));
        console.log('Triggered rerun by clicking hidden button');
    } else {
        console.log('Button not found, retrying in 1 second');
        setTimeout(findAndClickButton, 1000);
    }
}
    
class WSController {
    constructor() {
        this.ws = null;
        this.initWebsocket();
    }

    initWebsocket() {
        console.log('🏁 Starting to initialize WebSocket');
        this.ws = new WebSocket('ws://127.0.0.1:8765');

        this.ws.onopen = () => console.log('✅ WebSocket connection successful');
        
        this.ws.onmessage = (e) => {
            console.log('📩 Received message:', e.data);
            this.triggerRerun();
        };

        this.ws.onerror = (error) => console.error('❌ WebSocket error:', error);
        this.ws.onclose = () => {
            console.log('🔌 Connection closed, reconnecting in 5 seconds...');
            setTimeout(() => this.initWebsocket(), 5000);
        };
    }
    
    triggerRerun() {
        findAndClickButton();
    }
}

document.addEventListener('DOMContentLoaded', () => new WSController());
</script>
""", height=0)


# 清理WebSocket服务器
def cleanup():
    if "websocket_server" in server_state:
        server_state.websocket_server.stop()
        print("WebSocket服务器已停止")  # 调试输出


import atexit

atexit.register(cleanup)
