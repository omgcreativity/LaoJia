import streamlit as st
import json
import time
import auth
import storage
import chat_utils
import os
from PIL import Image

# --- 0. J1800 接口拦截逻辑 (必须放在最前面) ---
query_params = st.query_params
if "action" in query_params:
    action = query_params["action"]
    user = query_params.get("user")
    
    # J1800 取货接口: ?action=get&user=xxx
    if action == "get" and user:
        history = storage.load_memory(user)
        if history and history[-1]["role"] == "user":
            parts = history[-1]["parts"]
            text = ""
            for part in (parts if isinstance(parts, list) else [parts]):
                if isinstance(part, str): text += part
                elif isinstance(part, dict) and part.get("type") == "text":
                    text += part["text"]
            # 直接输出 JSON 并停止后续 UI 渲染
            st.write(json.dumps({"has_new": True, "content": text}, ensure_ascii=False))
        else:
            st.write(json.dumps({"has_new": False}))
        st.stop()

    # J1800 还货接口: ?action=put&user=xxx&msg=yyy
    if action == "put" and user and "msg" in query_params:
        msg = query_params["msg"]
        history = storage.load_memory(user)
        if history and history[-1]["role"] == "user":
            history.append({"role": "model", "parts": [{"type": "text", "text": msg}]})
            storage.save_memory(user, history)
            st.write(json.dumps({"status": "success"}))
        st.stop()

# --- 1. 正常 UI 页面配置 ---
st.set_page_config(page_title="老贾 - 会说话的AI助理", page_icon="🎙️")

if not auth.auth_flow():
    st.stop()

username = st.session_state.username
user_profile = storage.load_profile(username) or {}

if "history" not in st.session_state:
    st.session_state.history = storage.load_memory(username)

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
                    img_path = os.path.join("data", "users", username, part["path"])
                    if os.path.exists(img_path): st.image(img_path, width=300)

with chat_container:
    for msg in st.session_state.history:
        display_message(msg)

with st.expander("📷 拍照给老贾看", expanded=False):
    camera_img = st.camera_input("点击拍照", key="camera_input")

if prompt := st.chat_input("和老贾说说话..."):
    user_display_parts = [{"type": "text", "text": prompt}]
    if camera_img:
        image = Image.open(camera_img)
        rel_path = storage.save_image(username, image)
        user_display_parts.append({"type": "image", "path": rel_path})

    with chat_container:
        with st.chat_message("user"):
            st.write(prompt)
            if camera_img: st.image(camera_img, width=300)
    
    st.session_state.history.append({"role": "user", "parts": user_display_parts})
    storage.save_memory(username, st.session_state.history)
    
    with chat_container:
        with st.chat_message("assistant"):
            placeholder = st.empty()
            placeholder.markdown("⏳ 老贾正在通过 J1800 思考中...")
            found_reply = False
            for _ in range(45): # 最多等待90秒
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
                placeholder.error("💔 J1800 响应超时。")