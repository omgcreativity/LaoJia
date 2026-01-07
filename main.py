import streamlit as st
import google.generativeai as genai
import os

# 页面标题
st.set_page_config(page_title="我的老贾", page_icon="🤖")
st.title("🤖 永不失忆的老贾")

# 获取 API Key (部署到 Zeabur 后，我们会通过环境变量设置，这里先写个获取逻辑)
# 优先从环境变量获取，如果没有则尝试从输入框获取（方便本地测试）
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    api_key = st.text_input("请输入 Gemini API Key", type="password")

if not api_key:
    st.info("👋 请输入 API Key 开始对话")
    st.stop()

# 配置 Gemini
genai.configure(api_key=api_key)

# 核心：记忆系统 (在网页关闭前有效，如需永久保存需对接数据库，Zeabur支持)
if "history" not in st.session_state:
    st.session_state.history = []

# 显示历史消息
for message in st.session_state.history:
    role = "user" if message["role"] == "user" else "assistant"
    with st.chat_message(role):
        st.write(message["parts"][0])

# 处理用户输入
if prompt := st.chat_input("说点什么..."):
    with st.chat_message("user"):
        st.write(prompt)
    
    # 调用 Gemini
    try:
        model = genai.GenerativeModel("gemini-3-flash-preview")
        chat = model.start_chat(history=st.session_state.history)
        response = chat.send_message(prompt)
        
        with st.chat_message("assistant"):
            st.write(response.text)
        
        # 更新记忆
        st.session_state.history.append({"role": "user", "parts": [prompt]})
        st.session_state.history.append({"role": "model", "parts": [response.text]})
            
    except Exception as e:

        st.error(f"发生错误: {e}")





