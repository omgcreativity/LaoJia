import time
import json
from DrissionPage import ChromiumPage, ChromiumOptions

# ================= 配置区 =================
# 1. 车队配置
TARGET_URL = 'https://claudechn.com/pastel/#/gemini-carlist'

# 2. 老贾配置
ZEABUR_URL = "https://laojia.zeabur.app"
LAOJIA_USER = "breezecity" 
# ==========================================

def run_laojia_bridge():
    co = ChromiumOptions()
    co.set_browser_path('/usr/bin/google-chrome')
    co.headless(True)
    
    # J1800 性能优化参数
    co.set_argument('--no-sandbox')
    co.set_argument('--disable-gpu')
    co.set_argument('--disable-dev-shm-usage')
    co.set_argument('--mute-audio') 
    
    browser = ChromiumPage(co)
    
    try:
        # ==========================================
        # 1. 初始化 Tab 1: Gemini 车队
        # ==========================================
        tab_gemini = browser.latest_tab
        tab_gemini.listen.start('geminiCarpage')
        
        print("🌍 [Tab 1] 正在访问车库...")
        tab_gemini.get(TARGET_URL)
        time.sleep(3)
        
        # 弹窗处理
        if tab_gemini.ele('text:今日不再弹出', timeout=5):
            tab_gemini.ele('text:今日不再弹出').click()
            if tab_gemini.ele('text=确定'): tab_gemini.ele('text=确定').click()

        # 选车逻辑
        print("🔍 正在分析车况...")
        res = tab_gemini.listen.wait(timeout=15)
        if res:
            car_list = res.response.body['data']['list']
            pro_cars = [c for c in car_list if c['isPro'] == True and c['status'] == 1]
            pro_cars.sort(key=lambda x: x['count'])
            best_car = pro_cars[0]
            print(f"🥇 选定最空闲车位: {best_car['carID']}")
            
            target_ele = tab_gemini.ele(f'text:{best_car["carID"]}', timeout=10)
            if target_ele:
                target_ele.click()
            else:
                tab_gemini.ele('text:Gemini').click()
        else:
            print("⚠️ 抓包超时，尝试盲点第一个车位...")
            tab_gemini.ele('text:Gemini').click()
            
        print("🚀 正在前往聊天室...")
        # J1800 might be slow, give it time to open tab/redirect
        time.sleep(5)
        
        # IMPORTANT: Switch to the latest tab in case a new tab was opened
        tab_gemini = browser.latest_tab
        print(f"📍 当前页面: {tab_gemini.title}")
        
        # URL 跳转检查 (防止 J1800 响应慢导致还在车库页)
        print("🔗 检查 URL 跳转状态...")
        url_ok = False
        for _ in range(15): # 等待 15 秒
            if "/#/chat/" in tab_gemini.url:
                print(f"✅ URL 确认: {tab_gemini.url}")
                url_ok = True
                break
            time.sleep(1)
        
        if not url_ok:
             print(f"⚠️ 警告: 15秒后 URL 仍未包含 /chat/ (当前: {tab_gemini.url})")

        # Wait for chat input to confirm we are in
        # Increased timeout for J1800
        # Fix: Use .ele() directly which waits (DrissionPage syntax fix)
        if not tab_gemini.ele('tag:textarea', timeout=45):
                print("⚠️ 警告: 45秒内未找到输入框，尝试刷新页面...")
                tab_gemini.refresh()
                time.sleep(5)
                # Check again
                if not tab_gemini.ele('tag:textarea', timeout=30):
                    print("❌ 严重错误: 无法加载聊天页面 (可能被重定向到了登录页)")
        else:
                print("✅ 成功抵达聊天页面")

        print("🎯 等待 Gemini 3 Pro 模型就绪...")
        # Wait for model selector
        model_btn = tab_gemini.ele('text=Gemini', timeout=15)
        if model_btn:
            model_btn.click()
            time.sleep(1)
            # Try multiple selectors for the model
            target_model = (tab_gemini.ele('text:3 Pro', timeout=5) or 
                           tab_gemini.ele('text:Gemini 3 Pro', timeout=5) or
                           tab_gemini.ele('text:1.5 Pro', timeout=5)) # Fallback
            if target_model: 
                target_model.click()
                print("✅ 模型切换成功")
            else:
                print("⚠️ 未找到目标模型，保持默认")
        else:
            print("⚠️ 未找到模型切换按钮 (可能是移动端视图或已隐藏)")

        # ==========================================
        # 2. 初始化 Tab 2: 老贾云端信箱
        # ==========================================
        print("📮 [Tab 2] 正在打开老贾信箱...")
        tab_laojia = browser.new_tab(f"{ZEABUR_URL}/?action=get&user={LAOJIA_USER}")
        time.sleep(8) 

        # ==========================================
        # 3. 联动：自动打招呼 (Auto Hello)
        # ==========================================
        print("� 正在建立连接 (Auto Hello)...")
        try:
            input_box = tab_gemini.ele('@placeholder=输入消息') or tab_gemini.ele('tag:textarea')
            if input_box:
                # 发送上线通知，不作为对话内容，只是激活
                # input_box.input("（系统：J1800 节点已上线，连接正常）")
                # 暂时不发消息，避免打扰，或者仅打印日志
                # 如果用户希望它是"老贾"，那应该由 api.py 的 prompt 决定。
                # 这里我们只确保页面是活跃的。
                pass
        except:
            pass

        print("� 双线程就绪，开始搬运...")
        
        error_count = 0
        
        while True:
            try:
                # --- A: 刷新信箱 ---
                tab_laojia.refresh()
                time.sleep(3) 
                
                page_text = tab_laojia.ele('tag:body').text
                
                if "BRIDGE_DATA:" in page_text:
                    try:
                        json_str = page_text.split("BRIDGE_DATA:")[1].split(":END")[0]
                        res_data = json.loads(json_str)
                        
                        if res_data.get("has_new"):
                            question = res_data["content"]
                            print(f"\n✨ [收到指令] {question}")
                            
                            # --- B: 直接操作 Tab 1 (不需要 activate) ---
                            # DrissionPage 允许直接向后台标签页发送指令
                            
                            input_box = tab_gemini.ele('@placeholder=输入消息') or tab_gemini.ele('tag:textarea')
                            if not input_box:
                                raise Exception("未找到输入框 (可能车位已失效)")
                            input_box.input(question)
                            
                            send_btn = tab_gemini.ele('xpath://button[contains(., "发送")]') or tab_gemini.ele('@title=发送')
                            send_btn.click()
                            
                            print("⏳ 等待回复...")
                            time.sleep(15) # 等待生成
                            
                            replies = tab_gemini.eles('.content') or tab_gemini.eles('.message-content')
                            if replies:
                                ans = replies[-1].text
                                print(f"🤖 拿到回复，正在回传...")
                                
                                # --- C: 用 Tab 2 回传 ---
                                put_url = f"{ZEABUR_URL}/?action=put&user={LAOJIA_USER}&msg={ans}"
                                tab_laojia.get(put_url)
                                print("📤 已回传")
                                
                                # 回传完切回接收模式
                                time.sleep(2)
                                tab_laojia.get(f"{ZEABUR_URL}/?action=get&user={LAOJIA_USER}")
                        else:
                            # 没消息时显示个动态，证明脚本活着
                            print("📡 暂无新消息...", end='\r')
                            
                    except Exception as parse_e:
                         print(f"⚠️ 处理错误: {parse_e}")
                         raise parse_e
                else:
                    print(f"⚠️ 页面加载中... (文本长度: {len(page_text)})", end='\r')

            except Exception as e:
                print(f"\n⚠️ 异常: {e}")
                error_count += 1
                if error_count >= 3: # 连续3次错误就报警
                     try:
                        print("🚨 发送报警信息...")
                        # 必须对错误信息进行简单编码或截断，防止 URL 出错
                        safe_msg = str(e).replace('\n', ' ')[:50]
                        tab_laojia.get(f"{ZEABUR_URL}/?action=put&user={LAOJIA_USER}&msg=[⚠️ J1800 报警] {safe_msg}")
                     except: pass
                     
                     print("🔄 连续错误，退出程序以触发重启...")
                     break 

            time.sleep(5)

    except Exception as e:
        print(f"\n❌ 程序崩溃: {e}")
        try:
             safe_msg = str(e).replace('\n', ' ')[:50]
             browser.new_tab(f"{ZEABUR_URL}/?action=put&user={LAOJIA_USER}&msg=[☠️ J1800 崩溃] {safe_msg}")
             time.sleep(5)
        except: pass
        browser.quit()

if __name__ == "__main__":
    run_laojia_bridge()