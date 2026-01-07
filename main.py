import streamlit as st
import google.generativeai as genai
import os
import json
import time
import asyncio
import edge_tts
import re
import streamlit.components.v1 as components  # <--- 新增这个库

# --- 0. 页面配置 ---
st.set_page_config(page_title="老贾 - 会说话的AI助理", page_icon="🎙️")

# --- 1. 核心功能函数 ---

def clean_markdown(text):
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'`(.*?)`', r'\1', text)
    return text

async def generate_audio(text, output_file):
    voice = "zh-CN-YunxiNeural"
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_file)

def play_audio(text):
    clean_text = clean_markdown(text)
    output_file = "reply.mp3"
    asyncio.run(generate_audio(clean_text, output_file))
    st.audio(output_file, format='audio/mp3', start_time=0, autoplay=True)

# --- 2. 安全登录 ---
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if st.session_state.authenticated:
        return True
    
    CORRECT_PASSWORD = os.getenv("APP_PASSWORD", "123456")
    st.title("🔒 请验证身份")
    password_input = st.text_input("请输入访问密码", type="password")
    if st.button("进入"):
        if password_input == CORRECT_PASSWORD:
            st.session_state.authenticated = True
            st.success("验证成功！")
            time.sleep(0.5)
            st.rerun()
        else:
            st.error("密码错误")
    return False

if not check_password():
    st.stop()

# --- 3. 初始化与配置 ---
st.title("🎙️ 你的私人助理 - 老贾")

# ============== ⬇️ 新增：声音激活按钮 ⬇️ ==============
# 浏览器的自动播放策略要求用户必须先与页面交互（点击）才能播放声音。
# 我们做一个HTML按钮，点一下播放一个静音或提示音，以此解锁浏览器的音频权限。

sound_check_html = """
<div style="padding: 10px; border: 1px dashed #ccc; border-radius: 5px; margin-bottom: 20px; text-align: center;">
    <p style="margin: 0 0 10px 0; font-size: 14px; color: #666;">
        🔇 <b>听不到声音？</b> 浏览器通常默认静音。<br>请点击下方按钮<b>“激活”</b>音频权限。
    </p>
    <button onclick="activateSound()" style="
        background-color: #FF4B4B; 
        color: white; 
        border: none; 
        padding: 8px 16px; 
        border-radius: 4px; 
        cursor: pointer;
        font-weight: bold;">
        🔊 点击激活声音
    </button>
    <audio id="testAudio" src="https://www.soundjay.com/buttons/beep-01a.mp3"></audio>
    <script>
        function activateSound() {
            var audio = document.getElementById("testAudio");
            audio.play().then(() => {
                alert("声音已激活！现在老贾可以说话了。");
            }).catch(error => {
                console.log("激活失败: " + error);
            });
        }
    </script>
</div>
"""
# 渲染这个HTML块
components.html(sound_check_html, height=120)
# ============== ⬆️ 新增结束 ⬆️ ==============


DATA_FOLDER = "data" 
MEMORY_FILE = os.path.join(DATA_FOLDER, "memory.json")
if not os.path.exists(DATA_FOLDER):
    os.makedirs(DATA_FOLDER)

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    st.error("请配置 API Key")
    st.stop()

genai.configure(api_key=api_key)

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

if "history" not in st.session_state:
    st.session_state.history = load_memory()

system_prompt = """
你叫“老贾”，是一个永不失忆、声音温暖的私人AI助理。
使用的是最先进的 Gemini 3 Flash 模型。
你的回复将被转换成语音，所以：
1. **尽量口语化**，不要列太长的清单。
2. **简练**，像聊微信语音一样，不要长篇大论。
3. 语气要亲切、自然。
"""

model = genai.GenerativeModel(
    model_name="gemini-3-flash-preview",
    system_instruction=system_prompt
)

# --- 4. 界面交互 ---
chat_container = st.container()

with chat_container:
    for msg in st.session_state.history:
        role = "user" if msg["role"] == "user" else "assistant"
        with st.chat_message(role):
            st.write(msg["parts"][0])

if prompt := st.chat_input("和老贾说说话... (支持手机语音输入)"):
    with chat_container:
        with st.chat_message("user"):
            st.write(prompt)
    
    st.session_state.history.append({"role": "user", "parts": [prompt]})
    
    try:
        chat = model.start_chat(history=st.session_state.history)
        response = chat.send_message(prompt)
        
        with chat_container:
            with st.chat_message("assistant"):
                st.write(response.text)
                try:
                    play_audio(response.text)
                except Exception as e:
                    st.warning(f"语音播放失败: {e}")

        st.session_state.history.append({"role": "model", "parts": [response.text]})
        save_memory(st.session_state.history)
            
    except Exception as e:
        st.error(f"连接出错: {e}")
