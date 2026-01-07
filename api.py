from fastapi import FastAPI, HTTPException, Depends, status
from pydantic import BaseModel
import storage
import google.generativeai as genai
import os
import edge_tts
import asyncio
import uuid

app = FastAPI(title="老贾 API", description="LaoJia AI Assistant Backend")

# Data Models
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
    api_key: str = None # Optional: client can provide key

# Routes
@app.get("/")
def read_root():
    return {"message": "Welcome to LaoJia API"}

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
        # In a real app, return a JWT token here
        return {"message": "Login successful", "username": user.username}
    else:
        raise HTTPException(status_code=401, detail="Invalid credentials")

@app.post("/chat")
async def chat(request: ChatRequest):
    # 1. Load User & Config
    user_profile = storage.load_profile(request.username)
    
    # 2. Setup API Key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        if "api_key" in user_profile:
            api_key = user_profile["api_key"]
        elif request.api_key:
            api_key = request.api_key
    
    if not api_key:
        raise HTTPException(status_code=500, detail="API Key not configured")

    genai.configure(api_key=api_key)

    # 3. Build Prompt
    base_prompt = """
    你叫“老贾”，是一个永不失忆、声音温暖的私人AI助理。
    使用的是最先进的 Gemini 模型。
    你的回复将被转换成语音，所以：
    1. **尽量口语化**，不要列太长的清单。
    2. **简练**，像聊微信语音一样，不要长篇大论。
    3. 语气要亲切、自然。
    """
    
    user_info_prompt = f"""
    \n\n【用户信息】
    你的主人叫: {user_profile.get('nickname', request.username)}
    性别: {user_profile.get('gender', '未知')}
    年龄段: {user_profile.get('age', '未知')}
    职业: {user_profile.get('occupation', '未知')}
    兴趣爱好: {user_profile.get('hobbies', '未知')}
    希望你的说话风格: {user_profile.get('style', '温馨治愈')}
    请根据这些信息调整你的语气和话题，更好地服务主人。
    """

    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash", # Use a stable model
        system_instruction=base_prompt + user_info_prompt
    )

    # 4. History
    history_data = storage.load_memory(request.username)
    chat_history = []
    for msg in history_data:
        parts = msg["parts"]
        if not isinstance(parts, list):
            parts = [parts]
        role = "user" if msg["role"] == "user" else "model"
        chat_history.append({"role": role, "parts": parts})

    # 5. Generate Response
    try:
        chat_session = model.start_chat(history=chat_history)
        response = chat_session.send_message(request.message)
        response_text = response.text
        
        # Save memory
        history_data.append({"role": "user", "parts": [request.message]})
        history_data.append({"role": "model", "parts": [response_text]})
        storage.save_memory(request.username, history_data)

        # 6. Generate Audio (Optional: return URL or base64)
        # For API, we might just return text, or generate audio file and return link.
        # Here we just return text to keep it simple for now.
        
        return {
            "response": response_text,
            "audio_url": "/audio/..." # To be implemented
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
