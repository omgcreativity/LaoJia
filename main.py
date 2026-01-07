import streamlit as st
import google.generativeai as genai
import os
import auth
import storage
import chat_utils

# --- 0. 页面配置 ---
st.set_page_config(page_title="老贾 - 会说话的AI助理", page_icon="🎙️")

# --- 1. 认证流程 ---
if not auth.auth_flow():
    st.stop()

# --- 2. 获取当前用户及配置 ---
username = st.session_state.username
# user_profile = storage.load_profile(username) # 如果只是存Key，这行暂时不需要

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
    model_name="gemini-3-flash-preview", # 更新为更稳定的模型名称，或者保持用户原有的
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
        st.session_state.authenticated = False
        st.session_state.username = None
        st.session_state.history = []
        st.rerun()
    
    st.divider()
    chat_utils.render_sound_check()

chat_container = st.container()

with chat_container:
    for msg in st.session_state.history:
        role = "user" if msg["role"] == "user" else "assistant"
        with st.chat_message(role):
            # 兼容旧数据格式
            content = msg["parts"][0] if isinstance(msg["parts"], list) else msg["parts"]
            st.write(content)

if prompt := st.chat_input("和老贾说说话..."):
    with chat_container:
        with st.chat_message("user"):
            st.write(prompt)
    
    st.session_state.history.append({"role": "user", "parts": [prompt]})
    
    try:
        # Gemini history format adaptation if needed
        chat_history = []
        for msg in st.session_state.history:
            parts = msg["parts"]
            if not isinstance(parts, list):
                parts = [parts]
            # Gemini expects 'user' or 'model' roles
            role = "user" if msg["role"] == "user" else "model"
            chat_history.append({"role": role, "parts": parts})

        chat = model.start_chat(history=chat_history[:-1]) # send history excluding current prompt
        response = chat.send_message(prompt)
        
        with chat_container:
            with st.chat_message("assistant"):
                st.write(response.text)
                chat_utils.play_audio(response.text)

        st.session_state.history.append({"role": "model", "parts": [response.text]})
        storage.save_memory(username, st.session_state.history)
            
    except Exception as e:
        if "429" in str(e):
            st.error("⚠️ 老贾有点累了（触发了免费版频率限制），请稍等几十秒再试。")
        else:
            st.error(f"连接出错: {e}")
