import streamlit as st
import google.generativeai as genai
import os
import auth
import storage
import chat_utils
from PIL import Image

# --- 0. 页面配置 ---
st.set_page_config(page_title="老贾 - 会说话的AI助理", page_icon="🎙️")

# --- 1. 认证流程 ---
if not auth.auth_flow():
    st.stop()

# --- 2. 获取当前用户及配置 ---
username = st.session_state.username
user_profile = storage.load_profile(username)
# 防止 user_profile 是 None (虽然 storage.py 里的逻辑通常返回 {})
if not user_profile:
    user_profile = {}
# 【安全修正】只从环境变量读取 Key
# 这样 Key 只存在于 Zeabur 的后台，代码里和 GitHub 上完全没有痕迹
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    # 只有在 Zeabur 没配置好环境变量时才会报错
    st.error("🚨 系统配置错误：未检测到 API Key。请联系管理员（也就是你自己）在 Zeabur 环境变量中添加 GEMINI_API_KEY。")
    st.stop()

# 配置 Gemini
genai.configure(api_key=api_key)

# --- 3. 构建个性化 System Prompt ---
base_prompt = """
你叫“老贾”，是一个永不失忆、声音温暖的私人AI助理。
使用的是最先进的 Gemini 3 Flash 模型。
你的回复将被转换成语音，所以：
1. **尽量口语化**，不要列太长的清单。
2. **简练**，像聊微信语音一样，不要长篇大论。
3. 语气要亲切、自然。
"""

# 根据用户画像定制
user_info_prompt = f"""
\n\n【用户信息】
你的主人叫: {user_profile.get('nickname', username)}
性别: {user_profile.get('gender', '未知')}
年龄段: {user_profile.get('age', '未知')}
职业: {user_profile.get('occupation', '未知')}
兴趣爱好: {user_profile.get('hobbies', '未知')}
希望你的说话风格: {user_profile.get('style', '温馨治愈')}
请根据这些信息调整你的语气和话题，更好地服务主人。
"""

full_system_prompt = base_prompt + user_info_prompt

model = genai.GenerativeModel(
    model_name="gemini-3-flash-preview",
    system_instruction=full_system_prompt
)

# --- 4. 初始化聊天历史 ---
if "history" not in st.session_state:
    st.session_state.history = storage.load_memory(username)

# --- 5. 界面交互 ---
st.title(f"🎙️ 你的私人助理 - 老贾 ({user_profile.get('nickname', username)})")

# 侧边栏：个人中心
with st.sidebar:
    st.write(f"当前用户: **{username}**")
    if st.button("退出登录"):
        auth.logout()
    
    st.divider()
    chat_utils.render_sound_check()

chat_container = st.container()

with chat_container:
    # 定义显示消息的帮助函数
    def display_message(msg):
        role = "user" if msg["role"] == "user" else "assistant"
        with st.chat_message(role):
            parts = msg["parts"]
            if not isinstance(parts, list):
                parts = [parts] # Normalize old format
            
            for part in parts:
                if isinstance(part, str):
                    st.write(part)
                elif isinstance(part, dict):
                    if part.get("type") == "text":
                        st.write(part["text"])
                    elif part.get("type") == "image":
                        # Reconstruct path: data/users/{username}/{relative_path}
                        img_path = os.path.join("data", "users", username, part["path"])
                        if os.path.exists(img_path):
                            st.image(img_path, width=300)

    # 分离历史记录
    history = st.session_state.history
    SHOW_LAST_N = 5
    
    if len(history) > SHOW_LAST_N:
        with st.expander(f"🕒 查看更早的 {len(history) - SHOW_LAST_N} 条记录"):
            for msg in history[:-SHOW_LAST_N]:
                display_message(msg)
        
        # 显示最近的记录
        for msg in history[-SHOW_LAST_N:]:
            display_message(msg)
    else:
        # 记录较少时直接显示全部
        for msg in history:
            display_message(msg)

# Camera Input Area
with st.expander("📷 拍照给老贾看", expanded=False):
    camera_img = st.camera_input("点击拍照", key="camera_input")

if prompt := st.chat_input("和老贾说说话..."):
    # Prepare User Content
    user_content_parts = []
    user_display_parts = [] # For saving to history
    
    # 1. Add Text
    user_content_parts.append(prompt)
    user_display_parts.append({"type": "text", "text": prompt})
    
    # 2. Add Image if captured
    if camera_img:
        # Convert to PIL Image
        image = Image.open(camera_img)
        user_content_parts.append(image)
        
        # Save to disk for history
        rel_path = storage.save_image(username, image)
        user_display_parts.append({"type": "image", "path": rel_path})

    with chat_container:
        with st.chat_message("user"):
            st.write(prompt)
            if camera_img:
                st.image(camera_img, width=300)
    
    # Update Session History
    st.session_state.history.append({"role": "user", "parts": user_display_parts})
    
    try:
        # Rebuild Chat History for Gemini (Hydrate images)
        gemini_history = []
        for msg in st.session_state.history[:-1]: # Exclude the one we just added to process it freshly? 
            # Actually, model.start_chat history should NOT include the current message.
            # We send the current message via chat.send_message.
            
            role = "user" if msg["role"] == "user" else "model"
            parts = msg["parts"]
            if not isinstance(parts, list):
                parts = [parts]
            
            gemini_parts = []
            for part in parts:
                if isinstance(part, str):
                    gemini_parts.append(part)
                elif isinstance(part, dict):
                    if part.get("type") == "text":
                        gemini_parts.append(part["text"])
                    elif part.get("type") == "image":
                        # Load image from disk
                        img_path = os.path.join("data", "users", username, part["path"])
                        if os.path.exists(img_path):
                            try:
                                img = Image.open(img_path)
                                gemini_parts.append(img)
                            except:
                                pass # Skip missing images
            
            if gemini_parts:
                gemini_history.append({"role": role, "parts": gemini_parts})

        chat = model.start_chat(history=gemini_history)
        response = chat.send_message(user_content_parts)
        
        with chat_container:
            with st.chat_message("assistant"):
                st.write(response.text)
                chat_utils.play_audio(response.text)

        # Save Assistant Response
        st.session_state.history.append({"role": "model", "parts": [{"type": "text", "text": response.text}]})
        storage.save_memory(username, st.session_state.history)
        
    except Exception as e:
        if "429" in str(e):
            st.error("⚠️ 老贾有点累了（触发了免费版频率限制），请稍等几十秒再试。")
        else:
            st.error(f"连接出错: {e}")
