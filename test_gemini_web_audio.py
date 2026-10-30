"""
Gemini 网页版直接上传音频生成字幕测试脚本 (Playwright 自动化)

功能说明：
1. 自动复用已登录的 `tmp_gemini_profile` 浏览器会话（无需重复登录）。
2. 将本地音频文件直接上传至 Gemini 网页版。
3. 让 Gemini 听取音频并直接转写输出带有精准时间戳的标准 SRT 字幕。
"""

import os
import sys
import time
from playwright.sync_api import sync_playwright

PROFILE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tmp_gemini_profile")
DEFAULT_AUDIO = r"D:\AutoCutVideo_v2\AutoCutVideo_Lite\test1\tmp_autocut\extracted_audio.mp3"

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

def test_gemini_audio_transcription(
    audio_path: str = DEFAULT_AUDIO,
    headless: bool = False,
    prompt: str = "请仔细听这段音频，并将其完整转写为标准 SRT 字幕格式（包含序号、标准时间戳如 00:00:00,000 --> 00:00:02,000 以及识别文本），修正所有语音错别字，保持句子通顺。请直接输出完整SRT文本。"
):
    if not os.path.exists(audio_path):
        # 尝试回退查找
        fallback_paths = [
            r"D:\AutoCutVideo_v2\AutoCutVideo_Lite\test1\tmp_autocut\extracted_audio.mp3",
            r"D:\AutoCutVideo_v2\test_audio_sample.mp3"
        ]
        for fb in fallback_paths:
            if os.path.exists(fb):
                audio_path = fb
                break

    print(f"🚀 启动 Gemini 网页版音频直接转写测试 (静默无头: {headless})...")
    print(f"🎵 待上传音频: {audio_path} ({round(os.path.getsize(audio_path)/1024, 1)} KB)")
    print(f"📁 浏览器配置目录: {PROFILE_DIR}")

    channel_name, exe_path = find_browser_executable()
    if exe_path:
        print(f"🌐 系统浏览器: {exe_path}")

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

        print("🌐 正在进入 Google Gemini 网页版...")
        t0 = time.time()
        page.goto("https://gemini.google.com/app", timeout=60000)

        # 检查对话输入框是否就绪
        input_selector = 'div[role="textbox"], div.ql-editor[contenteditable="true"], rich-textarea div, textarea'
        try:
            page.wait_for_selector(input_selector, timeout=10000)
            print("✅ Gemini 对话界面已就绪，正在等待前端组件完全渲染 (3.5秒)...")
            time.sleep(3.5) # 留出充分时间让加号按钮的事件监听器绑定完成
        except Exception:
            print("⚠️ 正在等待用户完成登录...")
            page.wait_for_selector(input_selector, timeout=300000)
            print("✅ 登录成功，界面已就绪")
            time.sleep(3.0)

        # 1. 查找并触发文件上传
        print("📤 正在上传音频文件到 Gemini 网页...")
        t_upload_start = time.time()

        uploaded = False
        # 优先通过点击加号按钮触发原生菜单与文件选择器
        try:
            # 定位加号 / 附件选择按钮
            add_btn_selectors = [
                'button.attachment-picker-button',
                'button[aria-label*="加号"]',
                'button[aria-label*="添加"]',
                'button[aria-label*="上传"]',
                'button[aria-label*="Attach"]',
                'button[aria-label*="Add"]',
                'button:has(mat-icon:has-text("add"))',
                'button:has(span:has-text("add"))'
            ]
            
            target_add_btn = None
            for sel in add_btn_selectors:
                btn = page.locator(sel).first
                if btn.is_visible():
                    target_add_btn = btn
                    break

            if target_add_btn:
                print("🎯 找到附件加号按钮，准备点击...")
                target_add_btn.hover()
                time.sleep(0.5)
                target_add_btn.click()
                print("⏳ 已点击加号，等待上传菜单展开 (1.5秒)...")
                time.sleep(1.5)

                # 监听文件选择器并点击“从电脑上传”或“上传文件”
                menu_item_selector = 'button:has-text("从电脑上传"), button:has-text("从设备上传"), button:has-text("上传文件"), [data-test-id*="upload"], [role="menuitem"]:has-text("上传"), [role="menuitem"]:has-text("Upload"), [role="menuitem"]'
                
                with page.expect_file_chooser(timeout=10000) as fc_info:
                    upload_item = page.locator(menu_item_selector).first
                    if upload_item.is_visible():
                        print("📂 点击菜单项: 从电脑上传/上传文件...")
                        upload_item.click()
                    else:
                        print("📂 触发菜单项选择...")
                        page.locator('[role="menuitem"]').first.click()

                file_chooser = fc_info.value
                file_chooser.set_files(os.path.abspath(audio_path))
                uploaded = True
                print(f"✅ 文件选择成功！已将音频送入上传通道: {os.path.basename(audio_path)}")
        except Exception as ex:
            print(f"ℹ️ 菜单选择器尝试未直接捕获 ({ex})，切换为底层 input[type='file'] 注入...")
            try:
                page.set_input_files('input[type="file"]', os.path.abspath(audio_path))
                uploaded = True
            except Exception as e:
                print(f"❌ 注入文件失败: {e}")

        # 2. 关键：等待音频上传进度条结束，附件芯片（Chip）稳定出现在输入框内
        print("⏳ 正在等待音频在网页中完全上传并完成预解析 (请观察浏览器界面中的音频卡片)...")
        chip_selectors = [
            'attachment-chip',
            'mat-chip',
            '.file-preview',
            '.uploader-preview',
            '[aria-label*="删除"]',
            '[aria-label*="Remove"]',
            '.file-chip',
            'audio-player',
            '.audio-chip'
        ]
        
        chip_found = False
        for _ in range(40):
            for cs in chip_selectors:
                if page.locator(cs).count() > 0 and page.locator(cs).first.is_visible():
                    chip_found = True
                    break
            if chip_found:
                print("✅ 成功检测到音频附件卡片已牢固挂载到输入框！")
                break
            time.sleep(0.5)

        if not chip_found:
            print("⚠️ 未显式抓取到卡片 DOM，进行 8 秒安全缓冲等待文件上传完毕...")
            time.sleep(8)
        else:
            time.sleep(2) # 缓冲等待上传状态从 uploading 切换为 ready

        # 3. 输入转写提示词
        print("✍️ 正在输入转写提示词...")
        input_box = page.locator(input_selector).first
        input_box.click()
        try:
            input_box.fill(prompt)
        except Exception:
            input_box.type(prompt, delay=5)
        time.sleep(1)

        # 4. 发送请求
        print("🚀 正在提交转写任务给 Gemini...")
        t_send = time.time()
        send_btn_selector = 'button[aria-label*="发送"], button[aria-label*="Send"], button.send-button'
        try:
            send_btn = page.locator(send_btn_selector).first
            if send_btn.is_visible() and send_btn.is_enabled():
                send_btn.click()
            else:
                page.keyboard.press("Enter")
        except Exception:
            page.keyboard.press("Enter")

        # 5. 等待 Gemini 听取音频并完成生成
        print("🎙️ Gemini 正在深度理解音频并转写 SRT 字幕，请稍候（长音频约需 15~40 秒）...")
        time.sleep(6) # 缓冲等待大模型思考并输出

        response_selector = 'div.model-response-text, div[data-test-id="model-response-text"], message-content'
        try:
            page.wait_for_selector(response_selector, timeout=120000)
        except Exception:
            pass

        # 等待流式输出停止（文本长度在 2 秒内稳定不变）
        last_text = ""
        stable_count = 0
        for _ in range(120):
            responses = page.locator(response_selector).all()
            if responses:
                cur_text = responses[-1].inner_text()
                if cur_text and cur_text == last_text:
                    stable_count += 1
                    if stable_count >= 5:
                        break
                else:
                    stable_count = 0
                    last_text = cur_text
            time.sleep(1.0)

        t_cost = round(time.time() - t_send, 2)
        print("\n" + "="*60)
        print(f"🎉 音频转写与字幕生成完毕！(耗时: {t_cost} 秒)")
        print("="*60)
        print(last_text)
        print("="*60)

        # 保存结果到本地 srt
        out_srt = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gemini_audio_transcribed.srt")
        with open(out_srt, "w", encoding="utf-8") as f:
            f.write(last_text)
        print(f"💾 字幕已保存至: {out_srt}")

        context.close()
        return last_text

if __name__ == "__main__":
    is_headless = False
    target_audio = DEFAULT_AUDIO

    for arg in sys.argv[1:]:
        if arg.lower() == "headless":
            is_headless = True
        elif os.path.exists(arg):
            target_audio = arg

    test_gemini_audio_transcription(audio_path=target_audio, headless=is_headless)

