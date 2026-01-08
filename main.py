import streamlit as st
import time
import auth
import storage
import chat_utils
import os
from PIL import Image

# --- 0. 页面配置 ---
st.set_page_config(page_title="老贾 - 会说话的AI助理", page_icon="🎙️")

# --- 1. 认证流程 ---
if not auth.auth_flow():
    st.stop()

username = st.session_state.username
user_profile = storage.load_profile(username) or {}

# --- 2. 初始化聊天历史 ---
if "history" not in st.session_state:
    st.session_state.history = storage.load_memory(username)

# --- 3. 界面交互 ---
st.title(f"🎙️ 你的私人助理 - 老贾 ({user_profile.get('nickname', username)})")

with st.sidebar:
    st.write(f"当前用户: **{username}**")
    if st.button("退出登录"):
        auth.logout()
    st.divider()
    chat_utils.render_sound_check()

chat_container = st.container()

def display_message(msg):
    role = "user" if msg["role"] == "user" else "assistant"
    with st.chat_message(role):
        parts = msg["parts"]
        for part in (parts if isinstance(parts, list) else [parts]):
            if isinstance(part, str): st.write(part)
            elif isinstance(part, dict):
                if part.get("type") == "text": st.write(part["text"])
                elif part.get("type") == "image":
                    # 注意：Streamlit无法直接访问data目录，通常需要配置静态映射或读取Buffer
                    img_path = os.path.join("data", "users", username, part["path"])
                    if os.path.exists(img_path):
                        st.image(img_path, width=300)

with chat_container:
    for msg in st.session_state.history:
        display_message(msg)

# --- 4. 拍照功能扩展 ---
with st.expander("📷 拍照给老贾看", expanded=False):
    camera_img = st.camera_input("点击拍照", key="camera_input")

# --- 5. 输入处理 ---
if prompt := st.chat_input("和老贾说说话..."):
    user_display_parts = [{"type": "text", "text": prompt}]
    
    # 如果拍了照
    if camera_img:
        image = Image.open(camera_img)
        rel_path = storage.save_image(username, image)
        user_display_parts.append({"type": "image", "path": rel_path})

    with chat_container:
        with st.chat_message("user"):
            st.write(prompt)
            if camera_img: st.image(camera_img, width=300)
    
    # 存入数据库，等待 J1800 抓取
    st.session_state.history.append({"role": "user", "parts": user_display_parts})
    storage.save_memory(username, st.session_state.history)
    
    # --- 轮询等待 J1800 ---
    with chat_container:
        with st.chat_message("assistant"):
            placeholder = st.empty()
            placeholder.markdown("⏳ 老贾正在通过 J1800 思考中...")
            
            found_reply = False
            for _ in range(30): # 等待 60 秒
                time.sleep(2)
                latest_history = storage.load_memory(username)
                if latest_history and latest_history[-1]["role"] == "model":
                    answer = latest_history[-1]["parts"][0]["text"]
                    placeholder.markdown(answer)
                    chat_utils.play_audio(answer)
                    st.session_state.history = latest_history
                    found_reply = True
                    break
            
            if not found_reply:
                placeholder.error("💔 J1800 没反应，请确认小电脑是否正在运行 car_bot.py")