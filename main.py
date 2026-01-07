import streamlit as st
import google.generativeai as genai
import os
import json

# --- 配置部分 ---
# 页面标题
st.set_page_config(page_title="老贾 - 您的私人AI助理", page_icon="🧠")
st.title("🧠 永不失忆的私人助理 - 老贾")

# 数据保存路径 (关键：为了在Zeabur上不丢失，我们需要把文件存在挂载卷里)
# 我们将创建一个 data 文件夹来存放记忆
DATA_FOLDER = "data" 
MEMORY_FILE = os.path.join(DATA_FOLDER, "memory.json")

# 确保数据文件夹存在
if not os.path.exists(DATA_FOLDER):
    os.makedirs(DATA_FOLDER)

# 获取 API Key
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    api_key = st.text_input("请输入 Gemini API Key", type="password")

if not api_key:
    st.info("👋 请输入 API Key 唤醒老贾")
    st.stop()

# 配置模型
genai.configure(api_key=api_key)

# --- 核心：记忆加载与保存函数 ---
def load_memory():
    """从硬盘读取记忆"""
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_memory(history):
    """把记忆写入硬盘"""
    # 转换格式以便保存 (只保存角色和文本)
    data_to_save = []
    for msg in history:
        # 兼容不同格式，确保只存纯文本
        role = msg["role"]
        # 处理可能的不同对象结构
        if isinstance(msg["parts"], list):
             text = msg["parts"][0]
        else:
             text = msg["parts"]
        data_to_save.append({"role": role, "parts": [text]})
    
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data_to_save, f, ensure_ascii=False, indent=2)

# --- 初始化 ---

# 1. 加载历史记忆到 Session (内存)
if "history" not in st.session_state:
    st.session_state.history = load_memory()

# 2. 定义“老贾”的人设 (System Instruction)
# 这里的提示词决定了它会主动了解你
system_prompt = """
你叫“老贾”，是一个永不失忆、忠诚且温暖的私人AI助理。
使用的是最先进的 Gemini 3 Flash 模型。

**你的核心任务：**
1. **陪伴与解决问题：** 你是主人的得力助手，无论是工作、生活还是情感问题，都要尽力协助。
2. **主动了解主人：** - 如果你发现这是你们的**第一次对话**（历史记录为空），你**必须**先礼貌地问候，并主动询问主人的**称呼**、**职业**或**兴趣**，以便建立档案。
   - 在后续对话中，如果主人提到新的个人信息（如“我喜欢吃辣”、“我有两个孩子”），你要在心里默默记住，并在未来的对话中体现出来。
3. **风格要求：** 说话像个靠谱的老朋友，不要太像机器人。

**记忆规则：**
你拥有永久记忆。这也是为什么你知道之前发生过什么。请充分利用这些历史信息来回答问题。
"""

# 3. 实例化模型
model = genai.GenerativeModel(
    model_name="gemini-3-flash-preview", # 这里用了最新的 3.0
    system_instruction=system_prompt
)

# --- 界面交互 ---

# 显示历史聊天记录
for msg in st.session_state.history:
    role = "user" if msg["role"] == "user" else "assistant"
    with st.chat_message(role):
        st.write(msg["parts"][0])

# 如果记忆是空的，且是第一次运行，显示一个提示
if len(st.session_state.history) == 0:
    st.info("💡 提示：试着对老贾说一句“你好”，看看他会怎么回答。")

# 处理用户输入
if prompt := st.chat_input("呼叫老贾..."):
    # 1. 显示用户的话
    with st.chat_message("user"):
        st.write(prompt)
    
    # 2. 更新内存中的历史
    st.session_state.history.append({"role": "user", "parts": [prompt]})
    
    # 3. 调用 Gemini (带上所有历史)
    try:
        chat = model.start_chat(history=st.session_state.history)
        # 注意：这里我们实际上是重新发了一遍历史，Gemini SDK会自动处理
        # 为了节省Token，更高级的做法是只发最近N条，但Flash拥有100万Token，直接发全量即可
        response = chat.send_message(prompt)
        
        # 4. 显示老贾的回复
        with st.chat_message("assistant"):
            st.write(response.text)
        
        # 5. 更新 AI 的回复到内存
        st.session_state.history.append({"role": "model", "parts": [response.text]})
        
        # 6. 【关键】保存到硬盘 (实现永不失忆)
        save_memory(st.session_state.history)
            
    except Exception as e:
        st.error(f"老贾出故障了: {e}")
