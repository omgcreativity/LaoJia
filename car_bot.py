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

        # Wait for chat input to confirm we are in
        # Increased timeout for J1800
        if not tab_gemini.wait.ele('tag:textarea', timeout=45):
                print("⚠️ 警告: 45秒内未找到输入框，尝试刷新页面...")
                tab_gemini.refresh()
                time.sleep(5)
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

        print("🤖 双线程就绪，开始搬运...")
        
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
                         print(f"⚠️ 解析错误: {parse_e}")
                else:
                    print(f"⚠️ 页面加载中... (文本长度: {len(page_text)})", end='\r')

            except Exception as e:
                print(f"\n⚠️ 异常: {e}")
            
            time.sleep(5)

    except Exception as e:
        print(f"\n❌ 程序崩溃: {e}")
        browser.quit()

if __name__ == "__main__":
    run_laojia_bridge()