import streamlit as st
import storage
import time
import extra_streamlit_components as stx
import datetime

# Cookie Manager Setup
@st.cache_resource(experimental_allow_widgets=True)
def get_manager():
    return stx.CookieManager(key="auth_cookie_manager")

def logout():
    """Logs out the user and clears session/cookies."""
    cookie_manager = get_manager()
    # Clear cookies
    cookie_manager.delete("username")
    cookie_manager.delete("token")
    
    # Clear session state
    st.session_state.authenticated = False
    st.session_state.username = None
    st.session_state.history = []
    
    # Rerun to show login screen
    st.rerun()

def login_form():
    st.header("🔑 登录")
    
    cookie_manager = get_manager()
    
    with st.form("login_form"):
        username = st.text_input("用户名")
        password = st.text_input("密码", type="password")
        remember_me = st.checkbox("记住我 (30天免登录)")
        submitted = st.form_submit_button("登录")
        
        if submitted:
            if storage.verify_user(username, password):
                st.session_state.authenticated = True
                st.session_state.username = username
                
                # Handle Persistent Login
                if remember_me:
                    token = storage.update_session_token(username)
                    expires = datetime.datetime.now() + datetime.timedelta(days=30)
                    cookie_manager.set("username", username, expires_at=expires)
                    cookie_manager.set("token", token, expires_at=expires)
                
                st.success(f"欢迎回来, {username}!")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("用户名或密码错误")

def register_form():
    st.header("📝 注册新账号")
    
    cookie_manager = get_manager()
    
    # Step 1: Basic Auth
    with st.form("register_form"):
        new_username = st.text_input("设置用户名")
        new_password = st.text_input("设置密码", type="password")
        confirm_password = st.text_input("确认密码", type="password")
        
        st.markdown("### 👤 让我们了解你")
        st.caption("老贾需要了解你的一些基本信息，以便提供更好的服务。")
        
        col1, col2 = st.columns(2)
        with col1:
            nickname = st.text_input("怎么称呼你？(昵称)")
            age = st.text_input("你的年龄段 (如: 90后, 00后)")
        with col2:
            gender = st.selectbox("性别", ["保密", "男", "女"])
            occupation = st.text_input("你的职业/身份")
            
        hobbies = st.text_area("你的兴趣爱好 (例如: 喜欢看电影、编程、做饭)")
        style = st.selectbox("希望老贾的说话风格", ["温馨治愈", "幽默风趣", "专业严谨", "毒舌傲娇"])
        
        submitted = st.form_submit_button("注册并创建助理")
        
        if submitted:
            if not new_username or not new_password:
                st.error("请输入用户名和密码")
                return
            
            if new_password != confirm_password:
                st.error("两次输入的密码不一致")
                return
            
            profile_data = {
                "nickname": nickname or new_username,
                "age": age,
                "gender": gender,
                "occupation": occupation,
                "hobbies": hobbies,
                "style": style
            }
            
            success, msg = storage.create_user(new_username, new_password, profile_data)
            if success:
                st.success("注册成功！正在为您初始化老贾...")
                st.session_state.authenticated = True
                st.session_state.username = new_username
                
                # Auto-login after registration (optional, set cookies too?)
                token = storage.update_session_token(new_username)
                expires = datetime.datetime.now() + datetime.timedelta(days=30)
                cookie_manager.set("username", new_username, expires_at=expires)
                cookie_manager.set("token", token, expires_at=expires)
                
                time.sleep(1)
                st.rerun()
            else:
                st.error(msg)

def auth_flow():
    # Initialize CookieManager
    cookie_manager = get_manager()
    
    # If already authenticated in session, return True
    if st.session_state.get("authenticated", False):
        return True

    # Try to authenticate via cookies
    try:
        cookies = cookie_manager.get_all()
        c_username = cookies.get("username")
        c_token = cookies.get("token")
        
        if c_username and c_token:
            if storage.verify_session_token(c_username, c_token):
                st.session_state.authenticated = True
                st.session_state.username = c_username
                st.toast(f"欢迎回来, {c_username} (自动登录)")
                time.sleep(0.5) 
                st.rerun() 
    except Exception as e:
        # Ignore cookie errors
        pass

    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if st.session_state.authenticated:
        return True

    st.title("🎙️ 老贾 - 你的私人AI助理")
    
    tab1, tab2 = st.tabs(["登录", "注册"])
    
    with tab1:
        login_form()
    
    with tab2:
        register_form()
        
    return False
