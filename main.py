import streamlit as st
import google.generativeai as genai
import os
import json
import time

# --- 0. 页面基础设置 ---
st.set_page_config(page_title="老贾 - 私人助理", page_icon="🔒")

# --- 1. 安全登录机制 ---
def check_password():
    """检查访问密码，返回 True 表示验证通过"""
    # 这一步是为了防止 Session 混乱，确保状态存在
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    # 如果已经登录成功，直接放行
    if st.session_state.authenticated:
        return True

    # 获取我们在 Zeabur 环境变量里设置的真实密码
    # 如果没设置，默认密码是 123456 (为了防止你把自己锁在外面，但请务必去改掉)
    CORRECT_PASSWORD = os.getenv("APP_PASSWORD", "123456")

    # 显示登录界面
    st.title("🔒 请验证身份")
    password_input = st.text_input("请输入访问密码", type="password")
    
    if st.button("进入"):
        if password_input == CORRECT_PASSWORD:
            st.session_state.authenticated = True
            st.success("验证成功！正在唤醒老贾...")
            time.sleep(1)
            st.rerun()  # 重新加载页面，进入聊天界面
        else:
            st.error("密码错误，请重试。")
            
    return False

# 如果没有通过密码验证，直接停止运行下面的代码
if not check_password():
    st.stop()


# ==========================================
# 下面是登录成功后才会执行的代码 (原来的逻辑)
# ==========================================

st.title("🧠 永不失忆的私人助理 - 老贾")

# 数据配置
DATA_FOLDER = "data" 
MEMORY_FILE = os.path.join(DATA_FOLDER, "memory.json")

if not os.path.exists(DATA_FOLDER):
    os.makedirs(DATA_FOLDER)

# 获取 API Key
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    st.error("❌ 未检测到 API Key，请在 Zeabur 环境变量中配置 GEMINI_API_KEY")
    st.stop()

genai.configure(api_key=api_key)

# 记忆函数
def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except:
                return []
    return []

def save_memory(history):
    data_to_save = []
    for msg in history:
        role = msg["role"]
        text = msg["parts"][0] if isinstance(msg["parts"], list) else msg["parts"]
        data_to_save.append({"role": role, "parts": [text]})
    
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data_to_save, f, ensure_ascii=False, indent=2)

# 初始化 Session
if "history" not in st.session_state:
    st.session_state.history = load_memory()

# 模型定义
system_prompt = """
你叫“老贾”，是一个永不失忆、忠诚且温暖的私人AI助理。
使用的是最先进的 Gemini 3 Flash 模型。
你的任务是陪伴主人、了解主人并解决问题。
请用温暖、老朋友般的语气对话。
"""

model = genai.GenerativeModel(
    model_name="gemini-3-flash-preview",
    system_instruction=system_prompt
)

# 渲染聊天界面
for msg in st.session_state.history:
    role = "user" if msg["role"] == "user" else "assistant"
    with st.chat_message(role):
        st.write(msg["parts"][0])

if prompt := st.chat_input("呼叫老贾..."):
    with st.chat_message("user"):
        st.write(prompt)
    
    st.session_state.history.append({"role": "user", "parts": [prompt]})
    
    try:
        chat = model.start_chat(history=st.session_state.history)
        response = chat.send_message(prompt)
        
        with st.chat_message("assistant"):
            st.write(response.text)
        
        st.session_state.history.append({"role": "model", "parts": [response.text]})
        save_memory(st.session_state.history)
            
    except Exception as e:
        st.error(f"老贾出故障了: {e}")
