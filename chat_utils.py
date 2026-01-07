import streamlit as st
import streamlit.components.v1 as components
import re
import asyncio
import edge_tts
import os

def render_sound_check():
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
    components.html(sound_check_html, height=120)

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
    # Use a unique file name or overwrite
    output_file = "reply.mp3"
    try:
        asyncio.run(generate_audio(clean_text, output_file))
        st.audio(output_file, format='audio/mp3', start_time=0, autoplay=True)
    except Exception as e:
        st.warning(f"语音生成失败: {e}")
