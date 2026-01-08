from fastapi import FastAPI, HTTPException, Depends, status
from pydantic import BaseModel
import storage
import os
import asyncio

app = FastAPI(title="老贾 API", description="LaoJia AI Assistant Backend")

# --- 数据模型 (保留原有) ---
class UserLogin(BaseModel):
    username: str
    password: str

class UserRegister(BaseModel):
    username: str
    password: str
    nickname: str = None
    age: str = None
    gender: str = None
    occupation: str = None
    hobbies: str = None
    style: str = "温馨治愈"

class ChatRequest(BaseModel):
    username: str
    message: str

# --- 基础路由 (保留原有) ---
@app.get("/")
def read_root():
    return {"message": "Welcome to LaoJia Bridge API"}

@app.post("/register")
def register(user: UserRegister):
    profile_data = {
        "nickname": user.nickname,
        "age": user.age,
        "gender": user.gender,
        "occupation": user.occupation,
        "hobbies": user.hobbies,
        "style": user.style
    }
    success, msg = storage.create_user(user.username, user.password, profile_data)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return {"message": "Registration successful"}

@app.post("/login")
def login(user: UserLogin):
    if storage.verify_user(user.username, user.password):
        return {"message": "Login successful", "username": user.username}
    else:
        raise HTTPException(status_code=401, detail="Invalid credentials")

# --- 核心改造：J1800 中转接口 ---

@app.get("/get_pending_msg")
def get_pending_msg(username: str):
    """
    J1800 轮询此接口。
    作用：检查老贾数据库里，最后一条消息是不是用户发的。
    如果是，就返回给 J1800，让 J1800 去问网页版 Gemini。
    """
    history = storage.load_memory(username)
    if not history:
        return {"has_new": False}
    
    last_msg = history[-1]
    if last_msg["role"] == "user":
        # 提取文本内容（包含对照片的判断）
        parts = last_msg["parts"]
        text_content = ""
        has_image = False
        
        for part in (parts if isinstance(parts, list) else [parts]):
            if isinstance(part, str): 
                text_content += part
            elif isinstance(part, dict):
                if part.get("type") == "text":
                    text_content += part["text"]
                elif part.get("type") == "image":
                    has_image = True
        
        # 给 J1800 的提示词增加画像信息，让它在网页版也能保持“老贾”的人设
        user_profile = storage.load_profile(username) or {}
        system_prefix = f"【主人画像：{user_profile.get('nickname', username)}，风格：{user_profile.get('style', '温馨')}】"
        if has_image:
            system_prefix += "【主人发了照片，请结合照片回答】"
            
        return {"has_new": True, "content": f"{system_prefix} {text_content}"}
    
    return {"has_new": False}

@app.post("/callback_reply")
def callback_reply(request: ChatRequest):
    """
    J1800 拿到网页版回复后调用此接口。
    作用：把答案存回老贾的 memory.json。
    """
    history_data = storage.load_memory(request.username)
    
    # 防重逻辑
    if history_data and history_data[-1]["role"] == "model":
        return {"message": "Skip, already replied"}
        
    history_data.append({
        "role": "model", 
        "parts": [{"type": "text", "text": request.message}]
    })
    storage.save_memory(request.username, history_data)
    return {"message": "Success"}

# --- 原有的 /chat 接口可以保留作为备用，或者直接重写为报错提示 ---
@app.post("/chat")
async def chat(request: ChatRequest):
    # 既然改用 J1800 了，这个接口如果被调用，可以提示用户通过网页端触发
    raise HTTPException(status_code=405, detail="请通过老贾网页端发送消息，J1800 将自动处理回复。")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)