"""
slide_processor.py
PDF → 图片 → AI识别 → 字幕匹配 → FFmpeg合成
"""

import os
import json
import base64
import subprocess
from pathlib import Path
from openai import OpenAI
import imageio_ffmpeg


# ─────────────────────────────────────────────
# 工具函数
# ─────────────────────────────────────────────

def get_ffmpeg_path():
    try:
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def get_video_dimensions(video_path: str):
    """用 ffprobe 获取视频宽高"""
    ffprobe = get_ffmpeg_path().replace("ffmpeg", "ffprobe")
    if not os.path.exists(ffprobe):
        ffprobe = "ffprobe"
    try:
        result = subprocess.run(
            [ffprobe, "-v", "quiet", "-print_format", "json",
             "-show_streams", video_path],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        info = json.loads(result.stdout)
        for stream in info.get("streams", []):
            if stream.get("codec_type") == "video":
                return stream["width"], stream["height"]
    except Exception:
        pass
    return 1920, 1080  # 默认值


# ─────────────────────────────────────────────
# STEP 1: PDF → 图片
# ─────────────────────────────────────────────

def remove_watermark_from_image(image_path: str):
    """自动去除 NotebookLM 右下角水印"""
    try:
        from PIL import Image, ImageDraw
        with Image.open(image_path) as img:
            draw = ImageDraw.Draw(img)
            width, height = img.size
            # 覆盖右下角水印：高度倒数6%，宽度倒数15%
            rect = [
                (width * 0.85, height * 0.94),
                (width, height)
            ]
            draw.rectangle(rect, fill="black")
            img.save(image_path, quality=95)
    except Exception:
        pass

def convert_pdf_to_images(
    pdf_path: str,
    output_dir: str,
    dpi: int = 150,
    poppler_path: str = None, # 保持参数兼容性，但不再使用
    progress_callback=None
) -> list:
    """
    将 PDF 每页转换为图片。
    强制采用性能最强的 PyMuPDF (fitz) 进行极速转换。
    """
    os.makedirs(output_dir, exist_ok=True)
    image_paths = []

    try:
        import fitz  # PyMuPDF 库
    except ImportError as e:
        raise RuntimeError("未检测到 PyMuPDF (fitz)。请在终端执行命令: pip install PyMuPDF") from e

    if progress_callback:
        progress_callback("📄 正在使用 PyMuPDF 极速提取 PDF 图片...")
    
    doc = fitz.open(pdf_path)
    for i in range(len(doc)):
        page = doc[i]
        # 按 DPI 计算缩放，默认 PDF 基础 DPI 为 72
        zoom = dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)
        
        # alpha=False 避免透明通道，直接生成 RGB
        pix = page.get_pixmap(matrix=mat, alpha=False)
        
        # 如果宽度超过 1920，重新计算比例并固定宽度为 1920
        if pix.width > 1920:
            scale = 1920 / page.rect.width
            mat = fitz.Matrix(scale, scale)
            pix = page.get_pixmap(matrix=mat, alpha=False)

        out_path = os.path.join(output_dir, f"slide_{i+1:03d}.jpg")
        pix.save(out_path, "jpeg", 85)
        remove_watermark_from_image(out_path)
        image_paths.append(out_path)
        
    doc.close()
    if progress_callback:
        progress_callback(f"✅ PDF 极速转换完成，共 {len(image_paths)} 页")
    return image_paths

def convert_pptx_to_images(pptx_path: str, output_dir: str, progress_callback=None) -> list:
    """
    使用 PowerPoint COM 组件将 PPTX 转换为图片。
    """
    os.makedirs(output_dir, exist_ok=True)
    image_paths = []
    
    try:
        import win32com.client
        import pythoncom
        import re
        import glob
        
        # 初始化 COM 库，非常重要
        pythoncom.CoInitialize()
        
        if progress_callback:
            progress_callback("📄 正在使用 PowerPoint 提取幻灯片...")
            
        powerpoint = win32com.client.Dispatch("PowerPoint.Application")
        presentation = powerpoint.Presentations.Open(os.path.abspath(pptx_path), WithWindow=False)
        
        # 导出为 JPG
        presentation.Export(os.path.abspath(output_dir), "JPG")
        presentation.Close()
        powerpoint.Quit()
        
        # 释放 COM 库
        pythoncom.CoUninitialize()
        
        # 找到导出的所有 jpg 文件 (使用 set 去重，防止 Windows 环境下 glob 大小写不敏感导致重复)
        exported_files = list(set(glob.glob(os.path.join(output_dir, "*.jpg")) + glob.glob(os.path.join(output_dir, "*.JPG"))))
        
        # 自然排序，确保 幻灯片2.jpg 在 幻灯片10.jpg 之前
        def natural_sort_key(s):
            return [int(text) if text.isdigit() else text.lower() for text in re.split('([0-9]+)', s)]
            
        exported_files.sort(key=natural_sort_key)
        
        if progress_callback:
            progress_callback(f"✅ PPTX 转换完成，共 {len(exported_files)} 页")
            
        return exported_files
    except Exception as e:
        if progress_callback:
            progress_callback(f"❌ 提取 PPTX 失败: {e}")
        return []


# ─────────────────────────────────────────────
# STEP 1.5: 图片压缩
# ─────────────────────────────────────────────

def compress_images(image_paths: list, quality_level: str = "Medium", tmp_dir: str = None, progress_callback=None) -> list:
    """压缩图片，节省大模型 Token"""
    try:
        from PIL import Image
    except ImportError:
        if progress_callback:
            progress_callback("⚠️ 未检测到 Pillow 库，跳过图片压缩。")
        return image_paths

    if not image_paths:
        return []
        
    if progress_callback:
        progress_callback(f"🗜️ 正在压缩图片以节省 Token (级别: {quality_level})...")
        
    compressed_paths = []
    
    if quality_level == "Low":
        max_size = (800, 800)
        q = 60
    elif quality_level == "High":
        max_size = (1920, 1920)
        q = 90
    else: # Medium
        max_size = (1280, 1280)
        q = 75
        
    for i, path in enumerate(image_paths):
        try:
            from PIL import Image
            import os
            
            img = Image.open(path)
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            out_path = path.replace(".jpg", f"_compressed_{i}.jpg")
            img.save(out_path, format="JPEG", quality=q, optimize=True)
            compressed_paths.append(out_path)
            
        except Exception as e:
            if progress_callback:
                progress_callback(f"⚠️ 图片压缩失败: {path}, {e}")
            compressed_paths.append(path)
            
    return compressed_paths

def ai_analyze_slides(
    image_paths: list,
    api_key: str,
    base_url: str,
    model_name: str,
    cache_path: str = "slide_index.json",
    compressed_image_paths: list = None,
    progress_callback=None
) -> list:
    """
    对每张幻灯片图片调用多模态 AI，获取内容描述。
    结果缓存到 slide_index.json，避免重复调用。
    多线程并发版本，并发数等于 API Key 数量。
    """
    import queue
    import threading
    import concurrent.futures
    import time
    
    # 读取已有缓存
    cache = {}
    cache_lock = threading.Lock()
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cached = json.load(f)
                for item in cached:
                    # 使用 basename 作为唯一 key，防止项目路径移动后导致缓存失效并重复累加
                    basename = os.path.basename(item["image_path"])
                    cache[basename] = item
        except Exception:
            pass

    api_keys = [k.strip() for k in api_key.replace("，", "\n").replace(",", "\n").split("\n") if k.strip()]
    if not api_keys:
        api_keys = [""]

    # 初始化 Key 队列
    key_queue = queue.Queue()
    for k in api_keys:
        key_queue.put(k)

    fallback_models = [
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        "gemini-3-flash-preview",
        "gemini-3.1-flash-lite",
        "gemini-3.5-flash",
        "gemini-robotics-er-1.6-preview"
    ]
    models = []
    if "轮询" in model_name or "Round-Robin" in model_name:
        models = fallback_models
    else:
        models = [m.strip() for m in model_name.replace("，", ",").split(",") if m.strip()]
        for m in fallback_models:
            if m not in models:
                models.append(m)

    system_prompt = (
        "你是一个专业的幻灯片内容分析师。"
        "我将给你展示一张幻灯片图片，请你："
        "1. 仔细寻找图片角落是否带有类似 '001-P1'、'START-P0'、'END-P99' 格式的【专属编号水印】，如果有，必须将其作为第一个关键词强制提取！"
        "2. 用中文描述这张幻灯片的核心主题和关键信息（2-4句话）"
        "3. 列出3-8个关键词（用于后续与视频解说字幕的语义匹配）"
        "请以JSON格式返回：{\"description\": \"...\", \"keywords\": [\"...\", \"...\"]}"
    )

    total = len(image_paths)
    
    def process_single_slide(i, img_path):
        slide_num = i + 1
        basename = os.path.basename(img_path)

        # 命中缓存直接复用（增加缓存有效性校验）
        with cache_lock:
            cached_item = cache.get(basename)
            
        if cached_item:
            is_valid = True
            if not cached_item.get("keywords"):
                is_valid = False
            desc = cached_item.get("description", "").strip()
            if desc.startswith("{") or "识别失败" in desc:
                is_valid = False

            if is_valid:
                if progress_callback:
                    progress_callback(f"   ⚡ 第 {slide_num}/{total} 页（使用缓存）")
                # Fix: Update the image_path to the current actual path in case the project was moved
                cached_item["image_path"] = img_path
                return cached_item
            else:
                if progress_callback:
                    progress_callback(f"   ⚠️ 第 {slide_num} 页缓存数据异常，将强制重新识别...")

        target_read_path = compressed_image_paths[i] if compressed_image_paths else img_path

        try:
            with open(target_read_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode("utf-8")

            # 判断图片格式
            suffix = Path(target_read_path).suffix.lower()
            mime = "image/jpeg" if suffix in (".jpg", ".jpeg") else "image/png"

            success = False
            raw = ""
            
            # 最多尝试次数等于初始 Key 的数量
            max_attempts = len(api_keys)
            
            for attempt in range(max_attempts):
                if success:
                    break
                    
                cur_key = key_queue.get()
                try:
                    client = OpenAI(api_key=cur_key, base_url=base_url, max_retries=3)
                    
                    for model_idx, cur_model in enumerate(models):
                        if progress_callback:
                            masked_key = cur_key[:10] + "..." + cur_key[-5:] if len(cur_key) > 15 else "***"
                            progress_callback(f"   - 正在请求识别第 {slide_num}/{total} 页 (Key: {masked_key}, 模型: {cur_model}) ...")
                        try:
                            response = client.chat.completions.create(
                                model=cur_model,
                                messages=[
                                    {"role": "system", "content": system_prompt},
                                    {"role": "user", "content": [
                                        {"type": "text", "text": f"请分析第 {slide_num} 页幻灯片的内容："},
                                        {"type": "image_url", "image_url": {
                                            "url": f"data:{mime};base64,{img_b64}"
                                        }}
                                    ]}
                                ],
                                temperature=0.1,
                                max_tokens=1024
                            )
                            
                            raw = (response.choices[0].message.content or "").strip()

                            # 解析 JSON，容忍 markdown 包装
                            if raw.startswith("```"):
                                lines = raw.split("\n")
                                raw = "\n".join(
                                    l for l in lines
                                    if not l.strip().startswith("```")
                                )

                            parsed = json.loads(raw)
                            item = {
                                "slide_idx": slide_num,
                                "image_path": img_path,
                                "description": parsed.get("description", ""),
                                "keywords": parsed.get("keywords", [])
                            }

                            if progress_callback:
                                progress_callback(f"   - ✅ 第 {slide_num} 页识别成功 (最终使用模型: {cur_model})")
                            success = True
                            break
                        except Exception as e:
                            err_msg = str(e)
                            short_err = err_msg.split('\n')[0][:100] + "..." if len(err_msg) > 100 else err_msg
                            if progress_callback:
                                progress_callback(f"   - ⚠️ 模型 {cur_model} 失败 ({short_err})，尝试下一个...")
                            time.sleep(1)
                finally:
                    # 无论成功或失败，都将 key 放回队列，以便其他任务或重试使用
                    key_queue.put(cur_key)
                    
                if not success and attempt < max_attempts - 1:
                    time.sleep(1)
            
            if not success:
                raise RuntimeError(f"第 {slide_num} 页所有 API Key 和模型均已重试失败。")

        except json.JSONDecodeError:
            # 如果AI返回非JSON，把原文存入 description
            item = {
                "slide_idx": slide_num,
                "image_path": img_path,
                "description": raw if raw else "识别失败",
                "keywords": []
            }
        except Exception as e:
            if progress_callback:
                progress_callback(f"   ❌ 第 {slide_num} 页识别彻底失败: {e}")
            raise # 识别失败不再静默写入缓存，直接抛出异常

        with cache_lock:
            cache[basename] = item
            # 每次识别后立即保存缓存
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(list(cache.values()), f, ensure_ascii=False, indent=2)

        return item

    results = []
    # 并发数设置为 Key 的数量
    max_workers = len(api_keys)
    
    if progress_callback:
        progress_callback(f"🚀 启动并发识别，使用 {max_workers} 个并发线程...")
        
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_index = {executor.submit(process_single_slide, i, path): i for i, path in enumerate(image_paths)}
        
        for future in concurrent.futures.as_completed(future_to_index):
            idx = future_to_index[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                # 异常会在子线程抛出并通过 future.result() 传递过来
                raise e

    # 结果按 slide_idx 排序
    results.sort(key=lambda x: x["slide_idx"])

    if progress_callback:
        progress_callback(f"✅ AI识别完成，共 {len(results)} 张幻灯片")

    return results
# ─────────────────────────────────────────────
# STEP 3: AI 匹配字幕范围
# ─────────────────────────────────────────────

def ai_match_subtitle_range(
    slide_index: list,
    srt_data: list,
    api_key: str,
    base_url: str,
    model_name: str,
    advance_ms: int = 1000,
    progress_callback=None
) -> list:
    """
    将幻灯片内容描述和字幕列表发给AI，
    让AI判断每张幻灯片对应字幕的起止范围。

    srt_data 格式：[{"start": ms, "end": ms, "text": "..."}, ...]

    返回格式：
    [
        {
            "slide_idx": 1,
            "image_path": "...",
            "description": "...",
            "first_sub_idx": 8,    # 0-based
            "last_sub_idx": 13,
            "insert_ms": 33160,    # first_sub.start - advance_ms
            "hide_ms": 56320,      # last_sub.end
        },
        ...
    ]
    """
    if progress_callback:
        progress_callback("🔗 正在调用AI匹配幻灯片与字幕时间段...")

    api_keys = [k.strip() for k in api_key.replace("，", "\n").replace(",", "\n").split("\n") if k.strip()]
    if not api_keys:
        api_keys = [""]

    # 构建幻灯片描述文本
    slides_text = ""
    for item in slide_index:
        kw = "、".join(item["keywords"]) if item["keywords"] else "无"
        slides_text += (
            f"[第{item['slide_idx']}张] "
            f"内容：{item['description']} "
            f"关键词：{kw}\n"
        )

    # 构建字幕文本（编号|开始ms|结束ms|文字）
    subs_text = ""
    for i, sub in enumerate(srt_data):
        subs_text += f"{i}|{sub['start']}|{sub['end']}|{sub['text']}\n"

    prompt = f"""以下是PPT幻灯片的内容描述（共{len(slide_index)}张）：
{slides_text}

以下是视频字幕列表（格式：编号|开始时间ms|结束时间ms|文字内容）：
{subs_text}

任务：
请判断每张幻灯片对应视频解说中的字幕范围。
即：从第几条字幕开始讲这张幻灯片的内容，到第几条字幕结束。

注意：
- 每张幻灯片可能对应连续的多条字幕
- 字幕编号从0开始
- 【关键锚点】：如果幻灯片关键词中包含类似 '001-P1' 这样的专属水印编号，表示它属于 001 场赛事的对应页面；'START-P0' 代表全片开场；'END-P99' 代表全片结尾。请务必利用这些绝对线索，在茫茫字幕中精准锚定，彻底防止多场赛事之间发生张冠李戴！
- 如果某张幻灯片在字幕中没有明确对应内容，请合理推断（相邻幻灯片之间均分）
- 不同幻灯片的范围不应重叠

请以JSON数组格式返回，示例：
[
  {{"slide_idx": 1, "first_sub_idx": 8, "last_sub_idx": 13}},
  {{"slide_idx": 2, "first_sub_idx": 14, "last_sub_idx": 32}},
  ...
]

只返回JSON，不要有其他文字。"""
    fallback_models = [
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        "gemini-3-flash-preview",
        "gemini-3.1-flash-lite",
        "gemini-3.5-flash",
        "gemini-robotics-er-1.6-preview"
    ]
    models = []
    if "轮询" in model_name or "Round-Robin" in model_name:
        models = fallback_models
    else:
        models = [m.strip() for m in model_name.replace("，", ",").split(",") if m.strip()]
        for m in fallback_models:
            if m not in models:
                models.append(m)

    success = False
    raw = ""
    matches = []
    import time
    for key_idx, cur_key in enumerate(api_keys):
        if success:
            break
            
        masked_key = cur_key[:10] + "..." + cur_key[-5:] if len(cur_key) > 15 else "***"
        if progress_callback:
            progress_callback(f"🔑 正在使用 API Key (第 {key_idx+1}/{len(api_keys)} 个): {masked_key}")
            
        client = OpenAI(api_key=cur_key, base_url=base_url, max_retries=3)
        
        for model_idx, cur_model in enumerate(models):
            try:
                response = client.chat.completions.create(
                    model=cur_model,
                    messages=[
                        {"role": "system", "content": "你是一个专业的视频内容对齐分析师，擅长将PPT幻灯片与视频解说字幕进行精准匹配。"},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.1,
                    max_tokens=2048
                )

                raw = (response.choices[0].message.content or "").strip()

                # 清理 markdown
                if raw.startswith("```"):
                    lines = raw.split("\n")
                    raw = "\n".join(l for l in lines if not l.strip().startswith("```"))

                matches = json.loads(raw)
                success = True
                break
            except Exception as e:
                err_msg = str(e)
                short_err = err_msg.split('\n')[0][:100] + "..." if len(err_msg) > 100 else err_msg
                if progress_callback:
                    progress_callback(f"   - ⚠️ Key {key_idx+1}, 模型 {cur_model} 失败 ({short_err})，尝试下一个...")
                time.sleep(1)

    if not success:
        if progress_callback:
            progress_callback(f"❌ 字幕匹配失败: 所有 API Key 和模型均已重试失败。")
        raise RuntimeError("所有 API Key 和模型均已重试失败。")

    # 构建最终结果，计算精确时间
    results = []
    slide_map = {item["slide_idx"]: item for item in slide_index}

    if not srt_data:
        return []

    for m in matches:
        sidx = m.get("slide_idx", 0)
        first_i = max(0, min(len(srt_data) - 1, int(m.get("first_sub_idx", 0))))
        last_i = max(0, min(len(srt_data) - 1, int(m.get("last_sub_idx", 0))))

        first_sub = srt_data[first_i]
        last_sub = srt_data[last_i]

        # 插入时间 = 首句开始 - 提前量（最少为0）
        insert_ms = max(0, first_sub["start"] - advance_ms)
        hide_ms = last_sub["end"]

        slide_info = slide_map.get(sidx, {})
        results.append({
            "slide_idx": sidx,
            "image_path": slide_info.get("image_path", ""),
            "description": slide_info.get("description", ""),
            "first_sub_idx": first_i,
            "last_sub_idx": last_i,
            "insert_ms": insert_ms,
            "hide_ms": hide_ms,
        })

    # 按插入时间排序
    results.sort(key=lambda x: x["insert_ms"])

    if progress_callback:
        progress_callback(f"✅ 时间匹配完成，共 {len(results)} 张幻灯片已对齐")

    return results


# ─────────────────────────────────────────────
# STEP 4: FFmpeg 合成
# ─────────────────────────────────────────────

def build_overlay_video(
    video_path: str,
    timing_list: list,
    output_path: str,
    mode: str = "fullscreen",
    progress_callback=None
) -> str:
    """
    按时间段将幻灯片图片叠加/替换到视频中。

    timing_list: [{"slide_idx", "image_path", "insert_ms", "hide_ms"}, ...]
    mode:
        "fullscreen"  - 图片全屏替换视频画面（保留音频）
        "pip_right"   - 右侧画中画（图片占视频宽度40%）
        "pip_left"    - 左侧画中画
    """
    if progress_callback:
        progress_callback("🎬 正在生成FFmpeg合成命令...")

    if not timing_list:
        raise ValueError("时间轴列表为空，无法合成")

    ffmpeg = get_ffmpeg_path()
    vw, vh = get_video_dimensions(video_path)

    if mode == "fullscreen":
        return _build_fullscreen(ffmpeg, video_path, timing_list, output_path,
                                  vw, vh, progress_callback)
    elif mode in ("pip_right", "pip_left"):
        return _build_pip(ffmpeg, video_path, timing_list, output_path,
                          vw, vh, mode, progress_callback)
    else:
        raise ValueError(f"不支持的合成模式: {mode}")


def _build_fullscreen(ffmpeg, video_path, timing_list, output_path, vw, vh, progress_callback):
    """全屏替换模式：在指定时间段内用幻灯片图片完全替代视频画面"""

    # 构建 filtergraph
    # 每张图片先 scale 到视频尺寸，再用 overlay + enable 控制显隐
    # 思路：[0:v] 是原视频，逐层叠加图片（完全覆盖）

    inputs = ["-i", video_path]
    for item in timing_list:
        inputs += ["-loop", "1", "-i", item["image_path"]]

    filter_parts = []
    prev_label = "0:v"

    for idx, item in enumerate(timing_list):
        stream_idx = idx + 1
        start_s = item["insert_ms"] / 1000.0
        end_s = item["hide_ms"] / 1000.0
        cur_label = f"v{idx + 1}"

        # scale图片到视频尺寸，再 overlay（完全覆盖）
        scaled = f"scaled{idx + 1}"
        filter_parts.append(
            f"[{stream_idx}:v]scale={vw}:{vh},setsar=1[{scaled}]"
        )
        filter_parts.append(
            f"[{prev_label}][{scaled}]overlay=0:0:"
            f"enable='between(t,{start_s:.3f},{end_s:.3f})'[{cur_label}]"
        )
        prev_label = cur_label

    filter_complex = ";".join(filter_parts)

    cmd = [
        ffmpeg, "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", f"[{prev_label}]",
        "-map", "0:a",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "18",
        "-c:a", "copy",
        output_path
    ]

    return _run_ffmpeg(cmd, output_path, progress_callback)


def _build_pip(ffmpeg, video_path, timing_list, output_path, vw, vh, mode, progress_callback):
    """画中画模式：图片叠加在视频左侧或右侧（占宽40%）"""

    pip_w = int(vw * 0.4)
    pip_h = int(pip_w * 9 / 16)  # 保持16:9比例
    pip_h = min(pip_h, vh)

    if mode == "pip_right":
        x_pos = vw - pip_w - 10
        y_pos = (vh - pip_h) // 2
    else:  # pip_left
        x_pos = 10
        y_pos = (vh - pip_h) // 2

    inputs = ["-i", video_path]
    for item in timing_list:
        inputs += ["-loop", "1", "-i", item["image_path"]]

    filter_parts = []
    prev_label = "0:v"

    for idx, item in enumerate(timing_list):
        stream_idx = idx + 1
        start_s = item["insert_ms"] / 1000.0
        end_s = item["hide_ms"] / 1000.0
        cur_label = f"v{idx + 1}"

        scaled = f"scaled{idx + 1}"
        filter_parts.append(
            f"[{stream_idx}:v]scale={pip_w}:{pip_h},setsar=1[{scaled}]"
        )
        filter_parts.append(
            f"[{prev_label}][{scaled}]overlay={x_pos}:{y_pos}:"
            f"enable='between(t,{start_s:.3f},{end_s:.3f})'[{cur_label}]"
        )
        prev_label = cur_label

    filter_complex = ";".join(filter_parts)

    cmd = [
        ffmpeg, "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", f"[{prev_label}]",
        "-map", "0:a",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "23",
        "-c:a", "copy",
        output_path
    ]

    return _run_ffmpeg(cmd, output_path, progress_callback)


def _run_ffmpeg(cmd, output_path, progress_callback):
    """执行FFmpeg命令"""
    if progress_callback:
        progress_callback("⚙️ FFmpeg 合成中，请稍候（这可能需要几分钟）...")

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            check=True
        )
        if progress_callback:
            progress_callback(f"✅ 视频合成完成！输出文件: {output_path}")
        return output_path
    except subprocess.CalledProcessError as e:
        err_msg = e.stderr.decode("utf-8", errors="ignore") if e.stderr else str(e)
        if progress_callback:
            progress_callback(f"❌ FFmpeg合成失败:\n{err_msg[-1000:]}")
        raise RuntimeError(f"FFmpeg合成失败:\n{err_msg}") from e
