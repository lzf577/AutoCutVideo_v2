"""
Gemini 网页版自动化测试脚本 (基于 Playwright 独立环境)

功能说明：
1. 首次运行会自动弹出浏览器窗口，供您手动登录一次 Google 账号。
2. 登录成功后，登录状态会永久保存在本地 `tmp_gemini_profile` 缓存文件夹中。
3. 后续运行可开启静默模式（无头后台运行），自动打开 Gemini 网页版并提交字幕校对任务。
"""

import os
import sys
import time
from playwright.sync_api import sync_playwright

PROFILE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tmp_gemini_profile")

def find_browser_executable() -> tuple[str, str]:
    """智能查找系统中可用的 Chrome 或 Edge 浏览器路径"""
    candidates = [
        ("chrome", r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        ("chrome", r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
        ("chrome", os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")),
        ("msedge", r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
        ("msedge", r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
        ("msedge", os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe")),
    ]
    for channel, path in candidates:
        if os.path.exists(path):
            return channel, path
    return "msedge", ""

def test_gemini_web_interaction(headless: bool = False, prompt: str = "请帮我校对这段字幕的错别字：\n1\n00:00:00,000 --> 00:00:02,000\n大家豪，欢迎来到大好球场凤大镜。"):
    print(f"🚀 正在启动浏览器 (静默无头模式: {headless})...")
    print(f"📁 浏览器用户缓存目录: {PROFILE_DIR}")
    
    os.makedirs(PROFILE_DIR, exist_ok=True)
    channel_name, exe_path = find_browser_executable()
    if exe_path:
        print(f"🌐 自动检测到系统浏览器: {exe_path}")
    
    with sync_playwright() as p:
        launch_kwargs = {
            "user_data_dir": PROFILE_DIR,
            "headless": headless,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--start-maximized"
            ],
            "viewport": None
        }
        
        if exe_path:
            launch_kwargs["executable_path"] = exe_path
        else:
            launch_kwargs["channel"] = channel_name

        context = p.chromium.launch_persistent_context(**launch_kwargs)
        
        page = context.pages[0] if context.pages else context.new_page()
        
        print("🌐 正在访问 Google Gemini 网页版: https://gemini.google.com/app ...")
        t0 = time.time()
        page.goto("https://gemini.google.com/app", timeout=60000)
        
        # 检查是否处于已登录状态 (通过是否出现 Gemini 对话输入框判定)
        input_selector = 'div[role="textbox"], div.ql-editor[contenteditable="true"], rich-textarea div, textarea'
        
        is_logged_in = False
        try:
            page.wait_for_selector(input_selector, timeout=6000)
            is_logged_in = True
        except Exception:
            is_logged_in = False

        if not is_logged_in:
            print("\n" + "="*60)
            print("⚠️ 检测到当前尚未登录 Google 账号！")
            print("👉 请在弹出的 Edge 浏览器窗口中完成一次登录。登录后状态会自动永久保存在本地。")
            print("="*60 + "\n")
            
            # 等待用户完成登录并加载出输入框 (最多等待 5 分钟)
            page.wait_for_selector(input_selector, timeout=300000)
            print("✅ 登录成功！已成功就绪 Gemini 对话输入框。")
        
        # 聚焦并输入
        input_box = page.locator(input_selector).first
        input_box.click()
        try:
            input_box.fill(prompt)
        except Exception:
            input_box.type(prompt, delay=5)
        time.sleep(0.5)
        
        # 点击发送或回车
        print("📤 正在发送提示词给 Gemini...")
        t_send = time.time()
        
        # 尝试点击发送按钮或回车
        send_btn_selector = 'button[aria-label*="发送"], button[aria-label*="Send"], button.send-button'
        try:
            send_btn = page.locator(send_btn_selector).first
            if send_btn.is_visible():
                send_btn.click()
            else:
                page.keyboard.press("Enter")
        except Exception:
            page.keyboard.press("Enter")
        
        # 等待生成完成（监听停止生成按钮消失或复制按钮出现）
        print("⏳ 正在等待 Gemini 网页版生成回复...")
        time.sleep(3) # 缓冲等待流式输出开始
        
        # 等待回答元素出现并稳定
        response_selector = 'div.model-response-text, div[data-test-id="model-response-text"], message-content'
        try:
            page.wait_for_selector(response_selector, timeout=30000)
        except Exception:
            pass
        
        # 等待流式输出停止（文本长度在 1.5 秒内不再变化）
        last_text = ""
        stable_count = 0
        for _ in range(30):
            responses = page.locator(response_selector).all()
            if responses:
                cur_text = responses[-1].inner_text()
                if cur_text and cur_text == last_text:
                    stable_count += 1
                    if stable_count >= 3:
                        break
                else:
                    stable_count = 0
                    last_text = cur_text
            time.sleep(0.5)
            
        t_cost = round(time.time() - t_send, 2)
        print("\n" + "="*60)
        print(f"🎉 Gemini 网页版回答完成！(生成耗时: {t_cost} 秒)")
        print("="*60)
        print(last_text)
        print("="*60)
        
        context.close()
        return last_text

if __name__ == "__main__":
    # 首次建议使用 headless=False (有界面) 进行登录和观察
    is_headless = False
    if len(sys.argv) > 1 and sys.argv[1].lower() == "headless":
        is_headless = True
        
    test_gemini_web_interaction(headless=is_headless)
