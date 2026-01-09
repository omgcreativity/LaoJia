import streamlit as st
import json
import time
import auth
import storage
import chat_utils
import os
from PIL import Image
import google.generativeai as genai

# --- 0. 强力拦截逻辑：必须放在 st.set_page_config 之前 ---
q_params = st.query_params

if "action" in q_params:
    # 统一使用 action 和 user 变量名
    action = q_params["action"]
    user = q_params.get("user")
    
    if action == "get" and user:
        # 1. 取货逻辑
        h = storage.load_memory(user)
        res = {"has_new": False}
        if h and h[-1]["role"] == "user":
            p = h[-1]["parts"]
            # 兼容多种格式提取文本 (优先找文本内容)
            txt = ""
            for part in p:
                if isinstance(part, str):
                    txt = part
                    break
                elif isinstance(part, dict) and part.get("type") == "text":
                    txt = part.get("text", "")
                    break
            
            if txt:
                res = {"has_new": True, "content": txt}
        
        # 2. 构造带特征标签的输出
        st.write(f"BRIDGE_DATA:{json.dumps(res, ensure_ascii=False)}:END")
        st.stop() # 立即停止渲染
        
    elif action == "put" and user and "msg" in q_params:
        # 3. 还货逻辑
        msg = q_params["msg"]
        h = storage.load_memory(user)
        if h and h[-1]["role"] == "user":
            h.append({"role": "model", "parts": [{"type": "text", "text": msg}]})
            storage.save_memory(user, h)
            st.write("BRIDGE_DATA:{\"status\":\"success\"}:END")
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

    st.divider()
    st.markdown("### ⚙️ 设置")
    # 默认模式从 profile 读取，或者默认为车队
    default_mode_index = 0
    if user_profile.get("chat_mode") == "api":
        default_mode_index = 1
        
    chat_mode = st.radio("通信通道", ["Gemini 车队 (免费)", "官方 API (直连)"], index=default_mode_index)
    
    # 保存模式选择
    current_mode_code = "api" if "官方 API" in chat_mode else "car"
    if user_profile.get("chat_mode") != current_mode_code:
        user_profile["chat_mode"] = current_mode_code
        storage.save_profile(username, user_profile)

    # API Key 逻辑：用户设置优先 > 系统环境变量
    system_api_key = os.environ.get("GEMINI_API_KEY", "")
    stored_user_key = user_profile.get("api_key", "")
    
    api_key = stored_user_key if stored_user_key else system_api_key

    if current_mode_code == "api":
        label = "Gemini API Key"
        if system_api_key:
            label += " (留空则使用系统预设)"
            
        new_api_key = st.text_input(label, value=stored_user_key or "", type="password")
        
        if new_api_key != stored_user_key:
            user_profile["api_key"] = new_api_key
            storage.save_profile(username, user_profile)
            st.rerun()
        
        # 如果用户清空了输入框，回退到系统 Key
        api_key = new_api_key if new_api_key else system_api_key

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
            
            if current_mode_code == "car":
                # --- 车队模式 (J1800) ---
                placeholder.markdown("⏳ 老贾正在通过 J1800 思考中...")
                found_reply = False
                for _ in range(45): # 最多等待90秒
                    time.sleep(2)
                    latest_history = storage.load_memory(username)
                    if latest_history and latest_history[-1]["role"] == "model":
                        # 兼容旧格式和新格式
                        p = latest_history[-1]["parts"]
                        answer = ""
                        if isinstance(p, list) and len(p) > 0 and isinstance(p[0], dict):
                            answer = p[0].get("text", "")
                        
                        placeholder.markdown(answer)
                        chat_utils.play_audio(answer)
                        st.session_state.history = latest_history
                        found_reply = True
                        break
                if not found_reply:
                    placeholder.error("💔 J1800 响应超时。")
            
            else:
                # --- 官方 API 模式 ---
                if not api_key:
                    placeholder.error("请先在左侧设置 Gemini API Key")
                    st.stop()
                
                try:
                    placeholder.markdown("⏳ 老贾正在思考...")
                    genai.configure(api_key=api_key)
                    
                    # System Prompt
                    sys_prompt = f"你是一个名为'老贾'的AI助手。你的主人是 {user_profile.get('nickname', username)}。你的性格是 {user_profile.get('style', '温馨')}。"
                    
                    model = genai.GenerativeModel("gemini-3-flash-preview", system_instruction=sys_prompt)
                    
                    # 构造历史记录 (排除最新一条，因为要传给 send_message)
                    history_for_gemini = []
                    for msg in st.session_state.history[:-1]:
                        role = "user" if msg["role"] == "user" else "model"
                        parts = []
                        for p in msg["parts"]:
                            if isinstance(p, dict):
                                if p["type"] == "text": parts.append(p["text"])
                                elif p["type"] == "image":
                                    img_path = os.path.join("data", "users", username, p["path"])
                                    if os.path.exists(img_path):
                                        try: parts.append(Image.open(img_path))
                                        except: pass
                            else:
                                parts.append(str(p))
                        history_for_gemini.append({"role": role, "parts": parts})
                    
                    chat = model.start_chat(history=history_for_gemini)
                    
                    # 构造当前消息
                    current_parts = []
                    for p in st.session_state.history[-1]["parts"]:
                        if p["type"] == "text": current_parts.append(p["text"])
                        elif p["type"] == "image":
                             img_path = os.path.join("data", "users", username, p["path"])
                             if os.path.exists(img_path):
                                 try: current_parts.append(Image.open(img_path))
                                 except: pass
                    
                    response_stream = chat.send_message(current_parts, stream=True)
                    
                    full_text = ""
                    for chunk in response_stream:
                        full_text += chunk.text
                        placeholder.markdown(full_text)
                    
                    # 保存回复
                    st.session_state.history.append({"role": "model", "parts": [{"type": "text", "text": full_text}]})
                    storage.save_memory(username, st.session_state.history)
                    chat_utils.play_audio(full_text)
                    
                except Exception as e:
                    placeholder.error(f"API 调用失败: {e}")