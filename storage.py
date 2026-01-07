import os
import json
import hashlib
import uuid
from PIL import Image

DATA_FOLDER = "data"
USERS_FILE = os.path.join(DATA_FOLDER, "users.json")

def _get_user_folder(username):
    return os.path.join(DATA_FOLDER, "users", username)

def _get_images_folder(username):
    folder = os.path.join(_get_user_folder(username), "images")
    os.makedirs(folder, exist_ok=True)
    return folder

def init_storage():
    if not os.path.exists(DATA_FOLDER):
        os.makedirs(DATA_FOLDER)
    if not os.path.exists(os.path.join(DATA_FOLDER, "users")):
        os.makedirs(os.path.join(DATA_FOLDER, "users"))
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)

def get_user(username):
    init_storage()
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        users = json.load(f)
    return users.get(username)

def create_user(username, password, profile_data=None):
    init_storage()
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        users = json.load(f)
    
    if username in users:
        return False, "用户已存在"
    
    # Simple hash for password
    hashed_pw = hashlib.sha256(password.encode()).hexdigest()
    
    users[username] = {
        "password": hashed_pw,
        "created_at": str(os.path.getctime(USERS_FILE)) # Dummy timestamp logic, improved later
    }
    
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)
        
    # Create user specific folder and profile
    user_folder = _get_user_folder(username)
    os.makedirs(user_folder, exist_ok=True)
    
    if profile_data:
        save_profile(username, profile_data)
        
    return True, "注册成功"

def update_session_token(username):
    init_storage()
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        users = json.load(f)
    
    if username in users:
        token = str(uuid.uuid4())
        users[username]["token"] = token
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
        return token
    return None

def verify_session_token(username, token):
    user = get_user(username)
    if user and user.get("token") == token:
        return True
    return False

def verify_user(username, password):
    user = get_user(username)
    if not user:
        return False
    hashed_pw = hashlib.sha256(password.encode()).hexdigest()
    return user["password"] == hashed_pw

def save_profile(username, profile_data):
    user_folder = _get_user_folder(username)
    os.makedirs(user_folder, exist_ok=True)
    with open(os.path.join(user_folder, "profile.json"), "w", encoding="utf-8") as f:
        json.dump(profile_data, f, ensure_ascii=False, indent=2)

def load_profile(username):
    user_folder = _get_user_folder(username)
    profile_path = os.path.join(user_folder, "profile.json")
    if os.path.exists(profile_path):
        with open(profile_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_image(username, image):
    """Saves a PIL image and returns the relative path"""
    images_folder = _get_images_folder(username)
    filename = f"{uuid.uuid4()}.jpg"
    filepath = os.path.join(images_folder, filename)
    image.save(filepath)
    return f"images/{filename}"

def save_memory(username, history):
    user_folder = _get_user_folder(username)
    os.makedirs(user_folder, exist_ok=True)
    
    data_to_save = []
    for msg in history:
        role = msg["role"]
        parts = msg["parts"]
        
        # Normalize parts to a list
        if not isinstance(parts, list):
            parts = [parts]
            
        serializable_parts = []
        for part in parts:
            if isinstance(part, str):
                serializable_parts.append({"type": "text", "text": part})
            elif isinstance(part, dict) and "image_path" in part:
                # Already processed image dict
                serializable_parts.append(part)
            # We assume images in session state are already handled or won't be saved directly as objects here
            # In main.py, we should convert PIL images to paths before appending to history for saving
            
        data_to_save.append({"role": role, "parts": serializable_parts})
        
    with open(os.path.join(user_folder, "memory.json"), "w", encoding="utf-8") as f:
        json.dump(data_to_save, f, ensure_ascii=False, indent=2)

def load_memory(username):
    user_folder = _get_user_folder(username)
    memory_path = os.path.join(user_folder, "memory.json")
    if os.path.exists(memory_path):
        with open(memory_path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                # Convert back to simple format for app usage if needed, 
                # or adapt app to use structured parts.
                # For compatibility, we'll keep it structured.
                return data
            except:
                return []
    return []
