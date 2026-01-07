import streamlit as st
import storage
import time

def login_form():
    st.header("🔑 登录")
    with st.form("login_form"):
        username = st.text_input("用户名")
        password = st.text_input("密码", type="password")
        submitted = st.form_submit_button("登录")
        
        if submitted:
            if storage.verify_user(username, password):
                st.session_state.authenticated = True
                st.session_state.username = username
                st.success(f"欢迎回来, {username}!")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("用户名或密码错误")

def register_form():
    st.header("📝 注册新账号")
    
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
                time.sleep(1)
                st.rerun()
            else:
                st.error(msg)

def auth_flow():
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
