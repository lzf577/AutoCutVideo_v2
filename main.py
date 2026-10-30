import os
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
import sys

# 【修复补丁】解决 PyInstaller 打包后 imageio 找不到 metadata 的问题
if getattr(sys, 'frozen', False):
    import importlib.metadata
    original_version = importlib.metadata.version
    def patched_version(pkg_name):
        if pkg_name == 'imageio':
            return '2.37.3'
        return original_version(pkg_name)
    importlib.metadata.version = patched_version


import json
import logging
import datetime
import subprocess

# 全局屏蔽所有由 subprocess 调用的控制台黑框 (包括 moviepy, imageio_ffmpeg, ffmpeg 等)
if sys.platform == "win32":
    _old_popen_init = subprocess.Popen.__init__
    def _new_popen_init(self, *args, **kwargs):
        if 'creationflags' not in kwargs:
            kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
        _old_popen_init(self, *args, **kwargs)
    subprocess.Popen.__init__ = _new_popen_init
from pathlib import Path
from dotenv import load_dotenv, set_key

if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(sys.executable)
else:
    application_path = os.path.dirname(os.path.abspath(__file__))
    
ENV_PATH = os.path.join(application_path, ".env")

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QFileDialog, QTextEdit, QLabel, QInputDialog, 
    QMessageBox, QComboBox, QSlider, QFontDialog, QMenuBar, QMenu,
    QLineEdit, QDialog, QFormLayout, QDialogButtonBox, QStackedLayout,
    QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QScrollArea, QSizePolicy, QSpinBox, QDoubleSpinBox, QButtonGroup, QRadioButton,
    QGroupBox, QSplitter, QFrame, QGridLayout, QProgressBar, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QUrl, QSize, QSizeF, QRect
from PyQt6.QtGui import QAction, QFont, QPixmap, QIcon, QImage
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget, QGraphicsVideoItem
from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsProxyWidget
from PyQt6.QtOpenGLWidgets import QOpenGLWidget

from core_processor import extract_audio, generate_srt, burn_subtitles
from timeline_model import Timeline, Track, TrackType, Clip
from timeline_ui import TimelineWidget
from timeline_ui import TimelineWidget
from timeline_renderer import render_timeline, generate_cover_preview
from cover_templates import COVER_TEMPLATES

SUBTITLE_TEMPLATES = {
    "default": {"name": "默认无样式 (Default)", "style": ""},
    "classic_white": {"name": "经典白边 (Classic White)", "style": "FontName=SimHei,FontSize=24,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2,Shadow=1,MarginV=80"},
    "retro_yellow": {"name": "复古黄字 (Retro Yellow)", "style": "FontName=SimHei,FontSize=24,PrimaryColour=&H0000FFFF,OutlineColour=&H00000000,Outline=2,Shadow=2,MarginV=80"},
    "variety_orange": {"name": "综艺橙蓝 (Variety Orange)", "style": "FontName=SimHei,FontSize=28,PrimaryColour=&H0000A5FF,OutlineColour=&H00FFFFFF,Outline=3,Shadow=0,MarginV=85"},
    "cinema_bold": {"name": "影院大字 (Cinema Bold)", "style": "FontName=SimHei,FontSize=28,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=1,Shadow=0,MarginV=90,Bold=1"}
}

# --- 剪映风格 深色 QSS ---
DARK_THEME_QSS = """
QMainWindow {
    background-color: #121212;
}
QWidget {
    color: #E0E0E0;
    font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
    font-size: 13px;
}
QSplitter::handle {
    background-color: #000000;
}
QTabWidget::pane {
    border: 1px solid #333333;
    background-color: #181818;
}
QTabBar::tab {
    background: #181818;
    color: #888888;
    padding: 8px 16px;
    border: none;
    border-bottom: 2px solid transparent;
}
QTabBar::tab:selected {
    color: #FFFFFF;
    border-bottom: 2px solid #2980b9;
    font-weight: bold;
}
QTabBar::tab:hover {
    color: #FFFFFF;
}
QPushButton {
    background-color: #333333;
    color: #FFFFFF;
    border: none;
    border-radius: 4px;
    padding: 6px 12px;
}
QPushButton:hover {
    background-color: #444444;
}
QPushButton:pressed {
    background-color: #555555;
}
QPushButton#PrimaryBtn {
    background-color: #2980b9;
    font-weight: bold;
}
QPushButton#PrimaryBtn:hover {
    background-color: #3498db;
}
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background-color: #242424;
    border: 1px solid #444444;
    border-radius: 4px;
    padding: 4px;
    color: #FFFFFF;
}
QComboBox QAbstractItemView {
    background-color: #242424;
    color: #FFFFFF;
    selection-background-color: #2980b9;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border: 1px solid #2980b9;
}
QLabel {
    color: #BBBBBB;
}
QListWidget {
    background-color: #181818;
    border: none;
    outline: none;
}
QListWidget::item {
    padding: 10px;
    color: #888888;
}
QListWidget::item:selected {
    background-color: #2D2D2D;
    color: #FFFFFF;
    border-left: 3px solid #2980b9;
}
QTextEdit {
    background-color: #1A1A1A;
    border: 1px solid #333333;
    color: #CCCCCC;
}
QMenuBar {
    background-color: #121212;
    color: #E0E0E0;
}
QMenuBar::item {
    background-color: transparent;
    padding: 4px 10px;
}
QMenuBar::item:selected {
    background-color: #2980b9;
    color: #FFFFFF;
}
QMenu {
    background-color: #181818;
    color: #E0E0E0;
    border: 1px solid #333333;
}
QMenu::item {
    padding: 6px 20px;
}
QMenu::item:selected {
    background-color: #2980b9;
    color: #FFFFFF;
}
QMessageBox {
    background-color: #1A1A1A;
}
QMessageBox QLabel {
    color: #E0E0E0;
}
QMessageBox QPushButton {
    background-color: #333333;
    color: #FFFFFF;
    min-width: 60px;
    padding: 6px 12px;
}
QMessageBox QPushButton:hover {
    background-color: #444444;
}
"""

class CustomVideoWidget(QGraphicsView):
    clicked = pyqtSignal()
    doubleClicked = pyqtSignal()
    resized = pyqtSignal(int, int)
    
    def __init__(self):
        super().__init__()
        self.setStyleSheet("border: none; background-color: black;")
        # CRITICAL: Use OpenGL viewport to correctly render hardware video frames!
        self.setViewport(QOpenGLWidget())
        
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.video_item = QGraphicsVideoItem()
        self.scene.addItem(self.video_item)
        
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
    def mouseReleaseEvent(self, event):
        self.clicked.emit()
        super().mouseReleaseEvent(event)
        
    def mouseDoubleClickEvent(self, event):
        self.doubleClicked.emit()
        super().mouseDoubleClickEvent(event)
        
    def resizeEvent(self, event):
        super().resizeEvent(event)
        w, h = self.width(), self.height()
        self.scene.setSceneRect(0, 0, w, h)
        self.video_item.setSize(QSizeF(w, h))
        self.resized.emit(w, h)

class ProcessWorker(QThread):
    progress_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)
    srt_parsed_signal = pyqtSignal(list)
    
    def __init__(self, video_path, api_key, base_url, whisper_model, llm_model_name, output_dir, audio_bitrate, subtitle_lang, max_chars, tmp_dir):
        super().__init__()
        self.video_path = video_path
        self.api_key = api_key
        self.base_url = base_url
        self.whisper_model = whisper_model
        self.llm_model_name = llm_model_name
        self.output_dir = output_dir
        self.audio_bitrate = audio_bitrate
        self.subtitle_lang = subtitle_lang
        self.max_chars = max_chars
        self.tmp_dir = tmp_dir
        
    def run(self):
        temp_audio = None
        temp_srt = None
        try:
            import hashlib
            import os
            video_hash = hashlib.md5(self.video_path.encode()).hexdigest()[:8]
            sub_dir = os.path.join(self.tmp_dir, "subtitles")
            os.makedirs(sub_dir, exist_ok=True)
            
            cached_ai_srt = os.path.join(sub_dir, f"subtitles_{video_hash}_ai.srt")
            cached_local_srt = os.path.join(sub_dir, f"subtitles_{video_hash}_local.srt")
            
            import glob
            
            # 1. 精确匹配哈希
            if os.path.exists(cached_ai_srt) and os.path.getsize(cached_ai_srt) > 0:
                self.progress_signal.emit(f"✅ 检测到该视频已有缓存的 AI 翻译字幕，直接复用！")
                temp_srt = cached_ai_srt
            elif os.path.exists(cached_local_srt) and os.path.getsize(cached_local_srt) > 0:
                self.progress_signal.emit(f"✅ 检测到该视频已有缓存的初稿字幕，直接进入 AI 校对！")
                from core_processor import polish_srt_with_llm
                polish_srt_with_llm(cached_local_srt, cached_ai_srt, self.api_key, self.base_url, self.llm_model_name, self.progress_signal.emit)
                temp_srt = cached_ai_srt if os.path.exists(cached_ai_srt) else cached_local_srt
            else:
                # 2. 模糊匹配最新文件 (向下兼容旧版本 UUID 命名的缓存)
                ai_srts = glob.glob(os.path.join(sub_dir, "*_ai.srt"))
                local_srts = glob.glob(os.path.join(sub_dir, "*_local.srt"))
                
                if ai_srts:
                    latest_ai = max(ai_srts, key=os.path.getctime)
                    self.progress_signal.emit(f"✅ 检测到该目录存在最新 AI 字幕 ({os.path.basename(latest_ai)})，直接复用！")
                    temp_srt = latest_ai
                elif local_srts:
                    latest_local = max(local_srts, key=os.path.getctime)
                    self.progress_signal.emit(f"✅ 检测到该目录存在最新初稿字幕 ({os.path.basename(latest_local)})，直接进入 AI 校对！")
                    from core_processor import polish_srt_with_llm
                    polish_srt_with_llm(latest_local, cached_ai_srt, self.api_key, self.base_url, self.llm_model_name, self.progress_signal.emit)
                    temp_srt = cached_ai_srt if os.path.exists(cached_ai_srt) else latest_local
                else:
                    # 3. 实在没有缓存，走完整流程
                    temp_audio = extract_audio(self.video_path, self.tmp_dir, self.audio_bitrate, self.progress_signal.emit)
                    temp_srt = generate_srt(temp_audio, self.tmp_dir, self.whisper_model, self.api_key, self.base_url, self.subtitle_lang, self.max_chars, self.progress_signal.emit, self.llm_model_name, video_hash=video_hash)
            parsed_data = []
            with open(temp_srt, 'r', encoding='utf-8') as f:
                content = f.read()
            blocks = content.strip().split('\n\n')
            for block in blocks:
                lines = [l for l in block.split('\n') if l.strip()]
                if len(lines) >= 2:
                    time_idx = -1
                    for i, l in enumerate(lines):
                        if '-->' in l:
                            time_idx = i
                            break
                    if time_idx != -1:
                        time_line = lines[time_idx]
                        text = '\n'.join(lines[time_idx+1:])
                        start_str, end_str = time_line.split('-->')
                        def time_to_ms(ts):
                            try:
                                ts = ts.strip().replace(',', '.')
                                h, m, s = ts.split(':')
                                s, ms = s.split('.')
                                return int(h)*3600000 + int(m)*60000 + int(s)*1000 + int(ms)
                            except:
                                return 0
                        parsed_data.append({'start': time_to_ms(start_str), 'end': time_to_ms(end_str), 'text': text})
            self.srt_parsed_signal.emit(parsed_data)
            self.finished_signal.emit(True, temp_srt)
        except Exception as e:
            self.progress_signal.emit(f"❌ 发生严重错误: {str(e)}")
            self.finished_signal.emit(False, "")

class RetryAIWorker(QThread):
    progress_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)
    srt_parsed_signal = pyqtSignal(list)
    
    def __init__(self, srt_path_local, api_key, base_url, llm_model_name, tmp_dir):
        super().__init__()
        self.srt_path_local = srt_path_local
        self.api_key = api_key
        self.base_url = base_url
        self.llm_model_name = llm_model_name
        self.tmp_dir = tmp_dir
        
    def run(self):
        try:
            import os
            from core_processor import polish_srt_with_llm
            import uuid
            
            sub_dir = os.path.join(self.tmp_dir, "subtitles")
            os.makedirs(sub_dir, exist_ok=True)
            base_name = f"subtitles_retry_{uuid.uuid4().hex[:8]}"
            srt_path_ai = os.path.join(sub_dir, f"{base_name}_ai.srt")
            
            actual_model = self.llm_model_name
            if not actual_model or "自动" in actual_model:
                actual_model = "gemini-2.5-flash"
            
            polish_srt_with_llm(self.srt_path_local, srt_path_ai, self.api_key, self.base_url, actual_model, self.progress_signal.emit)
            
            if not os.path.exists(srt_path_ai):
                raise Exception("AI 字幕生成失败，请检查网络或API Key")
                
            parsed_data = []
            with open(srt_path_ai, 'r', encoding='utf-8') as f:
                content = f.read()
            blocks = content.strip().split('\n\n')
            for block in blocks:
                lines = [l for l in block.split('\n') if l.strip()]
                if len(lines) >= 2:
                    time_idx = -1
                    for i, l in enumerate(lines):
                        if '-->' in l:
                            time_idx = i
                            break
                    if time_idx != -1:
                        time_line = lines[time_idx]
                        text = '\n'.join(lines[time_idx+1:])
                        start_str, end_str = time_line.split('-->')
                        def time_to_ms(ts):
                            try:
                                ts = ts.strip().replace(',', '.')
                                h, m, s = ts.split(':')
                                s, ms = s.split('.')
                                return int(h)*3600000 + int(m)*60000 + int(s)*1000 + int(ms)
                            except:
                                return 0
                        parsed_data.append({'start': time_to_ms(start_str), 'end': time_to_ms(end_str), 'text': text})
            self.srt_parsed_signal.emit(parsed_data)
            self.finished_signal.emit(True, srt_path_ai)
        except Exception as e:
            self.progress_signal.emit(f"❌ 再次校对发生错误: {str(e)}")
            self.finished_signal.emit(False, "")

class SlideProcessWorker(QThread):
    progress_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, list) 

    def __init__(self, slide_source, srt_data, api_key, base_url, model_name, image_dir, advance_ms, tmp_dir, min_dur=3000, max_dur=15000):
        super().__init__()
        self.slide_source = slide_source
        self.srt_data = srt_data
        self.api_key = api_key
        self.base_url = base_url
        self.model_name = model_name
        self.image_dir = image_dir
        self.advance_ms = advance_ms
        self.tmp_dir = tmp_dir
        self.min_dur = min_dur
        self.max_dur = max_dur

    def run(self):
        from slide_processor import convert_pdf_to_images, convert_pptx_to_images, ai_analyze_slides, ai_match_subtitle_range
        try:
            import hashlib
            import glob
            import os
            
            import shutil
            
            if isinstance(self.slide_source, str):
                sources = [self.slide_source]
            else:
                sources = self.slide_source
                
            source_str = "".join(sources)
            source_hash = hashlib.md5(source_str.encode()).hexdigest()[:8]
            mixed_image_dir = os.path.join(self.image_dir, f"mixed_{source_hash}")
            os.makedirs(mixed_image_dir, exist_ok=True)
            cache_dir = mixed_image_dir
            
            image_paths = []
            
            existing_images = sorted(glob.glob(os.path.join(mixed_image_dir, "slide_*.jpg")))
            if existing_images:
                self.progress_signal.emit(f"✅ 检测到已缓存的插图集 ({len(existing_images)}张)，直接复用！")
                image_paths = existing_images
            else:
                self.progress_signal.emit(f"✅ 准备处理 {len(sources)} 个源文件...")
                for idx, src in enumerate(sources):
                    if src.lower().endswith('.pdf'):
                        self.progress_signal.emit(f"📄 正在将PDF ({os.path.basename(src)}) 转换为图片...")
                        pdf_sub = os.path.join(mixed_image_dir, f"pdf_part_{idx}")
                        os.makedirs(pdf_sub, exist_ok=True)
                        extracted = convert_pdf_to_images(
                            src, pdf_sub,
                            progress_callback=self.progress_signal.emit
                        )
                        for p in extracted:
                            new_name = f"slide_{len(image_paths):04d}.jpg"
                            new_path = os.path.join(mixed_image_dir, new_name)
                            shutil.copy2(p, new_path)
                            image_paths.append(new_path)
                    elif src.lower().endswith(('.pptx', '.ppt')):
                        self.progress_signal.emit(f"📄 正在将PPT ({os.path.basename(src)}) 转换为图片...")
                        pptx_sub = os.path.join(mixed_image_dir, f"pptx_part_{idx}")
                        os.makedirs(pptx_sub, exist_ok=True)
                        extracted = convert_pptx_to_images(
                            src, pptx_sub,
                            progress_callback=self.progress_signal.emit
                        )
                        for p in extracted:
                            new_name = f"slide_{len(image_paths):04d}.jpg"
                            new_path = os.path.join(mixed_image_dir, new_name)
                            shutil.copy2(p, new_path)
                            image_paths.append(new_path)
                    else:
                        new_name = f"slide_{len(image_paths):04d}.jpg"
                        new_path = os.path.join(mixed_image_dir, new_name)
                        shutil.copy2(src, new_path)
                        image_paths.append(new_path)

            self.progress_signal.emit("🤖 正在识别幻灯片内容...")
            cache_path = os.path.join(cache_dir, "slide_index.json")
            
            # 兼容：如果新的哈希目录里没有 cache_path，但外层有，则拷贝进来
            old_cache_path = os.path.join(self.image_dir, "slide_index.json")
            if not os.path.exists(cache_path) and os.path.exists(old_cache_path):
                try:
                    import shutil
                    shutil.copy2(old_cache_path, cache_path)
                except Exception:
                    pass
                    
            slide_index = ai_analyze_slides(
                image_paths, self.api_key, self.base_url, self.model_name,
                cache_path=cache_path, compressed_image_paths=None,
                progress_callback=self.progress_signal.emit
            )

            self.progress_signal.emit("🔗 正在匹配时间轴...")
            timing_list = ai_match_subtitle_range(
                slide_index, self.srt_data, self.api_key, self.base_url, self.model_name,
                advance_ms=self.advance_ms, progress_callback=self.progress_signal.emit
            )
            
            clips = []
            for item in timing_list:
                desc = item.get("description", "")
                # 按每秒阅读 5 个字计算出图片最佳阅读时长（转毫秒）
                reading_ms = int((len(desc) / 5.0) * 1000) if len(desc) > 0 else 5000
                
                # AI匹配出的字幕总跨度
                matched_ms = item.get("hide_ms", item["insert_ms"] + reading_ms) - item["insert_ms"]
                
                # 最终时长：取阅读时长和匹配时长的较小值（字少就早点切回真人，讲得短也早点切）
                final_duration = min(reading_ms, matched_ms)
                # 限制上下限：最少展示 min_dur，最长不超过 max_dur（避免长时间遮挡主视频）
                final_duration = min(self.max_dur, max(self.min_dur, final_duration))

                c = Clip(
                    name=f"幻灯片 {item['slide_idx']}",
                    source_path=item["image_path"],
                    start_time=item["insert_ms"],
                    duration=final_duration,
                    clip_type=TrackType.IMAGE,
                    description=desc
                )
                clips.append(c)

            self.finished_signal.emit(True, clips)
        except Exception as e:
            self.progress_signal.emit(f"❌ 错误: {e}")
            self.finished_signal.emit(False, [])

class AIRewriteArticleWorker(QThread):
    progress_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str, str)

    def __init__(self, srt_data, image_clips, api_key, base_url, model, out_dir, video_name=""):
        super().__init__()
        self.srt_data = srt_data
        self.image_clips = image_clips
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.out_dir = out_dir
        self.video_name = video_name

    def run(self):
        try:
            import os
            from openai import OpenAI
            import shutil
            
            transcript = ""
            for item in self.srt_data:
                transcript += item['text'] + " "
                
            image_info = []
            for i, clip in enumerate(self.image_clips):
                img_name = os.path.basename(clip.source_path)
                total_s = int(clip.start_time / 1000)
                m, s = divmod(total_s, 60)
                image_info.append(f"图片{i+1}: 出现时间点 {m}分{s}秒, 文件名: {img_name}")
                
                target_img_path = os.path.join(self.out_dir, img_name)
                try:
                    if not os.path.exists(target_img_path) or os.path.abspath(clip.source_path) != os.path.abspath(target_img_path):
                        shutil.copy2(clip.source_path, target_img_path)
                except Exception:
                    pass
            
            self.progress_signal.emit("🧠 正在组织文案，请求 AI 进行智能改写...")
            
            system_prompt = (
                "你是一个专业的微信公众号爆款文章写手。我会给你一份视频的逐字稿，以及视频中插入的幻灯片/配图的时间点和文件名。\n"
                "请你根据这些内容，重新润色、改写成一篇结构清晰、吸引人的微信公众号图文文章。\n"
                "要求：\n"
                "1. 去除口语化和冗余词汇，分段清晰，提炼出吸引人的小标题。\n"
                "2. 语气流畅专业，适合微信公众号阅读习惯（段落短，重点突出）。\n"
                "3. 根据我提供的【配图信息】，在文章的相关逻辑位置插入对应的配图。\n"
                "4. 插入配图的语法必须使用标准 Markdown：![幻灯片插图](对应的文件名)\n"
                "5. 你的回复应该是纯净的 Markdown 文章内容，不要输出任何寒暄废话。"
            )
            
            user_prompt = f"【配图信息】：\n{chr(10).join(image_info)}\n\n【视频逐字稿】：\n{transcript}"
            
            api_keys = [k.strip() for k in self.api_key.replace("，", "\n").replace(",", "\n").split("\n") if k.strip()]
            if not api_keys:
                raise Exception("未配置 API Key")
                
            fallback_models = [
                "gemini-2.5-flash",
                "gemini-2.5-flash-lite",
                "gemini-3-flash-preview",
                "gemini-3.1-flash-lite",
                "gemini-3.5-flash",
                "gemini-robotics-er-1.6-preview"
            ]
            
            models = []
            if "轮询" in self.model or "Round-Robin" in self.model:
                models = fallback_models
            else:
                models = [m.strip() for m in self.model.replace("，", ",").split(",") if m.strip()]
                for m in fallback_models:
                    if m not in models:
                        models.append(m)
            
            success = False
            response_text = ""
            
            import time
            for idx, cur_key in enumerate(api_keys):
                if success:
                    break
                masked_key = cur_key[:10] + "..." + cur_key[-5:] if len(cur_key) > 15 else "***"
                self.progress_signal.emit(f"🔑 正在使用 API Key (第 {idx+1}/{len(api_keys)} 个): {masked_key}")
                
                client = OpenAI(api_key=cur_key, base_url=self.base_url)
                
                for m_idx, cur_model in enumerate(models):
                    try:
                        response = client.chat.completions.create(
                            model=cur_model,
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt}
                            ],
                            temperature=0.7
                        )
                        response_text = response.choices[0].message.content
                        success = True
                        break
                    except Exception as e:
                        err_str = str(e)
                        short_err = err_str.split('\n')[0][:100] + "..." if len(err_str) > 100 else err_str
                        self.progress_signal.emit(f"⚠️ Key {idx+1}, 模型 {cur_model} 遇到问题 ({short_err})，尝试下一个...")
                        time.sleep(1)
                    
            if not success:
                raise Exception("所有 API Key 和模型均已请求失败，请检查网络或额度。")
                
            if self.video_name:
                filename = f"{self.video_name}_图文.md"
            else:
                filename = "图文稿件.md"
                
            article_path = os.path.join(self.out_dir, filename)
            with open(article_path, 'w', encoding='utf-8') as f:
                f.write(response_text)
                
            self.finished_signal.emit(True, article_path, response_text)
            
        except Exception as e:
            self.finished_signal.emit(False, str(e), "")

class BrollProcessWorker(QThread):
    progress_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, list) 

    def __init__(self, b_roll_video_path, srt_data, probability, image_clips=None, tmp_dir=None, min_dur=0.0, max_dur=0.0):
        super().__init__()
        self.b_roll_video_path = b_roll_video_path
        self.srt_data = srt_data
        self.probability = probability
        self.image_clips = image_clips or []
        self.tmp_dir = tmp_dir
        self.min_dur = min_dur
        self.max_dur = max_dur

    def run(self):
        try:
            import random
            from moviepy.editor import VideoFileClip
            from timeline_model import Clip, TrackType
            
            import os
            import subprocess
            
            import hashlib
            broll_hash = hashlib.md5(self.b_roll_video_path.encode()).hexdigest()[:8]
            self.progress_signal.emit(f"🎬 正在准备实体切片目录...")
            broll_dir = os.path.join(self.tmp_dir, f"broll_clips_{broll_hash}") if self.tmp_dir else f"broll_clips_{broll_hash}"
            os.makedirs(broll_dir, exist_ok=True)
            
            try:
                b_roll_clip = VideoFileClip(self.b_roll_video_path)
            except Exception as e:
                raise Exception(f"加载辅助视频失败: {e}")

            clips = []
            covered_count = 0
            just_inserted = False 
            broll_end_time_ms = 0
            
            self.progress_signal.emit(f"🎯 找到 {len(self.srt_data)} 句字幕基础，开始【按需动态提取】辅助素材...")
            
            # 兼容旧版本：顺便把可能存在于根目录旧文件夹的缓存挪过来
            old_broll_dir = os.path.join(self.tmp_dir, "broll_clips") if self.tmp_dir else "broll_clips"
            
            last_percent = -1
            for i, item in enumerate(self.srt_data):
                percent = int((i + 1) / len(self.srt_data) * 100)
                if percent != last_percent and percent % 10 == 0:
                    self.progress_signal.emit(f"   ⏳ 截取分析进度: {percent}% ...")
                    last_percent = percent
                    
                start_ms = item["start"]
                end_ms = item["end"]
                sentence_duration_s = (end_ms - start_ms) / 1000.0
                
                if start_ms < broll_end_time_ms:
                    just_inserted = False
                    continue
                
                # --- PDF 插图避让检测 ---
                # 如果这句字幕所在的时间段被任意一个 PDF 插图覆盖（有交集），则强制跳过，不插入 B-Roll
                is_covered_by_pdf = False
                for img_clip in self.image_clips:
                    if start_ms < img_clip.start_time + img_clip.duration and end_ms > img_clip.start_time:
                        is_covered_by_pdf = True
                        break
                        
                if is_covered_by_pdf:
                    just_inserted = False
                    continue
                
                # 优雅过滤算法
                if sentence_duration_s > 2.0 and not just_inserted and random.random() < self.probability:
                    if self.min_dur > 0 and self.max_dur >= self.min_dur:
                        target_duration_s = random.uniform(self.min_dur, self.max_dur)
                    else:
                        target_duration_s = sentence_duration_s
                        
                    actual_duration_s = min(target_duration_s, b_roll_clip.duration)
                    max_start_s = max(0, b_roll_clip.duration - actual_duration_s)
                    clip_start_s = random.uniform(0, max_start_s)
                    
                    actual_end_ms = start_ms + int(actual_duration_s * 1000)
                    broll_end_time_ms = actual_end_ms
                    
                    output_file = os.path.join(broll_dir, f"broll_{start_ms}_{actual_end_ms}.mp4")
                    old_output_file = os.path.join(old_broll_dir, f"broll_slice_{i+1}.mp4")
                    
                    if not os.path.exists(output_file) and os.path.exists(old_output_file):
                        try:
                            import shutil
                            shutil.copy2(old_output_file, output_file)
                        except:
                            pass
                            
                    if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                        self.progress_signal.emit(f"   ⚡ 命中缓存: 独立素材 [{start_ms}-{actual_end_ms}]")
                        c = Clip(
                            name=f"辅助切片 {i+1}",
                            source_path=output_file,
                            start_time=start_ms,
                            duration=int(actual_duration_s * 1000),
                            clip_type=TrackType.BROLL,
                            broll_start=0
                        )
                        clips.append(c)
                        covered_count += 1
                        just_inserted = True
                        continue
                        
                    self.progress_signal.emit(f"✂️ 正在物理截取素材 [{start_ms}-{actual_end_ms}]...")
                    
                    import imageio_ffmpeg
                    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
                    
                    cmd = [
                        ffmpeg_exe, "-y",
                        "-ss", str(clip_start_s),
                        "-i", self.b_roll_video_path,
                        "-t", str(actual_duration_s),
                        "-an", 
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                        output_file
                    ]
                    
                    try:
                        kwargs = {}
                        import platform
                        if platform.system() == "Windows":
                            kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
                        subprocess.run(cmd, check=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE, **kwargs)
                        
                        c = Clip(
                            name=f"辅助切片 {i+1}",
                            source_path=output_file,
                            start_time=start_ms,
                            duration=int(actual_duration_s * 1000),
                            clip_type=TrackType.BROLL,
                            broll_start=0 # 已经是独立文件了，所以从头播放
                        )
                        clips.append(c)
                        covered_count += 1
                        just_inserted = True
                    except Exception as ex:
                        print(f"FFmpeg slice error: {ex}")
                        just_inserted = False
                else:
                    just_inserted = False

            b_roll_clip.close()
            self.progress_signal.emit(f"🚀 动态提取完毕！共量身定制了 {covered_count} 段辅助画面。")
            self.finished_signal.emit(True, clips)
        except Exception as e:
            self.progress_signal.emit(f"❌ 辅助视频提取错误: {e}")
            self.finished_signal.emit(False, [])

class RenderWorker(QThread):
    progress_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, timeline, output_path, tmp_dir, style, hw_accel="auto", trim_start_s=0, trim_end_s=2, cover_path="", cover_duration=0.5, broll_transition="random", cover_title="", cover_subtitle="", cover_font="微软雅黑(加粗)", cover_template="classic_white_yellow", cover_custom_title="", cover_custom_subtitle="", cover_title_y=50, cover_spacing=2, cover_title_scale=100, cover_subtitle_scale=100):
        super().__init__()
        self.timeline = timeline
        self.output_path = output_path
        self.tmp_dir = tmp_dir
        self.style = style
        self.hw_accel = hw_accel
        self.trim_start_s = trim_start_s
        self.trim_end_s = trim_end_s
        self.cover_path = cover_path
        self.cover_duration = cover_duration
        self.cover_title = cover_title
        self.cover_subtitle = cover_subtitle
        self.cover_font = cover_font
        self.cover_template = cover_template
        self.cover_custom_title = cover_custom_title
        self.cover_custom_subtitle = cover_custom_subtitle
        self.cover_title_y = cover_title_y
        self.cover_spacing = cover_spacing
        self.cover_title_scale = cover_title_scale
        self.cover_subtitle_scale = cover_subtitle_scale
        self.broll_transition = broll_transition

    def run(self):
        try:
            out = render_timeline(
                self.timeline, 
                self.output_path, 
                self.tmp_dir, 
                self.style, 
                self.hw_accel, 
                self.trim_start_s,
                self.trim_end_s,
                self.cover_path,
                self.cover_duration,
                self.broll_transition,
                self.cover_title,
                self.cover_subtitle,
                self.cover_font,
                self.cover_template,
                self.cover_custom_title,
                self.cover_custom_subtitle,
                self.cover_title_y,
                self.cover_spacing,
                self.cover_title_scale,
                self.cover_subtitle_scale,
                progress_callback=self.progress_signal.emit
            )
            self.finished_signal.emit(True, out)
        except Exception as e:
            self.progress_signal.emit(f"❌ 渲染失败: {e}")
            self.finished_signal.emit(False, "")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI视频剪辑- AutoCutVideo V2.6.7")
        self.resize(1366, 800)
        
        # --- 初始化日志系统 ---
        self.log_dir = os.path.join(os.getcwd(), "logs")
        os.makedirs(self.log_dir, exist_ok=True)
        log_filename = os.path.join(self.log_dir, f"autocut_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        
        self.logger = logging.getLogger("AutocutVideo")
        self.logger.setLevel(logging.DEBUG)
        
        # 文件处理器
        fh = logging.FileHandler(log_filename, encoding='utf-8')
        fh.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        self.logger.addHandler(fh)
        
        # 控制台处理器
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        ch.setFormatter(formatter)
        self.logger.addHandler(ch)
        
        self.logger.info("应用程序启动，日志系统初始化完成。")
        
        load_dotenv(dotenv_path=ENV_PATH, override=True)
        
        self.video_path = ""
        self.slide_source = []
        self.cover_path = ""
        self.cover_duration = float(os.getenv("COVER_DURATION", "0.5"))
        self.cover_title = os.getenv("COVER_TITLE", "")
        self.cover_subtitle = os.getenv("COVER_SUBTITLE", "")
        self.cover_font = os.getenv("COVER_FONT", "微软雅黑(加粗)")
        self.cover_template = os.getenv("COVER_TEMPLATE", "classic_white_yellow")
        self.cover_custom_title = os.getenv("COVER_CUSTOM_TITLE", "")
        self.cover_custom_subtitle = os.getenv("COVER_CUSTOM_SUBTITLE", "")
        self.cover_title_y = int(os.getenv("COVER_TITLE_Y", "50"))
        self.cover_spacing = int(os.getenv("COVER_SPACING", "2"))
        self.cover_title_scale = int(os.getenv("COVER_TITLE_SCALE", "100"))
        self.cover_subtitle_scale = int(os.getenv("COVER_SUBTITLE_SCALE", "100"))
        self.export_dir = ""
        self.tmp_dir = ""
        self.srt_path = ""
        self.api_key = os.getenv("GEMINI_API_KEY", "")
        self.base_url = os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")
        self.selected_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self.audio_bitrate = os.getenv("GEMINI_AUDIO_BITRATE", "128k")
        self.whisper_model = os.getenv("WHISPER_MODEL", "base")
        self.subtitle_lang = os.getenv("GEMINI_SUBTITLE_LANG", "简体中文 (Simplified Chinese)")
        self.max_chars = os.getenv("GEMINI_MAX_CHARS", "30")
        self.selected_template_key = os.getenv("GEMINI_TEMPLATE_KEY", "classic_white")
        self.subtitle_margin_bottom = int(os.getenv("GEMINI_SUBTITLE_MARGIN", "80"))
        self.min_slide_duration = int(os.getenv("MIN_SLIDE_DURATION", "3000"))
        self.max_slide_duration = int(os.getenv("MAX_SLIDE_DURATION", "15000"))
        self.broll_min_duration = float(os.getenv("BROLL_MIN_DURATION", "0.0"))
        self.broll_max_duration = float(os.getenv("BROLL_MAX_DURATION", "0.0"))
        self.hw_accel = os.getenv("HW_ACCEL", "auto")
        self.trim_start_s = int(os.getenv("TRIM_START", "0"))
        self.trim_end_s = int(os.getenv("TRIM_END", "2"))
        self.broll_transition = os.getenv("BROLL_TRANSITION", "random")
        self.logo_x = int(os.getenv("LOGO_X", "0"))
        self.logo_y = int(os.getenv("LOGO_Y", "0"))
        self.logo_scale = int(os.getenv("LOGO_SCALE", "100"))
        self.last_opened_dir = os.getenv("LAST_OPENED_DIR", "")
        
        self.auto_pipeline_running = False
        
        self.auto_pipeline_running = False
        self.auto_pipeline_step = 0
        
        self.srt_data = []
        
        self.init_timeline_model()
        self.init_ui()
        self.setAcceptDrops(True)

    def init_timeline_model(self):
        self.timeline = Timeline()
        self.video_track = Track("主视频", TrackType.VIDEO)
        self.image_track = Track("贴纸/插图", TrackType.IMAGE)
        self.logo_track = Track("视频Logo", TrackType.LOGO)
        self.subtitle_track = Track("字幕", TrackType.SUBTITLE)
        self.cover_track = Track("视频封面", TrackType.COVER)
        self.broll_track = Track("辅助画面", TrackType.BROLL)
        
        self.timeline.add_track(self.video_track)
        self.timeline.add_track(self.image_track)
        self.timeline.add_track(self.logo_track)
        self.timeline.add_track(self.subtitle_track)
        self.timeline.add_track(self.cover_track)
        self.timeline.add_track(self.broll_track)

    def init_ui(self):
        self.create_menus()
        
        central_widget = QWidget()
        central_widget.setObjectName("CentralWidget")
        central_widget.setStyleSheet("QWidget#CentralWidget { background-color: #121212; }")
        self.setCentralWidget(central_widget)
        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(3)
        self.progress_bar.setStyleSheet("QProgressBar { border: none; background-color: #121212; } QProgressBar::chunk { background-color: #2980b9; }")
        self.progress_bar.hide()
        root_layout.addWidget(self.progress_bar)

        # 全局上下切割 (上部三大块，下部时间轴)
        main_splitter = QSplitter(Qt.Orientation.Vertical)
        
        # --- 上半部分 (Upper Section) ---
        upper_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 1. 左侧媒体与工具 (Left Panel)
        left_panel = QWidget()
        self.left_panel = left_panel
        left_panel.setObjectName("LeftPanel")
        left_panel.setStyleSheet("QWidget#LeftPanel { background-color: #181818; }")
        left_layout = QHBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)
        
        # 最左侧垂直导航菜单
        nav_list = QListWidget()
        nav_list.setFixedWidth(70)
        nav_list.addItem(QListWidgetItem("🎬\n基座"))
        nav_list.addItem(QListWidgetItem("📝\n字幕"))
        nav_list.addItem(QListWidgetItem("🖼️\n插图"))
        nav_list.addItem(QListWidgetItem("🎞️\n混剪"))
        nav_list.addItem(QListWidgetItem("🌟\nLogo"))
        nav_list.addItem(QListWidgetItem("🎴\n封面"))
        nav_list.addItem(QListWidgetItem("📤\n导出"))
        nav_list.setCurrentRow(0)
        left_layout.addWidget(nav_list)
        
        # 导航对应的功能区 (Stacked Widget)
        self.stacked_tools = QStackedLayout()
        
        # 媒体页面
        page_media = QWidget()
        l_media = QVBoxLayout(page_media)
        l_media.setContentsMargins(15, 15, 15, 15)
        self.lbl_video = QLabel("未导入基座视频，请拖拽或点击导入")
        l_media.addWidget(self.lbl_video)
        btn_import = QPushButton("导入基座视频")
        btn_import.setObjectName("PrimaryBtn")
        btn_import.clicked.connect(self.import_video)
        l_media.addWidget(btn_import)
        
        l_media.addStretch()
        self.stacked_tools.addWidget(page_media)
        
        # 文本页面
        page_text = QWidget()
        l_text = QVBoxLayout(page_text)
        l_text.setContentsMargins(15, 15, 15, 15)
        l_text.addWidget(QLabel("智能字幕生成："))
        btn_gen_sub = QPushButton("识别字幕")
        btn_gen_sub.setObjectName("PrimaryBtn")
        btn_gen_sub.clicked.connect(self.start_subtitle_gen)
        l_text.addWidget(btn_gen_sub)
        
        btn_import_sub = QPushButton("导入外部字幕")
        btn_import_sub.clicked.connect(self.import_external_subtitle)
        l_text.addWidget(btn_import_sub)
        
        btn_retry_ai = QPushButton("再次提交AI进行校对")
        btn_retry_ai.clicked.connect(self.retry_ai_correction)
        l_text.addWidget(btn_retry_ai)
        
        l_text.addStretch()
        self.stacked_tools.addWidget(page_text)
        
        # 插图页面
        page_pip = QWidget()
        l_pip = QVBoxLayout(page_pip)
        l_pip.setContentsMargins(15, 15, 15, 15)
        self.lbl_pdf = QLabel("已选择 0 个插图文件")
        l_pip.addWidget(self.lbl_pdf)
        
        h_btn_pip = QHBoxLayout()
        btn_add_pdf = QPushButton("添加 PDF")
        btn_add_pdf.clicked.connect(self.add_pdf)
        btn_add_ppt = QPushButton("添加 PPT")
        btn_add_ppt.clicked.connect(self.add_ppt)
        btn_add_images = QPushButton("添加图片")
        btn_add_images.clicked.connect(self.add_images)
        btn_clear_pip = QPushButton("清空")
        btn_clear_pip.clicked.connect(self.clear_slides)
        
        h_btn_pip.addWidget(btn_add_pdf)
        h_btn_pip.addWidget(btn_add_ppt)
        h_btn_pip.addWidget(btn_add_images)
        h_btn_pip.addWidget(btn_clear_pip)
        l_pip.addLayout(h_btn_pip)
        
        btn_gen_slide = QPushButton("AI 幻灯片匹配")
        btn_gen_slide.setObjectName("PrimaryBtn")
        btn_gen_slide.clicked.connect(self.start_slide_process)
        l_pip.addWidget(btn_gen_slide)
        l_pip.addStretch()
        self.stacked_tools.addWidget(page_pip)
        
        # 混剪(B-Roll)页面
        page_broll = QWidget()
        l_broll = QVBoxLayout(page_broll)
        l_broll.setContentsMargins(15, 15, 15, 15)
        
        self.lbl_broll = QLabel("未导入辅助视频")
        l_broll.addWidget(self.lbl_broll)
        btn_import_broll = QPushButton("导入辅助视频 (B-Roll)")
        btn_import_broll.clicked.connect(self.import_broll_video)
        l_broll.addWidget(btn_import_broll)
        
        l_broll.addSpacing(15)
        l_broll.addWidget(QLabel("B-Roll 辅助画面触发概率:"))
        self.broll_prob_slider = QSlider(Qt.Orientation.Horizontal)
        self.broll_prob_slider.setRange(0, 100)
        self.broll_prob_slider.setValue(60)
        self.lbl_broll_prob = QLabel("60%")
        broll_layout = QHBoxLayout()
        broll_layout.addWidget(self.broll_prob_slider)
        broll_layout.addWidget(self.lbl_broll_prob)
        self.broll_prob_slider.valueChanged.connect(lambda v: self.lbl_broll_prob.setText(f"{v}%"))
        l_broll.addLayout(broll_layout)
        
        btn_gen_broll = QPushButton("🎬 AI 智能提取辅助片段")
        btn_gen_broll.setObjectName("PrimaryBtn")
        btn_gen_broll.clicked.connect(self.start_broll_process)
        l_broll.addWidget(btn_gen_broll)
        
        l_broll.addStretch()
        self.stacked_tools.addWidget(page_broll)
        
        
        # Logo页面
        page_logo = QWidget()
        l_logo = QVBoxLayout(page_logo)
        l_logo.setContentsMargins(15, 15, 15, 15)
        self.lbl_logo = QLabel("您可以添加多个Logo到时间轴")
        l_logo.addWidget(self.lbl_logo)
        btn_logo = QPushButton("添加 Logo 轨道")
        btn_logo.setObjectName("PrimaryBtn")
        btn_logo.clicked.connect(self.select_logo)
        l_logo.addWidget(btn_logo)
        
        l_logo.addStretch()
        self.stacked_tools.addWidget(page_logo)
        
        # 封面页面
        page_cover = QWidget()
        l_cover = QVBoxLayout(page_cover)
        l_cover.setContentsMargins(15, 15, 15, 15)
        
        l_cover.addWidget(QLabel("<b>视频封面设置</b>"))
        self.lbl_cover = QLabel("未选择封面")
        l_cover.addWidget(self.lbl_cover)
        btn_cover = QPushButton("选择封面图片")
        btn_cover.clicked.connect(self.select_cover)
        l_cover.addWidget(btn_cover)
        
        l_cover.addStretch()
        self.stacked_tools.addWidget(page_cover)
        
        # 导出与裁剪页面
        page_export = QWidget()
        l_export = QVBoxLayout(page_export)
        l_export.setContentsMargins(15, 15, 15, 15)
        l_export.addWidget(QLabel("<b>导出与裁剪设置</b>"))
        
        self.lbl_export_path = QLabel(f"当前目录: {self.export_dir if self.export_dir else '未设置'}")
        self.lbl_export_path.setWordWrap(True)
        l_export.addWidget(self.lbl_export_path)
        
        btn_export_dir = QPushButton("设置导出目录")
        btn_export_dir.clicked.connect(self.set_export_dir)
        l_export.addWidget(btn_export_dir)
        
        l_export.addStretch()
        
        self.btn_export = QPushButton("📦 多格式打包导出...")
        self.btn_export.setObjectName("PrimaryBtn")
        self.btn_export.setMinimumHeight(50)
        self.btn_export.setStyleSheet("font-size: 16px; font-weight: bold; background-color: #0078D7; color: white; border-radius: 6px;")
        self.btn_export.clicked.connect(self.prompt_multi_export)
        l_export.addWidget(self.btn_export)
        
        self.btn_auto_export = QPushButton("⚡ 一键全自动导出视频")
        self.btn_auto_export.setObjectName("PrimaryBtn")
        self.btn_auto_export.setMinimumHeight(50)
        self.btn_auto_export.setStyleSheet("font-size: 16px; font-weight: bold; background-color: #E67E22; color: white; border-radius: 6px;")
        self.btn_auto_export.clicked.connect(self.start_auto_pipeline)
        l_export.addWidget(self.btn_auto_export)
        
        self.btn_stop_pipeline = QPushButton("🛑 紧急停止当前任务")
        self.btn_stop_pipeline.setMinimumHeight(40)
        self.btn_stop_pipeline.setStyleSheet("font-size: 14px; font-weight: bold; background-color: #C0392B; color: white; border-radius: 6px;")
        self.btn_stop_pipeline.clicked.connect(self.stop_all_tasks)
        self.btn_stop_pipeline.hide() # 默认隐藏
        l_export.addWidget(self.btn_stop_pipeline)
        
        self.stacked_tools.addWidget(page_export)
        
        nav_list.currentRowChanged.connect(self.stacked_tools.setCurrentIndex)
        nav_list.currentRowChanged.connect(self.on_nav_changed)
        
        tools_container = QWidget()
        tools_container.setLayout(self.stacked_tools)
        left_layout.addWidget(tools_container, stretch=1)
        
        upper_splitter.addWidget(left_panel)
        
        # 2. 中侧播放器 (Center Panel)
        player_panel = QWidget()
        player_panel.setObjectName("PlayerPanel")
        player_panel.setStyleSheet("QWidget#PlayerPanel { background-color: #0E0E0E; }")
        player_layout = QVBoxLayout(player_panel)
        player_layout.setContentsMargins(10, 10, 10, 10)
        
        # Use QGraphicsView with OpenGL viewport for hardware-accelerated video + overlays
        self.video_widget = CustomVideoWidget()
        self.video_widget.resized.connect(self.on_video_resized)
        
        # 悬浮的幻灯片预览
        self.image_preview_label = QLabel()
        self.image_preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_preview_label.setStyleSheet("background-color: transparent;")
        self.image_preview_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.image_preview_label.hide()
        self.image_proxy = self.video_widget.scene.addWidget(self.image_preview_label)
        self.image_proxy.setZValue(1)
        
        # 悬浮的 Logo 预览
        self.logo_preview_label = QLabel()
        self.logo_preview_label.setObjectName("logo_preview")
        self.logo_preview_label.setStyleSheet("background-color: transparent;")
        self.logo_preview_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.logo_preview_label.hide()
        self.logo_proxy = self.video_widget.scene.addWidget(self.logo_preview_label)
        self.logo_proxy.setZValue(2)
        
        # 悬浮的字幕预览
        self.lbl_subtitle_preview = QLabel("")
        self.lbl_subtitle_preview.setObjectName("subtitle_preview")
        self.lbl_subtitle_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_subtitle_preview.setStyleSheet("font-size: 28px; font-weight: bold; color: white; background-color: rgba(0,0,0,150); padding: 5px 15px; border-radius: 8px;")
        self.lbl_subtitle_preview.hide()
        self.subtitle_proxy = self.video_widget.scene.addWidget(self.lbl_subtitle_preview)
        self.subtitle_proxy.setZValue(3)
        
        player_layout.addWidget(self.video_widget, stretch=1)
        
        self.audio_output = QAudioOutput()
        self.media_player = QMediaPlayer()
        self.media_player.setAudioOutput(self.audio_output)
        self.media_player.setVideoOutput(self.video_widget.video_item)
        
        controls = QHBoxLayout()
        # 播放时间
        self.lbl_timecode = QLabel("00:00:00 / 00:00:00")
        self.lbl_timecode.setStyleSheet("color: #888888; font-family: monospace;")
        controls.addWidget(self.lbl_timecode)
        controls.addStretch()
        
        self.btn_play = QPushButton("▶")
        self.btn_play.setFixedSize(40, 40)
        self.btn_play.setStyleSheet("border-radius: 20px; font-size: 18px;")
        self.btn_play.clicked.connect(self.toggle_play_pause)
        controls.addWidget(self.btn_play)
        
        controls.addStretch()
        
        player_layout.addLayout(controls)
        # (The overlay setup was moved above)
        
        upper_splitter.addWidget(player_panel)
        
        # 3. 右侧属性 (Right Panel)
        right_panel = QWidget()
        self.right_panel = right_panel
        right_panel.setObjectName("RightPanel")
        right_panel.setStyleSheet("QWidget#RightPanel { background-color: #181818; }")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        self.stacked_properties = QStackedLayout()
        
        # 页面 1: 媒体属性 (全局与导出)
        page_prop_media = QWidget()
        l_prop_media = QVBoxLayout(page_prop_media)
        l_prop_media.setContentsMargins(15, 15, 15, 15)
        l_prop_media.addWidget(QLabel("<b>全局属性与导出</b>"))
        l_prop_media.addWidget(QLabel("AI大模型配置:"))
        
        self.api_key_input = QTextEdit()
        display_keys = self.api_key.replace(",", "\n") if self.api_key else ""
        self.api_key_input.setPlainText(display_keys)
        self.api_key_input.setPlaceholderText("请输入 API Key (每行一个)\n多 Key 将自动用于绕过免费限制")
        self.api_key_input.setMinimumHeight(250)
        l_prop_media.addWidget(self.api_key_input)
        
        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        self.model_combo.addItems([
            "自动智能轮询 (Auto Round-Robin)",
            "gemini-2.5-flash",
            "gemini-2.5-flash-lite",
            "gemini-3-flash-preview",
            "gemini-3.1-flash-lite",
            "gemini-3.5-flash",
            "gemini-robotics-er-1.6-preview"
        ])
        self.model_combo.setCurrentText(self.selected_model)
        l_prop_media.addWidget(self.model_combo)
        
        btn_save_model = QPushButton("保存配置")
        btn_save_model.clicked.connect(self.save_model_settings)
        l_prop_media.addWidget(btn_save_model)
        
        l_prop_media.addStretch()
        self.stacked_properties.addWidget(page_prop_media)
        
        # 页面 2: 文本属性 (字幕与音频)
        page_prop_text = QWidget()
        l_prop_text = QVBoxLayout(page_prop_text)
        l_prop_text.setContentsMargins(15, 15, 15, 15)
        l_prop_text.addWidget(QLabel("<b>字幕与音频设置</b>"))
        
        l_prop_text.addWidget(QLabel("音频提取码率:"))
        self.bitrate_combo = QComboBox()
        self.bitrate_combo.addItems(["8k", "16k", "32k", "64k", "128k", "192k", "256k", "320k"])
        self.bitrate_combo.setCurrentText(self.audio_bitrate)
        l_prop_text.addWidget(self.bitrate_combo)
        
        l_prop_text.addWidget(QLabel("字幕模型尺寸 (Whisper):"))
        self.whisper_combo = QComboBox()
        self.whisper_combo.addItems(["tiny", "base", "small", "medium", "large-v3"])
        self.whisper_combo.setCurrentText(self.whisper_model)
        l_prop_text.addWidget(self.whisper_combo)
        
        l_prop_text.addWidget(QLabel("目标字幕语言:"))
        self.lang_combo = QComboBox()
        self.lang_combo.setEditable(True)
        self.lang_combo.addItems([
            "简体中文 (Simplified Chinese)", 
            "繁体中文 (Traditional Chinese)", 
            "English"
        ])
        self.lang_combo.setCurrentText(self.subtitle_lang)
        l_prop_text.addWidget(self.lang_combo)
        
        l_prop_text.addWidget(QLabel("单行最大字符数:"))
        self.max_chars_spin = QSpinBox()
        self.max_chars_spin.setRange(10, 100)
        self.max_chars_spin.setValue(int(self.max_chars))
        l_prop_text.addWidget(self.max_chars_spin)
        
        l_prop_text.addWidget(QLabel("字幕底边距 (像素):"))
        self.margin_spin = QSpinBox()
        self.margin_spin.setRange(0, 500)
        self.margin_spin.setValue(self.subtitle_margin_bottom)
        l_prop_text.addWidget(self.margin_spin)
        
        l_prop_text.addWidget(QLabel("字幕渲染模板:"))
        self.template_combo = QComboBox()
        for key, val in SUBTITLE_TEMPLATES.items():
            self.template_combo.addItem(val["name"], key)
        idx = self.template_combo.findData(self.selected_template_key)
        if idx >= 0:
            self.template_combo.setCurrentIndex(idx)
        l_prop_text.addWidget(self.template_combo)
        
        btn_save_text = QPushButton("保存字幕设置")
        btn_save_text.clicked.connect(self.save_text_settings)
        l_prop_text.addWidget(btn_save_text)
        
        l_prop_text.addStretch()
        self.stacked_properties.addWidget(page_prop_text)
        
        # 页面 3: 插图属性
        page_prop_pip = QWidget()
        l_prop_pip = QVBoxLayout(page_prop_pip)
        l_prop_pip.setContentsMargins(15, 15, 15, 15)
        l_prop_pip.addWidget(QLabel("<b>插图与PDF设置</b>"))
        
        l_prop_pip.addWidget(QLabel("最短显示时长(秒):"))
        self.min_dur_spin = QSpinBox()
        self.min_dur_spin.setRange(1, 30)
        self.min_dur_spin.setSingleStep(1)
        self.min_dur_spin.setValue(self.min_slide_duration // 1000)
        l_prop_pip.addWidget(self.min_dur_spin)

        l_prop_pip.addWidget(QLabel("最长显示时长(秒):"))
        self.max_dur_spin = QSpinBox()
        self.max_dur_spin.setRange(2, 120)
        self.max_dur_spin.setSingleStep(1)
        self.max_dur_spin.setValue(self.max_slide_duration // 1000)
        l_prop_pip.addWidget(self.max_dur_spin)
        
        btn_save_pip = QPushButton("保存设置")
        btn_save_pip.clicked.connect(self.save_pip_settings)
        l_prop_pip.addWidget(btn_save_pip)
        l_prop_pip.addStretch()
        self.stacked_properties.addWidget(page_prop_pip)
        
        # 页面 3: 混剪(B-Roll) 属性设置
        page_prop_broll = QWidget()
        l_prop_broll = QVBoxLayout(page_prop_broll)
        l_prop_broll.setContentsMargins(15, 15, 15, 15)
        l_prop_broll.addWidget(QLabel("<b>混剪转场设置</b>"))
        
        l_prop_broll.addWidget(QLabel("辅助视频切片的转场特效:"))
        self.broll_trans_combo = QComboBox()
        self.broll_trans_combo.addItem("盲盒模式 (全随机)", "random")
        self.broll_trans_combo.addItem("平滑溶解 (0.5秒)", "smooth")
        self.broll_trans_combo.addItem("快速切入 (0.2秒)", "fast")
        self.broll_trans_combo.addItem("干脆硬切 (无过渡)", "hard")
        self.broll_trans_combo.addItem("抒情慢切 (0.8秒)", "slow")
        self.broll_trans_combo.addItem("黑场揭示", "fade_black")
        
        idx = self.broll_trans_combo.findData(getattr(self, 'broll_transition', 'random'))
        if idx >= 0:
            self.broll_trans_combo.setCurrentIndex(idx)
        l_prop_broll.addWidget(self.broll_trans_combo)
        
        # 添加混剪时长设置
        dur_layout = QHBoxLayout()
        dur_layout.addWidget(QLabel("自定义切片时长(秒) [为0则贴合单句]:"))
        self.spin_broll_min = QDoubleSpinBox()
        self.spin_broll_min.setRange(0.0, 60.0)
        self.spin_broll_min.setValue(getattr(self, 'broll_min_duration', 0.0))
        dur_layout.addWidget(self.spin_broll_min)
        
        dur_layout.addWidget(QLabel("-"))
        self.spin_broll_max = QDoubleSpinBox()
        self.spin_broll_max.setRange(0.0, 60.0)
        self.spin_broll_max.setValue(getattr(self, 'broll_max_duration', 0.0))
        dur_layout.addWidget(self.spin_broll_max)
        l_prop_broll.addLayout(dur_layout)
        
        btn_save_broll = QPushButton("保存设置")
        btn_save_broll.clicked.connect(self.save_broll_settings)
        l_prop_broll.addWidget(btn_save_broll)
        
        l_prop_broll.addStretch()
        self.stacked_properties.addWidget(page_prop_broll)
        
        # 页面 4: Logo属性
        page_prop_logo = QWidget()
        l_prop_logo = QVBoxLayout(page_prop_logo)
        l_prop_logo.setContentsMargins(15, 15, 15, 15)
        
        l_prop_logo.addWidget(QLabel("<b>全局 Logo 默认设置</b>"))
        
        logo_x_layout = QHBoxLayout()
        logo_x_layout.addWidget(QLabel("距右侧边缘距离 (px):"))
        self.spin_global_logo_x = QSpinBox()
        self.spin_global_logo_x.setRange(0, 9999)
        self.spin_global_logo_x.setValue(getattr(self, 'logo_x', 0))
        logo_x_layout.addWidget(self.spin_global_logo_x)
        l_prop_logo.addLayout(logo_x_layout)
        
        logo_y_layout = QHBoxLayout()
        logo_y_layout.addWidget(QLabel("距底部边缘距离 (px):"))
        self.spin_global_logo_y = QSpinBox()
        self.spin_global_logo_y.setRange(0, 9999)
        self.spin_global_logo_y.setValue(getattr(self, 'logo_y', 0))
        logo_y_layout.addWidget(self.spin_global_logo_y)
        l_prop_logo.addLayout(logo_y_layout)
        
        logo_scale_layout = QHBoxLayout()
        logo_scale_layout.addWidget(QLabel("缩放比例 (%):"))
        self.spin_global_logo_scale = QSpinBox()
        self.spin_global_logo_scale.setRange(1, 1000)
        self.spin_global_logo_scale.setValue(getattr(self, 'logo_scale', 100))
        logo_scale_layout.addWidget(self.spin_global_logo_scale)
        l_prop_logo.addLayout(logo_scale_layout)
        
        btn_save_logo = QPushButton("保存设置")
        btn_save_logo.clicked.connect(self.save_logo_settings)
        l_prop_logo.addWidget(btn_save_logo)
        
        l_prop_logo.addStretch()
        self.stacked_properties.addWidget(page_prop_logo)
        
        # 页面 5: 封面属性
        page_prop_cover = QWidget()
        l_prop_cover = QVBoxLayout(page_prop_cover)
        l_prop_cover.setContentsMargins(15, 15, 15, 15)
        
        l_prop_cover.addWidget(QLabel("<b>封面时长设置</b>"))
        cover_duration_layout = QHBoxLayout()
        cover_duration_layout.addWidget(QLabel("封面时长(秒):"))
        self.spin_cover_duration = QDoubleSpinBox()
        self.spin_cover_duration.setRange(0.1, 10.0)
        self.spin_cover_duration.setValue(getattr(self, 'cover_duration', 0.5))
        self.spin_cover_duration.setSingleStep(0.1)
        self.spin_cover_duration.valueChanged.connect(self.on_cover_duration_changed)
        cover_duration_layout.addWidget(self.spin_cover_duration)
        l_prop_cover.addLayout(cover_duration_layout)
        
        cover_title_layout = QHBoxLayout()
        cover_title_layout.addWidget(QLabel("主标题:"))
        self.txt_cover_title = QLineEdit()
        self.txt_cover_title.setText(getattr(self, 'cover_title', ''))
        cover_title_layout.addWidget(self.txt_cover_title)
        l_prop_cover.addLayout(cover_title_layout)
        
        cover_title_y_layout = QHBoxLayout()
        cover_title_y_layout.addWidget(QLabel("主标题离上边缘(%):"))
        self.spin_cover_title_y = QSpinBox()
        self.spin_cover_title_y.setRange(0, 100)
        self.spin_cover_title_y.setValue(getattr(self, 'cover_title_y', 50))
        cover_title_y_layout.addWidget(self.spin_cover_title_y)
        
        cover_title_y_layout.addWidget(QLabel("主副间距(%):"))
        self.spin_cover_spacing = QSpinBox()
        self.spin_cover_spacing.setRange(-50, 50)
        self.spin_cover_spacing.setValue(getattr(self, 'cover_spacing', 2))
        cover_title_y_layout.addWidget(self.spin_cover_spacing)
        
        l_prop_cover.addLayout(cover_title_y_layout)
        
        cover_scale_layout = QHBoxLayout()
        cover_scale_layout.addWidget(QLabel("主标大小(%):"))
        self.spin_cover_title_scale = QSpinBox()
        self.spin_cover_title_scale.setRange(10, 500)
        self.spin_cover_title_scale.setValue(getattr(self, 'cover_title_scale', 100))
        cover_scale_layout.addWidget(self.spin_cover_title_scale)
        
        cover_scale_layout.addWidget(QLabel("副标大小(%):"))
        self.spin_cover_subtitle_scale = QSpinBox()
        self.spin_cover_subtitle_scale.setRange(10, 500)
        self.spin_cover_subtitle_scale.setValue(getattr(self, 'cover_subtitle_scale', 100))
        cover_scale_layout.addWidget(self.spin_cover_subtitle_scale)
        
        l_prop_cover.addLayout(cover_scale_layout)
        
        cover_subtitle_layout = QHBoxLayout()
        cover_subtitle_layout.addWidget(QLabel("副标题:"))
        self.txt_cover_subtitle = QTextEdit()
        self.txt_cover_subtitle.setMinimumHeight(180)
        self.txt_cover_subtitle.setMaximumHeight(200)
        self.txt_cover_subtitle.setPlainText(getattr(self, 'cover_subtitle', ''))
        cover_subtitle_layout.addWidget(self.txt_cover_subtitle)
        l_prop_cover.addLayout(cover_subtitle_layout)
        
        cover_font_layout = QHBoxLayout()
        cover_font_layout.addWidget(QLabel("字体:"))
        self.combo_cover_font = QComboBox()
        self.combo_cover_font.addItems(["微软雅黑(加粗)", "微软雅黑", "黑体", "楷体", "宋体"])
        self.combo_cover_font.setCurrentText(getattr(self, 'cover_font', "微软雅黑(加粗)"))
        cover_font_layout.addWidget(self.combo_cover_font)
        l_prop_cover.addLayout(cover_font_layout)
        
        cover_template_layout = QHBoxLayout()
        cover_template_layout.addWidget(QLabel("样式模板:"))
        self.combo_cover_template = QComboBox()
        for k, v in COVER_TEMPLATES.items():
            self.combo_cover_template.addItem(v["name"], k)
        
        # Set current template
        current_idx = self.combo_cover_template.findData(getattr(self, 'cover_template', 'classic_white_yellow'))
        if current_idx >= 0:
            self.combo_cover_template.setCurrentIndex(current_idx)
        cover_template_layout.addWidget(self.combo_cover_template)
        l_prop_cover.addLayout(cover_template_layout)
        
        self.custom_style_widget = QWidget()
        custom_layout = QVBoxLayout(self.custom_style_widget)
        custom_layout.setContentsMargins(0, 0, 0, 0)
        
        custom_t_layout = QHBoxLayout()
        custom_t_layout.addWidget(QLabel("自定义主标题(FFmpeg):"))
        self.txt_cover_custom_t = QLineEdit()
        self.txt_cover_custom_t.setText(getattr(self, 'cover_custom_title', ''))
        custom_t_layout.addWidget(self.txt_cover_custom_t)
        custom_layout.addLayout(custom_t_layout)
        
        custom_s_layout = QHBoxLayout()
        custom_s_layout.addWidget(QLabel("自定义副标题(FFmpeg):"))
        self.txt_cover_custom_s = QLineEdit()
        self.txt_cover_custom_s.setText(getattr(self, 'cover_custom_subtitle', ''))
        custom_s_layout.addWidget(self.txt_cover_custom_s)
        custom_layout.addLayout(custom_s_layout)
        
        l_prop_cover.addWidget(self.custom_style_widget)
        
        def on_template_changed():
            is_custom = self.combo_cover_template.currentData() == "custom"
            self.custom_style_widget.setVisible(is_custom)
            
        self.combo_cover_template.currentIndexChanged.connect(on_template_changed)
        on_template_changed()
        
        cover_btns_layout = QHBoxLayout()
        
        btn_preview_cover_h = QPushButton("预览横屏封面")
        btn_preview_cover_h.clicked.connect(lambda: self.preview_cover("landscape"))
        cover_btns_layout.addWidget(btn_preview_cover_h)
        
        btn_preview_cover_v = QPushButton("预览竖屏封面")
        btn_preview_cover_v.clicked.connect(lambda: self.preview_cover("portrait"))
        cover_btns_layout.addWidget(btn_preview_cover_v)
        
        btn_save_cover = QPushButton("保存设置")
        btn_save_cover.clicked.connect(self.save_cover_settings)
        cover_btns_layout.addWidget(btn_save_cover)
        
        l_prop_cover.addLayout(cover_btns_layout)
        
        btn_open_cover_gen = QPushButton("🎨 打开独立封面生成器")
        btn_open_cover_gen.setObjectName("PrimaryBtn")
        btn_open_cover_gen.clicked.connect(self.open_standalone_cover_generator)
        l_prop_cover.addWidget(btn_open_cover_gen)
        
        l_prop_cover.addStretch()
        self.stacked_properties.addWidget(page_prop_cover)
        
        # 页面 5: 导出与裁剪属性
        page_prop_export = QWidget()
        l_prop_export = QVBoxLayout(page_prop_export)
        l_prop_export.setContentsMargins(15, 15, 15, 15)
        
        l_prop_export.addWidget(QLabel("<b>掐头去尾设置</b>"))
        l_prop_export.addWidget(QLabel("掐头 (秒):"))
        self.spin_trim_start = QSpinBox()
        self.spin_trim_start.setRange(0, 9999)
        self.spin_trim_start.setValue(self.trim_start_s)
        l_prop_export.addWidget(self.spin_trim_start)
        
        l_prop_export.addWidget(QLabel("去尾 (秒):"))
        self.spin_trim_end = QSpinBox()
        self.spin_trim_end.setRange(0, 9999)
        self.spin_trim_end.setValue(self.trim_end_s)
        l_prop_export.addWidget(self.spin_trim_end)
        
        l_prop_export.addSpacing(20)
        l_prop_export.addWidget(QLabel("<b>导出选项</b>"))
        
        l_prop_export.addWidget(QLabel("硬件加速(GPU)渲染:"))
        self.hw_accel_combo = QComboBox()
        self.hw_accel_combo.addItem("自动检测 (Auto)", "auto")
        self.hw_accel_combo.addItem("NVIDIA 显卡 (nvenc)", "h264_nvenc")
        self.hw_accel_combo.addItem("AMD 显卡 (amf)", "h264_amf")
        self.hw_accel_combo.addItem("Intel 核显 (qsv)", "h264_qsv")
        self.hw_accel_combo.addItem("仅限 CPU (libx264)", "libx264")
        
        idx = self.hw_accel_combo.findData(self.hw_accel)
        if idx >= 0:
            self.hw_accel_combo.setCurrentIndex(idx)
        l_prop_export.addWidget(self.hw_accel_combo)
        
        btn_save_export = QPushButton("保存导出设置")
        btn_save_export.clicked.connect(self.save_export_settings)
        l_prop_export.addWidget(btn_save_export)
        
        l_prop_export.addStretch()
        self.stacked_properties.addWidget(page_prop_export)
        
        # 页面 6: 动态检查器 (Inspector)
        self.page_prop_inspector = QWidget()
        self.l_prop_inspector = QVBoxLayout(self.page_prop_inspector)
        self.l_prop_inspector.setContentsMargins(15, 15, 15, 15)
        self.l_prop_inspector.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.stacked_properties.addWidget(self.page_prop_inspector)
        
        right_layout.addLayout(self.stacked_properties)
        
        # --- 运行日志区域 ---
        right_layout.addSpacing(10)
        right_layout.addWidget(QLabel("<b>运行日志</b>"))
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setStyleSheet("background-color: #0A0A0A; color: #00FF00; font-family: Consolas, monospace; font-size: 11px; border: 1px solid #333;")
        right_layout.addWidget(self.log_output, stretch=1)
        
        upper_splitter.addWidget(right_panel)
        
        upper_splitter.setSizes([350, 700, 300]) # 调整三列比例
        
        # --- 下半部分 (Lower Section - Timeline) ---
        self.timeline_ui = TimelineWidget()
        self.timeline_ui.set_model(self.timeline)
        self.timeline_ui.position_changed.connect(self.media_player.setPosition)
        self.timeline_ui.clip_selected.connect(self.on_clip_selected)
        self.timeline_ui.clip_updated.connect(self.on_clip_updated)
        
        self.update_subtitle_preview_style()
        
        self.media_player.positionChanged.connect(self.sync_timeline_cursor)
        self.media_player.durationChanged.connect(self.duration_changed)
        self.media_player.playbackStateChanged.connect(self.on_playback_state_changed)
        
        self.video_widget.clicked.connect(self.toggle_play_pause)
        self.video_widget.doubleClicked.connect(self.toggle_fullscreen)
        
        main_splitter.addWidget(upper_splitter)
        main_splitter.addWidget(self.timeline_ui)
        main_splitter.setSizes([700, 300]) # 调整上下比例，使下方轨道栏能完整显示5个轨道
        
        root_layout.addWidget(main_splitter)

    def showEvent(self, event):
        super().showEvent(event)
        if not hasattr(self, '_initial_fit_done') and hasattr(self, 'timeline_ui'):
            self._initial_fit_done = True
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(100, lambda: self.timeline_ui.fit_to_screen())

    def log_message(self, msg):
        """将日志输出到文本框和本地文件"""
        self.logger.info(msg)
        # 在文本框中追加（会自动滚动到底部）
        time_str = datetime.datetime.now().strftime('%H:%M:%S')
        self.log_output.append(f"[{time_str}] {msg}")
        
    def create_menus(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("文件 (&F)")
        
        new_action = QAction("新建项目 (&N)", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.new_project)
        file_menu.addAction(new_action)
        
        save_action = QAction("保存项目 (&S)", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_project)
        file_menu.addAction(save_action)
        
        load_action = QAction("加载项目 (&O)", self)
        load_action.setShortcut("Ctrl+O")
        load_action.triggered.connect(self.load_project)
        file_menu.addAction(load_action)

        file_menu.addSeparator()

        exit_action = QAction("退出 (&Q)", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        help_menu = menubar.addMenu("帮助 (&H)")
        about_action = QAction("关于 (&A)", self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)

    def show_about_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("关于 AutoCutVideo")
        dialog.resize(800, 600)
        
        layout = QVBoxLayout(dialog)
        
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setStyleSheet("font-size: 14px; padding: 10px; background-color: #181818; color: #E0E0E0;")
        
        usage_text = """
# AutoCutVideo 简要使用说明

欢迎使用 **AutoCutVideo** - 视频字幕及PDF幻灯片全自动合成工具！

## 🚀 快速入门
1. **导入视频**：在左侧“媒体”面板导入需要处理的主视频。
2. **导入幻灯片 (可选)**：如果需要，在左侧“插图”面板导入配套的 PDF 幻灯片。
3. **配置 API Key**：在界面右侧“设置”面板中，填写您的 Gemini API Key。
4. **生成字幕**：进入左侧“字幕”面板，点击“识别字幕”自动提取并生成精准字幕。
5. **匹配幻灯片**：如导入了 PDF，进入“插图”面板点击相关按钮，AI 将自动分析并将幻灯片匹配到视频对应的时间点。
6. **导出视频**：在左侧“导出”面板配置好相关参数，点击导出，稍等片刻即可获得成品！

## 💡 进阶功能
- **调整字幕**：可在下方时间轴上选中字幕片段，在右侧属性面板修改文字。
- **添加 Logo**：在左侧“Logo”面板添加您的品牌标志，自由拖动调整位置。
- **视频封面**：可导入一张图片作为视频封面，并自定义展示时长。
"""
        text_edit.setMarkdown(usage_text)
        
        layout.addWidget(text_edit)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_close = QPushButton("关闭")
        btn_close.setObjectName("PrimaryBtn")
        btn_close.clicked.connect(dialog.accept)
        btn_close.setFixedWidth(100)
        btn_layout.addWidget(btn_close)
        
        layout.addLayout(btn_layout)
        
        dialog.exec()

    def check_save_before_continue(self):
        # 只要当前有视频导入，就认为是一个可以保存的工作区
        if not hasattr(self, 'video_path') or not self.video_path:
            return True
            
        reply = QMessageBox.question(self, '保存提示', '当前已有打开的工作项目，是否在继续之前保存？\n如果不保存，未保存的修改将会丢失。',
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
                                     QMessageBox.StandardButton.Yes)
                                     
        if reply == QMessageBox.StandardButton.Yes:
            # 返回 True 表示用户已经成功保存或者跳过，可以继续；如果取消保存，可能意味着中断操作
            saved = self.save_project()
            return saved
        elif reply == QMessageBox.StandardButton.Cancel:
            return False
        return True

    def update_last_opened_dir(self, file_path):
        if not file_path: return
        if isinstance(file_path, list):
            if not file_path: return
            file_path = file_path[0]
        directory = os.path.dirname(file_path)
        if directory and directory != self.last_opened_dir:
            self.last_opened_dir = directory
            set_key(ENV_PATH, "LAST_OPENED_DIR", directory)

    def new_project(self):
        if not self.check_save_before_continue():
            return
            
        import subprocess
        import sys
        self.log_message("🔄 正在重新启动程序以创建新项目...")
        
        if getattr(sys, 'frozen', False):
            # 如果是打包后的 exe 环境
            subprocess.Popen([sys.executable] + sys.argv[1:])
        else:
            # 如果是 python 脚本运行环境
            subprocess.Popen([sys.executable] + sys.argv)
            
        QApplication.quit()

    def save_project(self):
        path, _ = QFileDialog.getSaveFileName(self, "保存项目", self.last_opened_dir, "AutoCut Project (*.acproj)")
        if not path:
            return False
        self.update_last_opened_dir(path)
        if not path:
            return False
        data = {
            "video_path": self.video_path,
            "pdf_path": getattr(self, 'slide_source', None),
            "logo_path": getattr(self, 'logo_path', ''),
            "cover_path": getattr(self, 'cover_path', ''),
            "cover_duration": getattr(self, 'cover_duration', 0.5),
            "cover_title": getattr(self, 'cover_title', ''),
            "cover_subtitle": getattr(self, 'cover_subtitle', ''),
            "cover_font": getattr(self, 'cover_font', '微软雅黑(加粗)'),
            "cover_template": getattr(self, 'cover_template', 'classic_white_yellow'),
            "cover_custom_title": getattr(self, 'cover_custom_title', ''),
            "cover_custom_subtitle": getattr(self, 'cover_custom_subtitle', ''),
            "broll_video_path": getattr(self, 'broll_video_path', ''),
            "export_dir": self.export_dir,
            "tmp_dir": self.tmp_dir,
            "srt_path": self.srt_path,
            "timeline": self.timeline.to_dict(),
            "srt_data": self.srt_data,
            "trim_start_s": self.trim_start_s,
            "trim_end_s": self.trim_end_s
        }
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.log_message(f"✅ 项目已成功保存至: {path}")
            QMessageBox.information(self, "成功", "项目保存成功！")
            return True
        except Exception as e:
            self.log_message(f"❌ 项目保存失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"项目保存失败: {str(e)}")
            return False

    def load_project(self):
        if not self.check_save_before_continue():
            return
            
        path, _ = QFileDialog.getOpenFileName(self, "加载项目", self.last_opened_dir, "AutoCut Project (*.acproj)")
        if not path:
            return
        self.update_last_opened_dir(path)
            
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            self.video_path = data.get("video_path", "")
            self.slide_source = data.get("pdf_path", None)
            self.logo_path = data.get("logo_path", "")
            if self.logo_path and os.path.exists(self.logo_path):
                self.lbl_logo.setText(f"当前Logo: {Path(self.logo_path).name}")
            self.cover_path = data.get("cover_path", "")
            if hasattr(self, 'lbl_cover'):
                if self.cover_path and os.path.exists(self.cover_path):
                    self.lbl_cover.setText(f"当前封面: {Path(self.cover_path).name}")
                else:
                    self.lbl_cover.setText("未选择封面")
            self.cover_duration = data.get("cover_duration", 0.5)
            self.cover_title = data.get("cover_title", "")
            self.cover_subtitle = data.get("cover_subtitle", "")
            self.cover_font = data.get("cover_font", "微软雅黑(加粗)")
            self.cover_template = data.get("cover_template", "classic_white_yellow")
            self.cover_custom_title = data.get("cover_custom_title", "")
            self.cover_custom_subtitle = data.get("cover_custom_subtitle", "")
            if hasattr(self, 'spin_cover_duration'):
                self.spin_cover_duration.blockSignals(True)
                self.spin_cover_duration.setValue(self.cover_duration)
                self.spin_cover_duration.blockSignals(False)
            if hasattr(self, 'txt_cover_title'):
                self.txt_cover_title.setText(self.cover_title)
            if hasattr(self, 'txt_cover_subtitle'):
                self.txt_cover_subtitle.setPlainText(self.cover_subtitle)
            if hasattr(self, 'combo_cover_font'):
                self.combo_cover_font.setCurrentText(self.cover_font)
            if hasattr(self, 'combo_cover_template'):
                idx = self.combo_cover_template.findData(self.cover_template)
                if idx >= 0:
                    self.combo_cover_template.setCurrentIndex(idx)
            if hasattr(self, 'txt_cover_custom_t'):
                self.txt_cover_custom_t.setText(self.cover_custom_title)
            if hasattr(self, 'txt_cover_custom_s'):
                self.txt_cover_custom_s.setText(self.cover_custom_subtitle)
            
            self.broll_video_path = data.get("broll_video_path", "")
            if hasattr(self, 'lbl_broll'):
                if self.broll_video_path and os.path.exists(self.broll_video_path):
                    self.lbl_broll.setText(f"辅助视频:\n{Path(self.broll_video_path).name}")
                else:
                    self.lbl_broll.setText("未导入辅助视频")
                    
            self.export_dir = data.get("export_dir", "")
            self.tmp_dir = data.get("tmp_dir", "")
            self.srt_path = data.get("srt_path", "")
            self.srt_data = data.get("srt_data", [])
            self.trim_start_s = data.get("trim_start_s", 0)
            self.trim_end_s = data.get("trim_end_s", 2)
            if hasattr(self, 'spin_trim_start'):
                self.spin_trim_start.setValue(self.trim_start_s)
                self.spin_trim_end.setValue(self.trim_end_s)
            
            # Rebuild Timeline
            if "timeline" in data:
                self.timeline = Timeline.from_dict(data["timeline"])
                # Re-bind the track references
                for t in self.timeline.tracks:
                    if t.track_type == TrackType.VIDEO: self.video_track = t
                    elif t.track_type == TrackType.IMAGE: self.image_track = t
                    elif t.track_type == TrackType.LOGO: self.logo_track = t
                    elif t.track_type == TrackType.SUBTITLE: self.subtitle_track = t
                    elif t.track_type == TrackType.COVER: self.cover_track = t
                    elif t.track_type == TrackType.BROLL: self.broll_track = t
                
                # 兼容旧版本项目，补充可能缺失的轨道
                existing_types = [t.track_type for t in self.timeline.tracks]
                if getattr(TrackType, 'COVER', 'cover') not in existing_types:
                    self.cover_track = Track("视频封面", TrackType.COVER)
                    self.timeline.add_track(self.cover_track)
                if getattr(TrackType, 'BROLL', 'broll') not in existing_types:
                    self.broll_track = Track("辅助画面", TrackType.BROLL)
                    self.timeline.add_track(self.broll_track)
            else:
                self.init_timeline_model()
                
            # Update UI
            if self.video_path and os.path.exists(self.video_path):
                self.lbl_video.setText(f"已导入视频: {os.path.basename(self.video_path)}")
                self.media_player.setSource(QUrl.fromLocalFile(self.video_path))
                
            # Normalize to list to support legacy single string path
            if getattr(self, 'slide_source', None):
                if isinstance(self.slide_source, str):
                    self.slide_source = [self.slide_source]
                self.lbl_pdf.setText(f"已选择 {len(self.slide_source)} 个插图文件")
            else:
                self.slide_source = []
                self.lbl_pdf.setText("已选择 0 个插图文件")
                
            if self.export_dir:
                self.lbl_export_path.setText(f"当前目录: {self.export_dir}")
                
            # Rebuild Timeline UI
            self.timeline_ui.set_model(self.timeline)
            
            self.log_message(f"✅ 项目已成功加载从: {path}")
            QMessageBox.information(self, "成功", "项目加载成功！")
        except Exception as e:
            self.log_message(f"❌ 项目加载失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"项目加载失败: {str(e)}")

    def on_nav_changed(self, index):
        # Deselect clip in timeline when navigating away
        self.timeline_ui.scene.clearSelection()
        self.stacked_properties.setCurrentIndex(index)

    def on_clip_selected(self, clip):
        # 清除检查器旧内容
        while self.l_prop_inspector.count():
            item = self.l_prop_inspector.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if clip is None:
            # 切回原来的导航属性页
            self.stacked_properties.setCurrentIndex(self.stacked_tools.currentIndex())
            return
            
        # 切换到检查器
        self.stacked_properties.setCurrentWidget(self.page_prop_inspector)
        self.current_inspector_clip = clip
        
        self.l_prop_inspector.addWidget(QLabel(f"<b>选中片段属性: {clip.name}</b>"))
        
        from timeline_model import TrackType
        
        # 共有属性：起止时间
        self.l_prop_inspector.addWidget(QLabel("起始时间 (毫秒):"))
        self.insp_start_spin = QSpinBox()
        self.insp_start_spin.setRange(0, 86400000)
        self.insp_start_spin.setValue(clip.start_time)
        self.l_prop_inspector.addWidget(self.insp_start_spin)
        
        self.l_prop_inspector.addWidget(QLabel("片段时长 (毫秒):"))
        self.insp_dur_spin = QSpinBox()
        self.insp_dur_spin.setRange(10, 86400000)
        self.insp_dur_spin.setValue(clip.duration)
        self.l_prop_inspector.addWidget(self.insp_dur_spin)
        
        # 按类型定制的属性
        if clip.clip_type == TrackType.SUBTITLE:
            self.l_prop_inspector.addWidget(QLabel("字幕文本:"))
            self.insp_text = QTextEdit()
            self.insp_text.setPlainText(clip.source_path) # subtitle text is stored in source_path
            self.l_prop_inspector.addWidget(self.insp_text)
            
        elif clip.clip_type == TrackType.LOGO:
            self.l_prop_inspector.addWidget(QLabel("距右侧边缘距离 (px):"))
            self.insp_logo_x = QSpinBox()
            self.insp_logo_x.setRange(0, 9999)
            
            x_val = clip.meta.get("x", 0)
            try: x_val = int(x_val)
            except: x_val = 0
            self.insp_logo_x.setValue(x_val)
            self.l_prop_inspector.addWidget(self.insp_logo_x)
            
            self.l_prop_inspector.addWidget(QLabel("距底部边缘距离 (px):"))
            self.insp_logo_y = QSpinBox()
            self.insp_logo_y.setRange(0, 9999)
            
            y_val = clip.meta.get("y", 0)
            try: y_val = int(y_val)
            except: y_val = 0
            self.insp_logo_y.setValue(y_val)
            self.l_prop_inspector.addWidget(self.insp_logo_y)
            
            self.l_prop_inspector.addWidget(QLabel("缩放比例 (%):"))
            self.insp_logo_scale = QSpinBox()
            self.insp_logo_scale.setRange(1, 1000)
            scale_val = clip.meta.get("scale", 100)
            try: scale_val = int(scale_val)
            except: scale_val = 100
            self.insp_logo_scale.setValue(scale_val)
            self.l_prop_inspector.addWidget(self.insp_logo_scale)
            
        else:
            self.l_prop_inspector.addWidget(QLabel("当前类型的片段暂无特殊属性可编辑。"))
            
        btn_save = QPushButton("保存修改")
        btn_save.setObjectName("PrimaryBtn")
        btn_save.clicked.connect(self.save_inspector_changes)
        self.l_prop_inspector.addWidget(btn_save)
        self.l_prop_inspector.addStretch()
        
    def save_inspector_changes(self):
        clip = getattr(self, "current_inspector_clip", None)
        if not clip: return
        
        from timeline_model import TrackType
        clip.start_time = self.insp_start_spin.value()
        clip.duration = self.insp_dur_spin.value()
        
        if clip.clip_type == TrackType.SUBTITLE:
            clip.source_path = self.insp_text.toPlainText()
        elif clip.clip_type == TrackType.LOGO:
            clip.meta["x"] = self.insp_logo_x.value()
            clip.meta["y"] = self.insp_logo_y.value()
            clip.meta["scale"] = self.insp_logo_scale.value()
            
            # 持久化保存到全局环境，方便下次添加时直接使用
            from dotenv import set_key
            set_key(ENV_PATH, "LOGO_X", str(self.insp_logo_x.value()))
            set_key(ENV_PATH, "LOGO_Y", str(self.insp_logo_y.value()))
            set_key(ENV_PATH, "LOGO_SCALE", str(self.insp_logo_scale.value()))
            
        self.timeline_ui.save_state()
        self.timeline_ui.rebuild_from_model()
        # 保持选中状态
        for item in self.timeline_ui.scene.clip_items:
            if item.clip.id == clip.id:
                item.setSelected(True)
                break
                
        # 立即强制刷新预览画面
        self.sync_timeline_cursor(self.media_player.position())

    def on_clip_updated(self, clip):
        if clip.clip_type == TrackType.COVER:
            self.cover_duration = clip.duration / 1000.0
            if hasattr(self, 'spin_cover_duration'):
                self.spin_cover_duration.blockSignals(True)
                self.spin_cover_duration.setValue(self.cover_duration)
                self.spin_cover_duration.blockSignals(False)
        # 当在时间轴直接拖动片段边缘导致变化时，如果当前正好选中它，则同步右侧 UI
        if getattr(self, "current_inspector_clip", None) and self.current_inspector_clip.id == clip.id:
            if hasattr(self, "insp_start_spin"):
                self.insp_start_spin.setValue(clip.start_time)
            if hasattr(self, "insp_dur_spin"):
                self.insp_dur_spin.setValue(clip.duration)

    def save_model_settings(self):
        raw_keys = self.api_key_input.toPlainText()
        self.api_key = raw_keys.replace('"', '').replace("'", "").replace("\n", ",").replace(" ", "")
        self.selected_model = self.model_combo.currentText()
        set_key(ENV_PATH, "GEMINI_API_KEY", self.api_key)
        set_key(ENV_PATH, "GEMINI_MODEL", self.selected_model)
        QMessageBox.information(self, "提示", "API配置已保存！")

    def save_text_settings(self):
        self.audio_bitrate = self.bitrate_combo.currentText()
        self.subtitle_lang = self.lang_combo.currentText()
        self.max_chars = str(self.max_chars_spin.value())
        self.selected_template_key = self.template_combo.currentData()
        self.whisper_model = self.whisper_combo.currentText()
        set_key(ENV_PATH, "WHISPER_MODEL", self.whisper_model)
        set_key(ENV_PATH, "GEMINI_AUDIO_BITRATE", self.audio_bitrate)
        set_key(ENV_PATH, "GEMINI_SUBTITLE_LANG", self.subtitle_lang)
        set_key(ENV_PATH, "GEMINI_MAX_CHARS", self.max_chars)
        set_key(ENV_PATH, "GEMINI_TEMPLATE_KEY", self.selected_template_key)
        
        self.subtitle_margin_bottom = self.margin_spin.value()
        set_key(ENV_PATH, "GEMINI_SUBTITLE_MARGIN", str(self.subtitle_margin_bottom))
        
        self.update_subtitle_preview_style()
        self.sync_timeline_cursor(self.media_player.position())
        
        QMessageBox.information(self, "提示", "字幕与音频设置已保存！")
        
    def save_pip_settings(self):
        self.min_slide_duration = self.min_dur_spin.value() * 1000
        self.max_slide_duration = self.max_dur_spin.value() * 1000
        set_key(ENV_PATH, "MIN_SLIDE_DURATION", str(self.min_slide_duration))
        set_key(ENV_PATH, "MAX_SLIDE_DURATION", str(self.max_slide_duration))
        QMessageBox.information(self, "提示", "插图设置已保存！")

    def save_logo_settings(self):
        self.logo_x = self.spin_global_logo_x.value()
        self.logo_y = self.spin_global_logo_y.value()
        self.logo_scale = self.spin_global_logo_scale.value()
        
        set_key(ENV_PATH, "LOGO_X", str(self.logo_x))
        set_key(ENV_PATH, "LOGO_Y", str(self.logo_y))
        set_key(ENV_PATH, "LOGO_SCALE", str(self.logo_scale))
        
        # 应用到已存在的时间轴片段
        updated = False
        from timeline_model import TrackType
        if hasattr(self, 'logo_track'):
            for clip in self.logo_track.clips:
                clip.meta["x"] = self.logo_x
                clip.meta["y"] = self.logo_y
                clip.meta["scale"] = self.logo_scale
                updated = True
        
        if updated and self.timeline_ui:
            self.timeline_ui.update()
            QMessageBox.information(self, "提示", "Logo设置已保存，并且已同步应用到轨道上的Logo片段！")
        else:
            QMessageBox.information(self, "提示", "Logo设置已保存，下次添加Logo时将自动生效！")

    def save_cover_settings(self):
        self.cover_duration = self.spin_cover_duration.value()
        self.cover_title = self.txt_cover_title.text()
        self.cover_subtitle = self.txt_cover_subtitle.toPlainText()
        self.cover_font = self.combo_cover_font.currentText()
        self.cover_template = self.combo_cover_template.currentData()
        self.cover_custom_title = self.txt_cover_custom_t.text()
        self.cover_custom_subtitle = self.txt_cover_custom_s.text()
        self.cover_title_y = self.spin_cover_title_y.value()
        self.cover_spacing = self.spin_cover_spacing.value()
        self.cover_title_scale = self.spin_cover_title_scale.value()
        self.cover_subtitle_scale = self.spin_cover_subtitle_scale.value()
        set_key(ENV_PATH, "COVER_DURATION", str(self.cover_duration))
        set_key(ENV_PATH, "COVER_TITLE", self.cover_title)
        set_key(ENV_PATH, "COVER_SUBTITLE", self.cover_subtitle)
        set_key(ENV_PATH, "COVER_FONT", self.cover_font)
        set_key(ENV_PATH, "COVER_TEMPLATE", self.cover_template)
        set_key(ENV_PATH, "COVER_CUSTOM_TITLE", self.cover_custom_title)
        set_key(ENV_PATH, "COVER_CUSTOM_SUBTITLE", self.cover_custom_subtitle)
        set_key(ENV_PATH, "COVER_TITLE_Y", str(self.cover_title_y))
        set_key(ENV_PATH, "COVER_SPACING", str(self.cover_spacing))
        set_key(ENV_PATH, "COVER_TITLE_SCALE", str(self.cover_title_scale))
        set_key(ENV_PATH, "COVER_SUBTITLE_SCALE", str(self.cover_subtitle_scale))
        QMessageBox.information(self, "提示", "封面设置已保存！")
        
    def preview_cover(self, orientation=None):
        # Gathering current inputs directly
        cover_path = getattr(self, 'cover_path', '')
        if not cover_path or not os.path.exists(cover_path):
            QMessageBox.warning(self, "提示", "请先在上方上传封面图片才能预览！")
            return
            
        c_title = self.txt_cover_title.text()
        c_subtitle = self.txt_cover_subtitle.toPlainText()
        c_font = self.combo_cover_font.currentText()
        c_template = self.combo_cover_template.currentData()
        c_custom_t = self.txt_cover_custom_t.text()
        c_custom_s = self.txt_cover_custom_s.text()
        c_title_y = self.spin_cover_title_y.value()
        c_spacing = self.spin_cover_spacing.value()
        c_t_scale = self.spin_cover_title_scale.value()
        c_s_scale = self.spin_cover_subtitle_scale.value()
        
        tmp_d = self.get_tmp_dir()
        preview_jpg = os.path.join(tmp_d, "preview.jpg")
        
        self.log_message("⏳ 正在极速生成封面预览...")
        # Save so that UI state is not completely lost, but without popup
        success = generate_cover_preview(
            cover_path=cover_path,
            output_jpg_path=preview_jpg,
            tmp_dir=tmp_d,
            video_path=self.video_path,
            cover_title=c_title,
            cover_subtitle=c_subtitle,
            cover_font=c_font,
            cover_template=c_template,
            cover_custom_title=c_custom_t,
            cover_custom_subtitle=c_custom_s,
            cover_title_y=c_title_y,
            cover_spacing=c_spacing,
            cover_title_scale=c_t_scale,
            cover_subtitle_scale=c_s_scale,
            orientation=orientation
        )
        
        if success and os.path.exists(preview_jpg):
            self.log_message("✅ 预览生成完毕！")
            dlg = QDialog(self)
            dlg.setWindowTitle("封面实时预览")
            layout = QVBoxLayout(dlg)
            layout.setContentsMargins(0, 0, 0, 0)
            lbl = QLabel()
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(lbl)
            
            pixmap = QPixmap(preview_jpg)
            
            # 动态适应横竖屏
            if pixmap.width() > pixmap.height():
                dlg.resize(1280, 720)
            else:
                dlg.resize(540, 960)
            
            def resizeEvent(event):
                lbl.setPixmap(pixmap.scaled(dlg.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                QDialog.resizeEvent(dlg, event)
            dlg.resizeEvent = resizeEvent
            
            # Initial scale
            lbl.setPixmap(pixmap.scaled(dlg.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            dlg.exec()
        else:
            QMessageBox.warning(self, "错误", "预览生成失败，请查看日志！")

    def open_standalone_cover_generator(self):
        try:
            candidates = [
                os.path.join(application_path, "cover_generator", "cover_generator.py"),
                os.path.join(application_path, "cover_generator", "main.py"),
                os.path.join(application_path, "cover_generator.py"),
                os.path.join(application_path, "cover_generator", "cover_generator.exe"),
                os.path.join(application_path, "cover_generator.exe"),
            ]
            for target in candidates:
                if os.path.exists(target):
                    if target.endswith(".py"):
                        subprocess.Popen([sys.executable, target])
                    else:
                        subprocess.Popen([target])
                    return
            QMessageBox.warning(self, "提示", "未找到封面生成器脚本或程序！")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法启动封面生成器: {e}")
        
    def save_broll_settings(self):
        self.broll_transition = self.broll_trans_combo.currentData()
        self.broll_min_duration = self.spin_broll_min.value()
        self.broll_max_duration = self.spin_broll_max.value()
        
        set_key(ENV_PATH, "BROLL_TRANSITION", self.broll_transition)
        set_key(ENV_PATH, "BROLL_MIN_DURATION", str(self.broll_min_duration))
        set_key(ENV_PATH, "BROLL_MAX_DURATION", str(self.broll_max_duration))
        QMessageBox.information(self, "提示", "混剪设置已保存！")

    def save_export_settings(self):
        self.trim_start_s = self.spin_trim_start.value()
        self.trim_end_s = self.spin_trim_end.value()
        self.hw_accel = self.hw_accel_combo.currentData()
        
        set_key(ENV_PATH, "TRIM_START", str(self.trim_start_s))
        set_key(ENV_PATH, "TRIM_END", str(self.trim_end_s))
        set_key(ENV_PATH, "HW_ACCEL", self.hw_accel)
        
        self.log_message(f"✅ 已保存导出设置 (掐头: {self.trim_start_s}s, 去尾: {self.trim_end_s}s, 加速: {self.hw_accel})")
        QMessageBox.information(self, "提示", "导出与裁剪设置已保存！")

    def show_progress(self, show=True):
        if show:
            self.progress_bar.show()
            if hasattr(self, 'btn_stop_pipeline'):
                self.btn_stop_pipeline.show()
        else:
            self.progress_bar.hide()
            if hasattr(self, 'btn_stop_pipeline'):
                self.btn_stop_pipeline.hide()
            
    def get_tmp_dir(self):
        base_dir = self.export_dir if self.export_dir else (os.path.dirname(self.video_path) if self.video_path else os.getcwd())
        tmp_dir = os.path.join(base_dir, "tmp_autocut")
        os.makedirs(tmp_dir, exist_ok=True)
        return tmp_dir

    def format_time(self, ms):
        s = ms // 1000
        m = s // 60
        h = m // 60
        return f"{h:02d}:{m%60:02d}:{s%60:02d}"

    # ==========================
    # 视频与播放器逻辑
    # ==========================
    def toggle_play_pause(self):
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.media_player.pause()
        else:
            self.media_player.play()

    def on_playback_state_changed(self, state):
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.btn_play.setText("⏸")
        else:
            self.btn_play.setText("▶")

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
            self.left_panel.show()
            self.right_panel.show()
            self.timeline_ui.show()
            self.menuBar().show()
        else:
            self.left_panel.hide()
            self.right_panel.hide()
            self.timeline_ui.hide()
            self.menuBar().hide()
            self.showFullScreen()

    def import_video(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "选择基座视频", self.last_opened_dir, "Video Files (*.mp4 *.mkv *.avi *.mov)")
        if file_name:
            self.update_last_opened_dir(file_name)
            self.video_path = file_name
            self.lbl_video.setText(f"基座视频:\n{Path(file_name).name}")
            self.media_player.setSource(QUrl.fromLocalFile(file_name))
            
            self.video_track.clips = []
            
            # 尝试通过 moviepy 同步获取真实的视频时长，避免等待 QMediaPlayer 异步回调缓慢或失败导致的时间轴错误
            real_duration_ms = 60000
            try:
                from moviepy.editor import VideoFileClip
                vc = VideoFileClip(file_name)
                if vc.duration and vc.duration > 0:
                    real_duration_ms = int(vc.duration * 1000)
                vc.close()
            except Exception as e:
                self.log_message(f"⚠️ 无法同步获取视频时长，将使用默认值。({e})")
            
            v_clip = Clip(Path(file_name).name, file_name, 0, real_duration_ms, TrackType.VIDEO)
            self.video_track.add_clip(v_clip)
            self.timeline_ui.rebuild_from_model()
            self.timeline_ui.fit_to_screen(real_duration_ms)
            
            if not getattr(self, 'export_dir', None):
                self.export_dir = os.path.dirname(self.video_path)

    def import_broll_video(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "选择辅助视频 (B-Roll)", self.last_opened_dir, "Video Files (*.mp4 *.mkv *.avi *.mov)")
        if file_name:
            self.update_last_opened_dir(file_name)
            self.broll_video_path = file_name
            self.lbl_broll.setText(f"辅助视频:\n{Path(file_name).name}")

    def duration_changed(self, duration_ms):
        # 修正视频剪辑轨道的实际时长，如果播放器回调 0 意味着尚未加载完毕，则跳过
        if duration_ms > 0:
            if self.video_track.clips:
                self.video_track.clips[0].duration = duration_ms
                self.timeline_ui.rebuild_from_model()
                self.timeline_ui.fit_to_screen(duration_ms)
                
            self.lbl_timecode.setText(f"00:00:00 / {self.format_time(duration_ms)}")

    def on_video_resized(self, w, h):
        pos = self.media_player.position()
        self.sync_timeline_cursor(pos)

    def sync_timeline_cursor(self, ms):
        self.timeline_ui.set_position(ms)
        duration = self.media_player.duration()
        
        new_timecode = f"{self.format_time(ms)} / {self.format_time(duration)}"
        if self.lbl_timecode.text() != new_timecode:
            self.lbl_timecode.setText(new_timecode)
        
        size = self.video_widget.size()
        w = size.width()
        h = size.height()
        native_size = self.video_widget.video_item.nativeSize()
        video_w, video_h = float(w), float(h)
        x_offset = 0.0
        y_offset = 0.0
        scale = 1.0
        if not native_size.isEmpty():
            nw = native_size.width()
            nh = native_size.height()
            if nw > 0 and nh > 0:
                scale = min(w / nw, h / nh)
                video_w = nw * scale
                video_h = nh * scale
                x_offset = (w - video_w) / 2
                y_offset = (h - video_h) / 2
        
        current_text = ""
        for clip in self.subtitle_track.clips:
            if clip.start_time <= ms <= clip.start_time + clip.duration:
                current_text = clip.source_path 
                break
                
        if current_text != getattr(self, '_current_preview_text', None):
            self._current_preview_text = current_text
            if current_text:
                self.lbl_subtitle_preview.setText(current_text)
                self.lbl_subtitle_preview.adjustSize()
                
                # 更新坐标使其居中靠底
                lbl_w = self.lbl_subtitle_preview.width()
                lbl_h = self.lbl_subtitle_preview.height()
                scaled_margin = self.subtitle_margin_bottom * scale
                self.subtitle_proxy.setPos(x_offset + (video_w - lbl_w) / 2, y_offset + video_h - lbl_h - scaled_margin)
                
                self.lbl_subtitle_preview.show()
            else:
                self.lbl_subtitle_preview.hide()
        
        # 同步封面与幻灯片预览
        current_img = None
        is_cover = False
        if hasattr(self, 'cover_track'):
            for clip in self.cover_track.clips:
                if clip.start_time <= ms <= clip.start_time + clip.duration:
                    current_img = clip.source_path
                    is_cover = True
                    break
        if not current_img:
            for clip in self.image_track.clips:
                if clip.start_time <= ms <= clip.start_time + clip.duration:
                    current_img = clip.source_path
                    break
                
        img_state = (current_img, size.width(), size.height(), is_cover)
        
        if img_state != getattr(self, '_current_preview_image_state', None):
            self._current_preview_image_state = img_state
            if current_img and os.path.exists(current_img):
                pixmap = QPixmap(current_img)
                if is_cover:
                    # 视频封面的比例预览时和视频保持一致的展示方式 (Fit)
                    scaled_pixmap = pixmap.scaled(size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    self.image_preview_label.setPixmap(scaled_pixmap)
                else:
                    # 幻灯片适应屏幕 (Fit)
                    scaled_pixmap = pixmap.scaled(size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    self.image_preview_label.setPixmap(scaled_pixmap)
                    
                self.image_preview_label.resize(size)
                self.image_preview_label.show()
            else:
                self.image_preview_label.hide()
            
        # 同步 Logo 预览
        current_logo = None
        for clip in self.logo_track.clips:
            if clip.start_time <= ms <= clip.start_time + clip.duration:
                current_logo = clip
                break
                
        logo_path = current_logo.source_path if current_logo else None
        logo_x = current_logo.meta.get("x") if current_logo else None
        logo_y = current_logo.meta.get("y") if current_logo else None
        logo_scale = current_logo.meta.get("scale", 100) if current_logo else 100
        
        logo_state = (logo_path, logo_x, logo_y, logo_scale, size.width(), size.height())
        
        if logo_state != getattr(self, '_current_preview_logo_state', None):
            self._current_preview_logo_state = logo_state
            if current_logo and os.path.exists(logo_path):
                logo_suffix = Path(logo_path).suffix.lower()
                if logo_suffix in (".mp4", ".mov", ".webm", ".avi", ".mkv"):
                    pixmap = QPixmap()
                    try:
                        import cv2
                        cap = cv2.VideoCapture(logo_path)
                        ret, frame = cap.read()
                        cap.release()
                        if ret:
                            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                            h, w, ch = frame.shape
                            bytes_per_line = ch * w
                            qimg = QImage(frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
                            pixmap = QPixmap.fromImage(qimg)
                    except:
                        pass
                else:
                    pixmap = QPixmap(logo_path)
                
                try: scale_val = int(logo_scale)
                except: scale_val = 100
                
                total_scale_factor = (float(scale_val) / 100.0) * scale
                if total_scale_factor != 1.0:
                    new_w = max(1, int(pixmap.width() * total_scale_factor))
                    new_h = max(1, int(pixmap.height() * total_scale_factor))
                    pixmap = pixmap.scaled(new_w, new_h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    
                self.logo_preview_label.setPixmap(pixmap)
                self.logo_preview_label.resize(pixmap.size())
                
                # 距右边距和底边距
                try: x_val = int(logo_x)
                except: x_val = 0
                try: y_val = int(logo_y)
                except: y_val = 0
                
                w_logo = pixmap.width()
                h_logo = pixmap.height()
                
                # 计算坐标：以视频画面右下角为 0 坐标点
                final_x = x_offset + max(0, video_w - w_logo - x_val * scale)
                final_y = y_offset + max(0, video_h - h_logo - y_val * scale)
                    
                self.logo_proxy.resize(w_logo, h_logo)
                self.logo_proxy.setPos(final_x, final_y)
                self.logo_preview_label.show()
            else:
                self.logo_preview_label.hide()

    def update_subtitle_preview_style(self):
        style_str = SUBTITLE_TEMPLATES.get(self.selected_template_key, SUBTITLE_TEMPLATES["default"])["style"]
        
        css_props = {
            "font-size": "28px",
            "font-family": "SimHei",
            "color": "white",
            "background-color": "rgba(0,0,0,150)",
            "padding": "5px 15px",
            "border-radius": "8px",
            "font-weight": "bold"
        }
        
        if style_str:
            pairs = style_str.split(',')
            for p in pairs:
                if '=' not in p: continue
                k, v = p.split('=', 1)
                k = k.strip()
                v = v.strip()
                if k == 'FontName':
                    css_props["font-family"] = f"'{v}', sans-serif"
                elif k == 'FontSize':
                    css_props["font-size"] = f"{v}px"
                elif k == 'PrimaryColour':
                    if v.startswith('&H') and len(v) >= 10:
                        b = v[4:6]
                        g = v[6:8]
                        r = v[8:10]
                        css_props["color"] = f"#{r}{g}{b}"
                elif k == 'Bold':
                    if v == '1' or v == '-1':
                        css_props["font-weight"] = "bold"
                    else:
                        css_props["font-weight"] = "normal"
                        
        css_str = "".join([f"{k}: {v}; " for k, v in css_props.items()])
        self.lbl_subtitle_preview.setStyleSheet(css_str)

    # ==========================
    # 字幕生成与一键全自动
    # ==========================
    def stop_all_tasks(self):
        self.log_message("🛑 正在紧急终止所有任务并清理进程...")
        self.auto_pipeline_running = False
        
        # 终止所有后台 QThread
        workers = ['worker_sub', 'worker_slide', 'worker_broll', 'worker_render', 'worker_retry_ai']
        for w_name in workers:
            if hasattr(self, w_name):
                worker = getattr(self, w_name)
                if worker and worker.isRunning():
                    worker.terminate()
                    worker.wait()
                    
        # 强制杀掉底层渲染进程 (如 ffmpeg)
        import platform
        if platform.system() == "Windows":
            os.system("taskkill /f /im ffmpeg.exe >nul 2>&1")
            
        self.show_progress(False)
        self.btn_export.setText("📦 多格式打包导出...")
        self.btn_export.setEnabled(True)
        self.btn_auto_export.setText("⚡ 一键全自动导出视频")
        self.btn_auto_export.setEnabled(True)
        self.log_message("⛔ 任务已被手动强制终止。")

    def start_auto_pipeline(self):
        if not hasattr(self, 'video_path') or not self.video_path:
            QMessageBox.warning(self, "警告", "请先导入主视频！")
            return
        if not getattr(self, 'slide_source', None):
            QMessageBox.warning(self, "警告", "请先导入配套的 PDF 幻灯片！")
            return
        if not self.api_key_input.toPlainText().strip():
            QMessageBox.warning(self, "警告", "请先填写 API Key！")
            return
            
        msg = "将依次自动执行：\n1. 识别字幕\n2. AI幻灯片匹配"
        if hasattr(self, 'broll_video_path') and self.broll_video_path:
            msg += "\n3. 动态辅助视频提取 (B-Roll)\n4. 导出最终视频"
        else:
            msg += "\n3. 导出最终视频"
        msg += "\n\n请确保各项设置已就绪，是否开始？"
            
        reply = QMessageBox.question(self, "一键全自动导出", msg,
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.auto_pipeline_running = True
            self.btn_auto_export.setEnabled(False)
            self.btn_auto_export.setText("自动流程运行中...")
            
            if not self.subtitle_track.clips:
                self.auto_pipeline_step = 1
                self.log_message("⚡ [一键全自动] 开始第一步：识别字幕")
                self.start_subtitle_gen()
            else:
                self.log_message("⚡ [一键全自动] 检测到已有字幕记录，自动跳过识别。")
                self.auto_pipeline_step = 1
                self.on_subtitle_gen_finished(True, None)

    def start_subtitle_gen(self):
        # 强制更新最新的配置，防止用户忘记点击保存
        raw_keys = self.api_key_input.toPlainText()
        self.api_key = raw_keys.replace('"', '').replace("'", "").replace("\n", ",").replace(" ", "")
        self.selected_model = self.model_combo.currentText()
        self.whisper_model = self.whisper_combo.currentText()
        
        if not self.video_path or not self.api_key:
            QMessageBox.warning(self, "警告", "请先导入视频并填写API Key")
            return
            
        self.log_message("🎙️ 正在提取音频并生成字幕...")
        self.show_progress(True)
        self.worker_sub = ProcessWorker(
            self.video_path, self.api_key, self.base_url, self.whisper_model, self.selected_model,
            self.export_dir, self.audio_bitrate, self.subtitle_lang, self.max_chars, self.get_tmp_dir()
        )
        self.worker_sub.progress_signal.connect(self.log_message)
        self.worker_sub.srt_parsed_signal.connect(self.on_srt_parsed)
        self.worker_sub.finished_signal.connect(self.on_subtitle_gen_finished)
        self.worker_sub.start()

    def on_subtitle_gen_finished(self, success, temp_srt):
        self.show_progress(False)
        if success and getattr(self, 'auto_pipeline_running', False) and self.auto_pipeline_step == 1:
            if getattr(self, 'slide_source', None) and not self.image_track.clips:
                self.auto_pipeline_step = 2
                self.log_message("⚡ [一键全自动] 开始第二步：AI 幻灯片匹配")
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(1000, self.start_slide_process)
            elif getattr(self, 'slide_source', None) and self.image_track.clips:
                self.log_message("⚡ [一键全自动] 检测到已有插图记录，自动跳过匹配。")
                self.auto_pipeline_step = 2
                self.on_slide_finished(True, self.image_track.clips)
            else:
                self.log_message("⚡ [一键全自动] 未导入插图/PDF，跳过第二步。")
                self.auto_pipeline_step = 2
                self.on_slide_finished(True, [])
        elif not success and getattr(self, 'auto_pipeline_running', False):
            self.log_message("❌ [一键全自动] 识别字幕失败，自动流程终止。")
            self.auto_pipeline_running = False
            self.btn_auto_export.setEnabled(True)
            self.btn_auto_export.setText("⚡ 一键全自动导出视频")

    def retry_ai_correction(self):
        # 强制更新最新的配置
        raw_keys = self.api_key_input.toPlainText()
        self.api_key = raw_keys.replace('"', '').replace("'", "").replace("\n", ",").replace(" ", "")
        self.selected_model = self.model_combo.currentText()
        
        if not self.api_key:
            QMessageBox.warning(self, "警告", "请先填写API Key")
            return
            
        # 查找最新的 local_srt
        import glob
        import os
        sub_dir = os.path.join(self.get_tmp_dir(), "subtitles")
        local_srts = glob.glob(os.path.join(sub_dir, "*_local.srt"))
        
        if not local_srts:
            QMessageBox.warning(self, "警告", "未找到本地识别的字幕记录，请先点击【识别字幕】提取一次！")
            return
            
        # 取最新的那一个 local.srt
        latest_local_srt = max(local_srts, key=os.path.getctime)
        
        self.log_message(f"🔄 正在重新提交AI校对，基于: {os.path.basename(latest_local_srt)}")
        self.show_progress(True)
        
        self.worker_retry_ai = RetryAIWorker(
            latest_local_srt, self.api_key, self.base_url, self.selected_model, self.get_tmp_dir()
        )
        self.worker_retry_ai.progress_signal.connect(self.log_message)
        self.worker_retry_ai.srt_parsed_signal.connect(self.on_srt_parsed)
        self.worker_retry_ai.finished_signal.connect(lambda s, f: self.show_progress(False))
        self.worker_retry_ai.start()

    def on_srt_parsed(self, parsed_data):
        self.srt_data = parsed_data
        self.subtitle_track.clips = []
        for sub in parsed_data:
            c = Clip("文本", sub['text'], sub['start'], sub['end'] - sub['start'], TrackType.SUBTITLE)
            self.subtitle_track.add_clip(c)
        self.timeline_ui.save_state()
        self.timeline_ui.rebuild_from_model()
        self.log_message(f"✅ 成功生成/导入了 {len(parsed_data)} 句字幕。")
        if not getattr(self, 'auto_pipeline_running', False):
            QMessageBox.information(self, "成功", f"成功应用了 {len(parsed_data)} 句字幕。")

    def import_external_subtitle(self):
        path, _ = QFileDialog.getOpenFileName(self, "导入字幕", self.last_opened_dir, "SRT Files (*.srt)")
        if not path:
            return
        self.update_last_opened_dir(path)
            
        try:
            parsed_data = []
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            blocks = content.strip().split('\n\n')
            for block in blocks:
                lines = [l for l in block.split('\n') if l.strip()]
                if len(lines) >= 2:
                    time_idx = -1
                    for i, l in enumerate(lines):
                        if '-->' in l:
                            time_idx = i
                            break
                    if time_idx != -1:
                        time_line = lines[time_idx]
                        text = '\n'.join(lines[time_idx+1:])
                        start_str, end_str = time_line.split('-->')
                        def time_to_ms(ts):
                            try:
                                ts = ts.strip().replace(',', '.')
                                h, m, s = ts.split(':')
                                s, ms = s.split('.')
                                return int(h)*3600000 + int(m)*60000 + int(s)*1000 + int(ms)
                            except:
                                return 0
                        parsed_data.append({'start': time_to_ms(start_str), 'end': time_to_ms(end_str), 'text': text})
            
            if parsed_data:
                self.on_srt_parsed(parsed_data)
            else:
                self.log_message("⚠️ 导入失败：未能从文件中解析出有效的字幕块")
                
        except Exception as e:
            self.log_message(f"❌ 导入字幕失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"读取字幕文件时出错:\n{str(e)}")

    # ==========================
    # PPT 处理
    # ==========================
    def add_pdf(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "选择PDF", self.last_opened_dir, "PDF Files (*.pdf)"
        )
        if paths:
            self.update_last_opened_dir(paths)
            if getattr(self, 'slide_source', None) is None or not isinstance(self.slide_source, list):
                self.slide_source = []
            self.slide_source.extend(paths)
            self.lbl_pdf.setText(f"已选择 {len(self.slide_source)} 个插图文件")

    def add_ppt(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "选择PPT", self.last_opened_dir, "PowerPoint Files (*.pptx *.ppt)"
        )
        if paths:
            self.update_last_opened_dir(paths)
            if getattr(self, 'slide_source', None) is None or not isinstance(self.slide_source, list):
                self.slide_source = []
            self.slide_source.extend(paths)
            self.lbl_pdf.setText(f"已选择 {len(self.slide_source)} 个插图文件")

    def add_images(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "选择图片", self.last_opened_dir, "Images (*.jpg *.jpeg *.png *.bmp)"
        )
        if paths:
            self.update_last_opened_dir(paths)
            if getattr(self, 'slide_source', None) is None or not isinstance(self.slide_source, list):
                self.slide_source = []
            valid_images = [p for p in paths if p.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp'))]
            self.slide_source.extend(sorted(valid_images))
            self.lbl_pdf.setText(f"已选择 {len(self.slide_source)} 个插图文件")

    def clear_slides(self):
        self.slide_source = []
        self.lbl_pdf.setText("已选择 0 个插图文件")

    def start_slide_process(self):
        if not getattr(self, 'slide_source', None) or not self.srt_data:
            QMessageBox.warning(self, "警告", "请先选择 PDF或图片并提取字幕！")
            return
            
        self.log_message("🪄 开始解析 PDF 并智能匹配时间轴...")
        self.show_progress(True)
        image_dir = os.path.join(self.get_tmp_dir(), "slides")
        os.makedirs(image_dir, exist_ok=True)
        
        self.worker_slide = SlideProcessWorker(
            self.slide_source, self.srt_data, self.api_key, self.base_url, self.selected_model,
            image_dir, 1000, self.get_tmp_dir(), self.min_slide_duration, self.max_slide_duration
        )
        self.worker_slide.progress_signal.connect(self.log_message)
        self.worker_slide.finished_signal.connect(self.on_slide_finished)
        self.worker_slide.start()
        
    def on_slide_finished(self, success, clips):
        self.show_progress(False)
        if success:
            self.image_track.clips = []
            for c in clips:
                self.image_track.add_clip(c)
            self.timeline_ui.rebuild_from_model()
            self.log_message(f"✅ 成功生成了 {len(clips)} 个幻灯片。")
            if not getattr(self, 'auto_pipeline_running', False):
                QMessageBox.information(self, "成功", f"生成了 {len(clips)} 个幻灯片。")
                
        if getattr(self, 'auto_pipeline_running', False) and self.auto_pipeline_step == 2:
            if success:
                if hasattr(self, 'broll_video_path') and self.broll_video_path and not self.broll_track.clips:
                    self.auto_pipeline_step = 3
                    self.log_message("⚡ [一键全自动] 开始第三步：提取辅助视频 (B-Roll)")
                    from PyQt6.QtCore import QTimer
                    QTimer.singleShot(1000, self.start_broll_process)
                elif hasattr(self, 'broll_video_path') and self.broll_video_path and self.broll_track.clips:
                    self.log_message("⚡ [一键全自动] 检测到已有辅助画面记录，自动跳过提取。")
                    self.auto_pipeline_step = 3
                    self.on_broll_finished(True, self.broll_track.clips)
                else:
                    self.auto_pipeline_step = 4
                    self.log_message("⚡ [一键全自动] 跳过 B-Roll 步骤，开始导出视频")
                    from PyQt6.QtCore import QTimer
                    QTimer.singleShot(1000, self.render_timeline)
            else:
                self.log_message("❌ [一键全自动] 幻灯片匹配失败，自动流程终止。")
                self.auto_pipeline_running = False
                self.btn_auto_export.setEnabled(True)
                self.btn_auto_export.setText("⚡ 一键全自动导出视频")

    # ==========================
    # 辅助视频 (B-Roll) 处理
    # ==========================
    def start_broll_process(self):
        if not hasattr(self, 'broll_video_path') or not self.broll_video_path or not hasattr(self, 'srt_data') or not self.srt_data:
            QMessageBox.warning(self, "警告", "请先选择辅助视频并提取字幕！")
            return
            
        self.log_message("🎬 开始根据字幕动态提取辅助素材并避让插图...")
        self.show_progress(True)
        prob = self.broll_prob_slider.value() / 100.0
        
        # 将 PDF 插图轨道的数据传给 B-Roll 处理器进行碰撞检测
        image_clips = []
        if hasattr(self, 'image_track'):
            image_clips = self.image_track.clips
            
        self.worker_broll = BrollProcessWorker(
            self.broll_video_path, self.srt_data, prob, image_clips, self.get_tmp_dir(),
            getattr(self, 'broll_min_duration', 0.0), getattr(self, 'broll_max_duration', 0.0)
        )
        self.worker_broll.progress_signal.connect(self.log_message)
        self.worker_broll.finished_signal.connect(self.on_broll_finished)
        self.worker_broll.start()

    def on_broll_finished(self, success, clips):
        self.show_progress(False)
        if success:
            self.broll_track.clips = []
            for c in clips:
                self.broll_track.add_clip(c)
            self.timeline_ui.rebuild_from_model()
            self.log_message(f"✅ 成功生成了 {len(clips)} 个辅助画面。")
            if not getattr(self, 'auto_pipeline_running', False):
                QMessageBox.information(self, "成功", f"生成了 {len(clips)} 个辅助画面。")
                
        if getattr(self, 'auto_pipeline_running', False) and self.auto_pipeline_step == 3:
            if success:
                self.auto_pipeline_step = 4
                self.log_message("⚡ [一键全自动] 辅助视频提取完成，开始导出视频")
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(1000, self.render_timeline)
            else:
                self.log_message("❌ [一键全自动] 辅助视频提取失败，自动流程终止。")
                self.auto_pipeline_running = False
                self.btn_auto_export.setEnabled(True)
                self.btn_auto_export.setText("⚡ 一键全自动导出视频")

    # ==========================
    # 导出渲染
    # ==========================
    def prompt_multi_export(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("📦 多格式打包导出")
        dialog.setMinimumWidth(400)
        
        layout = QVBoxLayout(dialog)
        
        lbl = QLabel("请选择您需要导出的格式 (可多选)：")
        lbl.setStyleSheet("font-size: 14px; font-weight: bold; margin-bottom: 10px; color: #333333;")
        layout.addWidget(lbl)
        
        from PyQt6.QtWidgets import QCheckBox
        
        chk_mp4 = QCheckBox("🎬 最终合成视频 (.mp4)")
        chk_mp4.setStyleSheet("font-size: 14px; color: #333333;")
        chk_mp4.setChecked(False)
        layout.addWidget(chk_mp4)
        
        chk_srt = QCheckBox("💬 独立外挂字幕 (.srt)")
        chk_srt.setStyleSheet("font-size: 14px; color: #333333;")
        layout.addWidget(chk_srt)
        
        layout.addSpacing(10)
        
        lbl_doc = QLabel("基于 AI 精修文章的文档 (需调用大模型)：")
        lbl_doc.setStyleSheet("font-size: 14px; font-weight: bold; margin-bottom: 5px; color: #333333;")
        layout.addWidget(lbl_doc)
        
        chk_ai_md = QCheckBox("✨ Markdown 文档 (.md)")
        chk_ai_md.setStyleSheet("font-size: 14px; color: #333333;")
        chk_ai_md.setChecked(True)
        layout.addWidget(chk_ai_md)
        
        chk_txt = QCheckBox("📄 纯文本 (.txt)")
        chk_txt.setStyleSheet("font-size: 14px; color: #333333;")
        layout.addWidget(chk_txt)
        
        chk_html = QCheckBox("🌐 纯净网页 (.html)")
        chk_html.setStyleSheet("font-size: 14px; color: #333333;")
        layout.addWidget(chk_html)
        
        chk_word = QCheckBox("📝 Word 文档 (.docx)")
        chk_word.setStyleSheet("font-size: 14px; color: #333333;")
        layout.addWidget(chk_word)
        
        chk_pdf = QCheckBox("📕 PDF 文档 (.pdf)")
        chk_pdf.setStyleSheet("font-size: 14px; color: #333333;")
        layout.addWidget(chk_pdf)
        
        layout.addSpacing(15)
        
        btn_export = QPushButton("🚀 一键打包导出")
        btn_export.setMinimumHeight(45)
        btn_export.setStyleSheet("font-size: 14px; font-weight: bold; background-color: #0078D7; color: white; border-radius: 6px;")
        layout.addWidget(btn_export)
        
        btn_cancel = QPushButton("取消")
        btn_cancel.setMinimumHeight(35)
        layout.addWidget(btn_cancel)
        
        def on_export():
            dialog.accept()
            self.execute_multi_export(
                chk_mp4.isChecked(),
                chk_srt.isChecked(),
                False,
                chk_ai_md.isChecked(),
                chk_txt.isChecked(),
                chk_html.isChecked(),
                chk_word.isChecked(),
                chk_pdf.isChecked()
            )
            
        btn_export.clicked.connect(on_export)
        btn_cancel.clicked.connect(dialog.reject)
        
        dialog.exec()

    def execute_multi_export(self, do_mp4, do_srt, do_raw_md, do_ai_md, do_txt, do_html, do_word, do_pdf):
        if not any([do_mp4, do_srt, do_raw_md, do_ai_md, do_txt, do_html, do_word, do_pdf]):
            QMessageBox.information(self, "提示", "您没有勾选任何导出格式。")
            return
            
        if do_srt:
            self.export_srt()
        if do_raw_md:
            self.export_article()
        if do_mp4:
            self.render_timeline()
            
        if any([do_ai_md, do_txt, do_html, do_word, do_pdf]):
            self.pending_ai_exports = {
                'md': do_ai_md,
                'txt': do_txt,
                'html': do_html,
                'word': do_word,
                'pdf': do_pdf
            }
            self.export_ai_article()

    def export_srt(self):
        if not hasattr(self, 'srt_data') or not self.srt_data:
            QMessageBox.warning(self, "错误", "没有字幕数据，无法导出 SRT！")
            return
            
        import sys
        _fallback = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
        out_dir = self.export_dir if self.export_dir else _fallback
        
        def format_ms(ms):
            s, ms_rem = divmod(ms, 1000)
            m, s = divmod(s, 60)
            h, m = divmod(m, 60)
            return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int(ms_rem):03d}"
        
        srt_content = ""
        for i, sub in enumerate(self.srt_data):
            start_str = format_ms(sub['start'])
            end_str = format_ms(sub['end'])
            text = sub['text']
            srt_content += f"{i+1}\n{start_str} --> {end_str}\n{text}\n\n"
            
        out_path = os.path.join(out_dir, "export_subtitles.srt")
        try:
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(srt_content)
            self.log_message(f"✅ 独立外挂字幕 (.srt) 已导出至: {out_path}")
        except Exception as e:
            self.log_message(f"❌ 导出 SRT 失败: {e}")

    def get_srt_pure_text(self):
        if not hasattr(self, 'srt_data') or not self.srt_data:
            return ""
        return "\n\n".join([sub['text'] for sub in self.srt_data])



    def export_ai_article(self):
        if not hasattr(self, 'srt_data') or not self.srt_data:
            QMessageBox.warning(self, "错误", "没有字幕数据，请先提取或导入字幕！")
            return
            
        import sys
        _fallback = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
        out_dir = self.export_dir if self.export_dir else _fallback
        out_dir = os.path.join(out_dir, "导出文档")
        os.makedirs(out_dir, exist_ok=True)
        
        image_clips = []
        if hasattr(self, 'image_track'):
            image_clips = self.image_track.clips
            
        api_key = self.api_key
        base_url = self.base_url
        model = getattr(self, 'selected_model', 'gemini-2.5-flash')
        if "自动" in model or "Round" in model:
            model = "gemini-2.5-flash"
        video_name = ""
        if hasattr(self, 'video_path') and self.video_path:
            video_name = Path(self.video_path).stem
            
        self.ai_article_worker = AIRewriteArticleWorker(self.srt_data, image_clips, api_key, base_url, model, out_dir, video_name=video_name)
        self.ai_article_worker.progress_signal.connect(self.log_message)
        self.ai_article_worker.finished_signal.connect(self.on_ai_article_finished)
        self.ai_article_worker.start()
        
        self.log_message("🚀 开始启动 AI 文章智能重写任务...")
        self.show_progress(True)
        
    def on_ai_article_finished(self, success, result, response_text=""):
        self.show_progress(False)
        if success:
            QMessageBox.information(self, "成功", f"✨ 爆款图文已生成至：\n{result}\n\n正在处理附属文档 (如有勾选)...")
            self.log_message("✅ AI 文章重写圆满完成！")
            
            if hasattr(self, 'pending_ai_exports'):
                do_txt = self.pending_ai_exports.get('txt', False)
                do_html = self.pending_ai_exports.get('html', False)
                do_word = self.pending_ai_exports.get('word', False)
                do_pdf = self.pending_ai_exports.get('pdf', False)
                
                import sys
                _fallback = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
                out_dir = self.export_dir if self.export_dir else _fallback
                out_dir = os.path.join(out_dir, "导出文档")
                os.makedirs(out_dir, exist_ok=True)
                
                if do_txt:
                    import re
                    txt_content = re.sub(r'[*_~`>\[\]()]', '', response_text).replace('#', '')
                    txt_path = os.path.join(out_dir, "export_document.txt")
                    try:
                        with open(txt_path, "w", encoding="utf-8") as f:
                            f.write(txt_content)
                        self.log_message(f"✅ 纯文本 (.txt) 已导出至: {txt_path}")
                    except Exception as e:
                        self.log_message(f"❌ 导出 TXT 失败: {e}")
                        
                if do_html or do_pdf:
                    import markdown
                    html_body = markdown.markdown(response_text)
                    full_html = f"<!DOCTYPE html><html><head><meta charset=\"utf-8\"><title>AI精修文档</title><style>body{{font-family:sans-serif;padding:20px;line-height:1.6;font-size:16px;color:#333;}}img{{max-width:100%;height:auto;}}</style></head><body>{html_body}</body></html>"
                    
                    if do_html:
                        html_path = os.path.join(out_dir, "export_document.html")
                        try:
                            with open(html_path, "w", encoding="utf-8") as f:
                                f.write(full_html)
                            self.log_message(f"✅ 纯净网页 (.html) 已导出至: {html_path}")
                        except Exception as e:
                            self.log_message(f"❌ 导出 HTML 失败: {e}")
                            
                    if do_pdf:
                        pdf_path = os.path.join(out_dir, "export_document.pdf")
                        def run_pdf_export():
                            try:
                                import os
                                os.environ["PLAYWRIGHT_BROWSERS_PATH"] = os.path.join(os.environ.get("LOCALAPPDATA", ""), "ms-playwright")
                                from playwright.sync_api import sync_playwright
                                with sync_playwright() as p:
                                    browser = p.chromium.launch(headless=True)
                                    page = browser.new_page()
                                    page.set_content(full_html, wait_until="networkidle")
                                    page.pdf(path=pdf_path, format="A4", print_background=True)
                                    browser.close()
                                self.log_message(f"✅ PDF 文档 (.pdf) 已导出至: {pdf_path}")
                            except Exception as e:
                                self.log_message(f"❌ 导出 PDF 失败: {e}")
                        import threading
                        threading.Thread(target=run_pdf_export, daemon=True).start()
                        
                if do_word:
                    word_path = os.path.join(out_dir, "export_document.docx")
                    try:
                        from docx import Document
                        doc = Document()
                        for line in response_text.split('\n'):
                            if line.startswith('# '):
                                doc.add_heading(line.replace('# ', '').strip(), level=1)
                            elif line.startswith('## '):
                                doc.add_heading(line.replace('## ', '').strip(), level=2)
                            elif line.startswith('### '):
                                doc.add_heading(line.replace('### ', '').strip(), level=3)
                            elif line.strip():
                                import re
                                clean_line = re.sub(r'[*_`~]', '', line.strip())
                                if clean_line.startswith('!['):
                                    continue
                                doc.add_paragraph(clean_line)
                        doc.save(word_path)
                        self.log_message(f"✅ Word 文档 (.docx) 已导出至: {word_path}")
                    except Exception as e:
                        self.log_message(f"❌ 导出 Word 失败: {e}")
        else:
            QMessageBox.warning(self, "错误", f"AI 重写失败: {result}")
            self.log_message(f"❌ AI 文章重写失败: {result}")

    def export_article(self):
        if not hasattr(self, 'srt_data') or not self.srt_data:
            QMessageBox.warning(self, "错误", "没有字幕数据，请先提取或导入字幕！")
            return
            
        out_dir = self.export_dir if self.export_dir else os.path.dirname(os.path.abspath(__file__))
        article_path = os.path.join(out_dir, "公众号图文.md")
        
        events = []
        for item in self.srt_data:
            events.append((item['start'], 'text', item['text']))
            
        if hasattr(self, 'image_track'):
            for clip in self.image_track.clips:
                import shutil
                img_name = os.path.basename(clip.source_path)
                target_img_path = os.path.join(out_dir, img_name)
                try:
                    if not os.path.exists(target_img_path) or os.path.abspath(clip.source_path) != os.path.abspath(target_img_path):
                        shutil.copy2(clip.source_path, target_img_path)
                except Exception:
                    pass
                events.append((clip.start_time - 1, 'image', img_name))
                
        events.sort(key=lambda x: x[0])
        
        try:
            with open(article_path, 'w', encoding='utf-8') as f:
                f.write("# 视频配套图文\n\n")
                current_paragraph = ""
                
                for t, e_type, content in events:
                    if e_type == 'text':
                        text = content.strip()
                        if not text:
                            continue
                        if text[-1] in ['，', '。', '！', '？', '；', ',', '.', '!', '?', ';']:
                            current_paragraph += text
                        else:
                            current_paragraph += text + "，"
                            
                        if len(current_paragraph) > 120 and current_paragraph[-1] in ['。', '！', '？', '.', '!', '?']:
                            f.write(current_paragraph + "\n\n")
                            current_paragraph = ""
                            
                    elif e_type == 'image':
                        if current_paragraph:
                            if current_paragraph[-1] == '，':
                                current_paragraph = current_paragraph[:-1] + "。"
                            f.write(current_paragraph + "\n\n")
                            current_paragraph = ""
                        f.write(f"![幻灯片插图]({content})\n\n")
                        
                if current_paragraph:
                    if current_paragraph[-1] == '，':
                        current_paragraph = current_paragraph[:-1] + "。"
                    f.write(current_paragraph + "\n\n")
                    
            QMessageBox.information(self, "成功", f"图文文章已生成至：\n{article_path}\n\n您可以使用 Typora 等 Markdown 编辑器打开，或复制到 MdNice 等工具排版发公众号。")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"生成文章失败: {e}")

    def render_timeline(self):
        if not self.video_track.clips:
            QMessageBox.warning(self, "警告", "没有主视频无法渲染！")
            return
            
        out_name = f"export_{Path(self.video_path).stem}.mp4"
        out_path = os.path.join(self.export_dir, out_name)
        
        self.log_message("🚀 开始渲染导出视频...")
        self.show_progress(True)
        self.btn_export.setText("渲染中...")
        self.btn_export.setEnabled(False)
        
        style_str = SUBTITLE_TEMPLATES.get(self.selected_template_key, SUBTITLE_TEMPLATES["default"])["style"]
        import re
        if "MarginV=" in style_str:
            style_str = re.sub(r"MarginV=\d+", f"MarginV={self.subtitle_margin_bottom}", style_str)
        else:
            if style_str:
                style_str += f",MarginV={self.subtitle_margin_bottom}"
            else:
                style_str = f"MarginV={self.subtitle_margin_bottom}"
        self.worker_render = RenderWorker(self.timeline, out_path, self.get_tmp_dir(), style_str, self.hw_accel, self.trim_start_s, self.trim_end_s, getattr(self, 'cover_path', ''), getattr(self, 'cover_duration', 0.5), getattr(self, 'broll_transition', 'random'), getattr(self, 'cover_title', ''), getattr(self, 'cover_subtitle', ''), getattr(self, 'cover_font', '微软雅黑(加粗)'), getattr(self, 'cover_template', 'classic_white_yellow'), getattr(self, 'cover_custom_title', ''), getattr(self, 'cover_custom_subtitle', ''), getattr(self, 'cover_title_y', 50), getattr(self, 'cover_spacing', 2), getattr(self, 'cover_title_scale', 100), getattr(self, 'cover_subtitle_scale', 100))
        self.worker_render.progress_signal.connect(self.log_message)
        self.worker_render.finished_signal.connect(self.on_render_finished)
        self.worker_render.start()
        
    def on_render_finished(self, success, out_path):
        self.show_progress(False)
        self.btn_export.setText("📦 多格式打包导出...")
        self.btn_export.setEnabled(True)
        
        if success and isinstance(out_path, str) and out_path.startswith("FFmpeg Error:"):
            success = False
            
        if success:
            self.log_message(f"🎉 渲染成功！文件: {out_path}")
            if not getattr(self, 'auto_pipeline_running', False):
                QMessageBox.information(self, "完成", f"渲染成功！文件: {out_path}")
        else:
            self.log_message("❌ 渲染失败！")
            err_msg = out_path if isinstance(out_path, str) else "未知错误"
            # Extract last 15 lines of FFmpeg error for the dialog to avoid truncation of the actual reason
            lines = err_msg.split('\n')
            if len(lines) > 15:
                err_msg = "...\n" + "\n".join(lines[-15:])
            if not getattr(self, 'auto_pipeline_running', False):
                QMessageBox.critical(self, "错误", f"渲染失败！\n{err_msg}")
                
        if getattr(self, 'auto_pipeline_running', False):
            self.auto_pipeline_running = False
            self.btn_auto_export.setEnabled(True)
            self.btn_auto_export.setText("⚡ 一键全自动导出视频")
            if success:
                if hasattr(self, 'export_ai_article'):
                    self.log_message("⏳ 视频渲染完成，正在自动生成配套图文稿件...")
                    # 假装勾选了 MD，确保配套的配置
                    if not hasattr(self, 'pending_ai_exports'):
                        self.pending_ai_exports = {'md': True}
                    self.export_ai_article()
                QMessageBox.information(self, "一键全自动完成", f"🎉 一键全自动视频导出成功！\n正在后台生成配套的图文稿件...\n视频已保存至: {out_path}")
            else:
                err_msg = out_path if isinstance(out_path, str) else "未知错误"
                lines = err_msg.split('\n')
                if len(lines) > 15:
                    err_msg = "...\n" + "\n".join(lines[-15:])
                QMessageBox.critical(self, "错误", f"一键全自动导出在渲染阶段失败！\n{err_msg}")

    def select_logo(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择Logo(支持图片/视频)", self.last_opened_dir, "Media Files (*.png *.jpg *.jpeg *.bmp *.mp4 *.mov *.webm *.avi)")
        if path:
            self.update_last_opened_dir(path)
            # Create a Logo Clip on the Logo track
            duration = self.video_track.clips[0].duration if self.video_track.clips else 10000
            
            # Load default settings from .env
            default_x = int(os.getenv("LOGO_X", "0"))
            default_y = int(os.getenv("LOGO_Y", "0"))
            default_scale = int(os.getenv("LOGO_SCALE", "100"))
            
            c = Clip(Path(path).name, path, 0, duration, TrackType.LOGO, x=default_x, y=default_y, scale=default_scale)
            self.logo_track.add_clip(c)
            self.timeline_ui.save_state()
            self.timeline_ui.rebuild_from_model()
            self.log_message(f"🌟 添加 Logo 成功: {Path(path).name}")

    def select_cover(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择视频封面图片", self.last_opened_dir, "Image Files (*.png *.jpg *.jpeg *.bmp)")
        if path:
            self.update_last_opened_dir(path)
            self.cover_path = path
            self.lbl_cover.setText(f"当前封面: {Path(path).name}")
            self.cover_track.clips.clear()
            duration_ms = int(self.cover_duration * 1000)
            c = Clip(Path(path).name, path, 0, duration_ms, TrackType.COVER)
            self.cover_track.add_clip(c)
            self.timeline_ui.rebuild_from_model()
            self.log_message(f"🖼️ 设置视频封面成功: {Path(path).name} (已加入时间轴)")
            
    def on_cover_duration_changed(self, val):
        self.cover_duration = val
        if hasattr(self, 'cover_track') and self.cover_track.clips:
            self.cover_track.clips[0].duration = int(val * 1000)
            self.timeline_ui.rebuild_from_model()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    def dropEvent(self, event):
        url = event.mimeData().urls()[0]
        file_name = url.toLocalFile()
        if file_name.endswith('.mp4'):
            self.video_path = file_name
            self.lbl_video.setText(f"当前:\n{Path(file_name).name}")
            self.media_player.setSource(QUrl.fromLocalFile(file_name))
            self.video_track.clips = [Clip(Path(file_name).name, file_name, 0, 3600000, TrackType.VIDEO)]
            self.timeline_ui.rebuild_from_model()
            
    def set_export_dir(self):
        dir_name = QFileDialog.getExistingDirectory(self, "选择导出目录", self.last_opened_dir)
        if dir_name:
            self.update_last_opened_dir(dir_name)
            self.export_dir = dir_name
            if hasattr(self, 'lbl_export_path'):
                self.lbl_export_path.setText(f"当前目录: {self.export_dir}")
                
    def closeEvent(self, event):
        event.accept()
def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(resource_path('logo.ico')))
    app.setStyleSheet(DARK_THEME_QSS)
    window = MainWindow()
    window.setWindowIcon(QIcon(resource_path('logo.ico')))
    window.show()
    sys.exit(app.exec())
