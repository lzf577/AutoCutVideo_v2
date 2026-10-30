import os
import subprocess
from pathlib import Path
import base64
from openai import OpenAI
from moviepy.editor import VideoFileClip
import imageio_ffmpeg

def get_ffmpeg_path():
    try:
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"

def extract_audio(video_path: str, tmp_dir: str, bitrate: str = "128k", progress_callback=None) -> str:
    """提取本地音频"""
    if progress_callback:
        progress_callback(f"正在本地提取音频 ({bitrate})，这不会消耗网络流量...")
    
    audio_dir = os.path.join(tmp_dir, "audio")
    os.makedirs(audio_dir, exist_ok=True)
    audio_path = os.path.join(audio_dir, "temp_audio.mp3")
    
    try:
        video = VideoFileClip(video_path)
        if video.audio is None:
            raise ValueError("视频文件中不存在音轨。")
            
        if bitrate == "8k":
            fps = 8000
        elif bitrate == "16k":
            fps = 16000
        elif bitrate == "32k":
            fps = 22050
        else:
            fps = 44100
            
        video.audio.write_audiofile(audio_path, bitrate=bitrate, fps=fps, logger=None)
        video.close()
        if progress_callback:
            progress_callback("✅ 音频提取成功！")
        return audio_path
    except Exception as e:
        if progress_callback:
            progress_callback(f"❌ 提取音频失败: {e}")
        raise

def polish_srt_with_llm(input_srt_path, output_srt_path, api_key, base_url, llm_model, progress_callback=None):
    try:
        from openai import OpenAI
        import concurrent.futures
        import threading
        
        if progress_callback:
            progress_callback(f"🧠 正在使用大模型 ({llm_model}) 进行智能错别字校对，请稍候...")
            
        with open(input_srt_path, "r", encoding="utf-8") as f:
            raw_srt = f.read()
            
        api_keys = [k.strip() for k in api_key.replace("，", ",").split(",") if k.strip()]
        if not api_keys:
            api_keys = [""]
            
        system_prompt = (
            "你是一个专业的字幕校对专家。你的任务是修正语音识别生成的错别字，并使得句子稍微通顺。\n"
            "【最高优先级警告：格式严格性】\n"
            "1. 绝不允许合并相邻的字幕块！哪怕它们合起来是一句完整的话，你也必须保持它们被切分的状态！\n"
            "2. 绝对不能修改时间轴（形如 00:00:00,000 --> 00:00:02,000）！\n"
            "3. 绝对不能删除或修改数字序号！\n"
            "4. 每个字幕块之间必须保留一个空行！\n"
            "如果原文是：\n"
            "1\n"
            "00:00:00,000 --> 00:00:02,000\n"
            "我们今天\n\n"
            "2\n"
            "00:00:02,000 --> 00:00:04,000\n"
            "来拆揭比赛\n\n"
            "你输出的格式必须完全一致（仅仅修正错别字）：\n"
            "1\n"
            "00:00:00,000 --> 00:00:02,000\n"
            "我们今天\n\n"
            "2\n"
            "00:00:02,000 --> 00:00:04,000\n"
            "来拆解比赛\n\n"
            "绝不允许合并时间轴和文本！\n"
            "请直接输出校对后的完整SRT文本，必须输出简体中文，不要包含任何额外的解释。"
        )
        
        fallback_models = [
            "gemini-2.5-flash",
            "gemini-2.5-flash-lite",
            "gemini-3-flash-preview",
            "gemini-3.1-flash-lite",
            "gemini-3.5-flash",
            "gemini-robotics-er-1.6-preview"
        ]
        
        models = []
        if "轮询" in llm_model or "Round-Robin" in llm_model:
            models = fallback_models
        else:
            models = [m.strip() for m in llm_model.replace("，", ",").split(",") if m.strip()]
            for m in fallback_models:
                if m not in models:
                    models.append(m)
                    
        success_event = threading.Event()
        result_lock = threading.Lock()
        shared_polished_text = [""]
        
        def safe_progress(msg):
            if progress_callback and not success_event.is_set():
                try:
                    progress_callback(msg)
                except Exception:
                    pass

        def make_request(key_idx, cur_key, model_idx, cur_model):
            # 如果别的线程已经成功了，直接退出不发请求了
            if success_event.is_set():
                return False
                
            client = OpenAI(api_key=cur_key, base_url=base_url)
            try:
                masked_key = cur_key[:8] + "..." if len(cur_key) > 10 else "***"
                safe_progress(f"   🚀 并发请求: (Key {key_idx+1}, 模型: {cur_model})")
                    
                response = client.chat.completions.create(
                    model=cur_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": raw_srt}
                    ],
                    temperature=0.2
                )
                
                # 如果请求途中别的线程成功了，直接丢弃本线程结果
                if success_event.is_set():
                    return False
                    
                text = response.choices[0].message.content.strip()
                
                with result_lock:
                    if not success_event.is_set():
                        shared_polished_text[0] = text
                        success_event.set()
                        safe_progress(f"   ✅ 请求最快返回！(Key {key_idx+1}, 模型: {cur_model})，已中止其他等待中的任务。")
                        return True
            except Exception as e:
                err_msg = str(e)
                short_err = err_msg.split('\n')[0][:100] + "..." if len(err_msg) > 100 else err_msg
                # 为了日志整洁，如果不报 404 等无关紧要的错，或者如果已经成功了就不发报错
                safe_progress(f"   ⚠️ 并发队列报错 (Key {key_idx+1}, 模型 {cur_model}): {short_err} (不影响主流程)")
            return False

        # 构造所有的 (key, model) 组合任务
        tasks = []
        for key_idx, cur_key in enumerate(api_keys):
            for model_idx, cur_model in enumerate(models):
                tasks.append((key_idx, cur_key, model_idx, cur_model))

        if progress_callback:
             progress_callback(f"⚡ 启动并发竞速模式，共分发 {len(tasks)} 个请求组合，取最快响应...")

        # 限制最大并发数，防止系统 socket 耗尽
        max_workers = min(30, len(tasks))
        if max_workers == 0:
            max_workers = 1

        executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        futures = [executor.submit(make_request, *t) for t in tasks]

        # 等待任何一个任务成功，或者所有任务结束
        for _ in concurrent.futures.as_completed(futures):
            if success_event.is_set():
                # 如果已经有成功的，尝试取消所有还未开始的任务
                for f in futures:
                    f.cancel()
                break

        # 不阻塞等待依然在执行的无用任务，允许主线程立刻继续往下走
        executor.shutdown(wait=False)

        if not success_event.is_set():
            raise RuntimeError("所有 API Key 和模型组合并发请求均已失败，请检查网络或更换密钥。")
            
        polished_text = shared_polished_text[0]

        if polished_text.startswith("```"):
            lines = polished_text.split('\n')
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            polished_text = '\n'.join(lines).strip()
            
        if polished_text and "-->" in polished_text:
            # 尝试把原始的正确时间轴，缝合到 AI 返回的文字上
            try:
                def parse_srt(content):
                    blocks = []
                    for block in content.strip().split('\n\n'):
                        lines = [l for l in block.split('\n') if l.strip()]
                        if len(lines) >= 2:
                            time_idx = -1
                            for i, l in enumerate(lines):
                                if '-->' in l:
                                    time_idx = i
                                    break
                            if time_idx != -1 and time_idx + 1 < len(lines):
                                blocks.append({
                                    'idx': lines[time_idx - 1] if time_idx > 0 else "",
                                    'time': lines[time_idx],
                                    'text': '\n'.join(lines[time_idx + 1:])
                                })
                    return blocks
                
                raw_blocks = parse_srt(raw_srt)
                polished_blocks = parse_srt(polished_text)
                
                if len(raw_blocks) > 0 and len(raw_blocks) == len(polished_blocks):
                    merged_out = []
                    for i in range(len(raw_blocks)):
                        r_b = raw_blocks[i]
                        p_b = polished_blocks[i]
                        # 强制使用原本正确的 idx 和 time
                        merged_out.append(f"{r_b['idx']}\n{r_b['time']}\n{p_b['text']}")
                    polished_text = '\n\n'.join(merged_out)
                    if progress_callback:
                        progress_callback("✅ 已成功拦截并强制作废AI时间轴，使用本地精准时间轴完成拼接！")
                else:
                    if progress_callback:
                        progress_callback(f"⚠️ 注意: AI返回的段落数({len(polished_blocks)})与原文件({len(raw_blocks)})不一致，保留AI完整输出。")
            except Exception as parse_e:
                if progress_callback:
                    progress_callback(f"⚠️ 时间轴缝合过程出现异常: {parse_e}，直接使用AI返回结果。")
                    
            with open(output_srt_path, "w", encoding="utf-8") as f:
                f.write(polished_text + "\n")
            if progress_callback:
                progress_callback("✅ 智能润色完成，文案质量已大幅提升！")
                
    except Exception as e:
        if progress_callback:
            progress_callback(f"⚠️ 大模型润色遇到问题，已回退使用原始识别字幕: {str(e)}")

def generate_srt(audio_path: str, tmp_dir: str, model_name: str, api_key: str, base_url: str, subtitle_lang: str = "自动检测 (Auto)", max_chars: str = "30", progress_callback=None, llm_model_name: str = None, video_hash: str = None) -> str:
    """使用 Faster-Whisper 生成精确时间轴 SRT 字幕"""
    if progress_callback:
        progress_callback(f"正在加载 {model_name} 模型 (初次加载可能需要下载)...")
        
    try:
        import os
        # 针对国内网络环境，设置 HuggingFace 镜像站，防止 429 或连接超时
        os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
        from faster_whisper import WhisperModel
    except ImportError:
        raise RuntimeError("请先安装 faster-whisper 库：pip install faster-whisper")
        
    import os
    import uuid
    import time
    
    # 语言映射
    lang_code = None
    if "简体中文" in subtitle_lang or "繁体中文" in subtitle_lang:
        lang_code = "zh"
    elif "英文" in subtitle_lang or "English" in subtitle_lang:
        lang_code = "en"
        
    # 模型尺寸映射（兼容旧版本传过来的 "gemini-xxx" 或 "自动智能轮询"）
    whisper_sizes = ["tiny", "base", "small", "medium", "large-v3"]
    real_model_size = "base" # 默认值
    if model_name in whisper_sizes:
        real_model_size = model_name
    
    try:
        max_chars_int = int(max_chars)
    except:
        max_chars_int = 30
        
    try:
        def _download_from_modelscope(size_name, target_dir):
            import requests
            repo_id = f"Systran/faster-whisper-{size_name}"
            files = ["config.json", "model.bin", "tokenizer.json", "vocabulary.txt"]
            os.makedirs(target_dir, exist_ok=True)
            for f in files:
                target_path = os.path.join(target_dir, f)
                if os.path.exists(target_path) and os.path.getsize(target_path) > 0:
                    continue
                if progress_callback:
                    progress_callback(f"   📥 正在从阿里备用节点下载 {f} (请耐心等待)...")
                url = f"https://modelscope.cn/api/v1/models/{repo_id}/repo?Revision=master&FilePath={f}"
                r = requests.get(url, stream=True, timeout=30)
                r.raise_for_status()
                with open(target_path, "wb") as out:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk: out.write(chunk)
                        
        # 先检查本地全局 models 目录是否已经有完整模型，避免重复下载
        import sys
        if getattr(sys, 'frozen', False):
            app_dir = os.path.dirname(sys.executable)
        else:
            app_dir = os.path.dirname(os.path.abspath(__file__))
        ms_dir = os.path.join(app_dir, "models", real_model_size)
        
        try:
            required_files = ["config.json", "model.bin", "tokenizer.json", "vocabulary.txt"]
            has_local_model = True
            for f in required_files:
                fpath = os.path.join(ms_dir, f)
                if not os.path.exists(fpath) or os.path.getsize(fpath) == 0:
                    has_local_model = False
                    break
            
            if not has_local_model:
                _download_from_modelscope(real_model_size, ms_dir)
                
            try:
                model = WhisperModel(ms_dir, device="auto", compute_type="int8")
            except Exception:
                model = WhisperModel(ms_dir, device="cpu", compute_type="int8")
            if progress_callback:
                progress_callback(f"✅ {real_model_size} 模型加载完成，开始识别 (完全本地运行)...")
        except Exception as load_e:
            if progress_callback:
                progress_callback(f"⚠️ ModelScope 节点下载异常，尝试回退官方节点: {str(load_e)}")
            try:
                model = WhisperModel(real_model_size, device="auto", compute_type="int8")
            except Exception:
                model = WhisperModel(real_model_size, device="cpu", compute_type="int8")
            if progress_callback:
                progress_callback(f"✅ {real_model_size} 模型加载完成，开始识别 (完全本地运行)...")
            
        start_time = time.time()
        
        # 增加前置提示词，强制模型输出简体中文，并提供一定的语境，能大幅减少繁体字和幻觉
        prompt = None
        if "简体" in subtitle_lang:
            prompt = "以下是一段普通话的视频字幕，请务必使用简体中文输出："
            
        # vad_filter=True 能极大提升时间戳准确度和静音过滤
        segments, info = model.transcribe(
            audio_path, 
            language=lang_code, 
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500),
            initial_prompt=prompt
        )
        
        if progress_callback:
            detected_lang = info.language
            progress_callback(f"🎙️ 识别到语言: {detected_lang} (概率 {info.language_probability:.2f})，正在生成时间轴...")
            
        def ms_to_time(ms_val):
            ms_val = max(0, int(ms_val))
            h = ms_val // 3600000
            ms_val %= 3600000
            m = ms_val // 60000
            ms_val %= 60000
            s = ms_val // 1000
            ms = ms_val % 1000
            return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
            
        srt_lines = []
        seg_idx = 1
        last_percent = -1
        
        for segment in segments:
            # Whisper segment contains: start, end, text
            start_ms = int(segment.start * 1000)
            end_ms = int(segment.end * 1000)
            text = segment.text.strip()
            
            if not text:
                continue
                
            if progress_callback and info.duration > 0:
                percent = int((segment.end / info.duration) * 100)
                if percent != last_percent and percent % 5 == 0:
                    progress_callback(f"   ⏳ 语音识别进度: {min(100, percent)}% ...")
                    last_percent = percent
                
            # 分割超长文本
            import textwrap
            if max_chars_int > 0 and len(text) > max_chars_int:
                split_texts = textwrap.wrap(text, width=max_chars_int, break_long_words=True)
            else:
                split_texts = [text]
                
            duration_per_line = max(10, (end_ms - start_ms) // len(split_texts)) if len(split_texts) > 0 else 1000
            curr_start = start_ms
            
            for stxt in split_texts:
                curr_end = curr_start + duration_per_line
                srt_lines.append(str(seg_idx))
                srt_lines.append(f"{ms_to_time(curr_start)} --> {ms_to_time(curr_end)}")
                srt_lines.append(stxt)
                srt_lines.append("")
                seg_idx += 1
                curr_start = curr_end
                
        elapsed = time.time() - start_time
        
        if not srt_lines:
            raise ValueError("未能从音频中识别出任何文字。可能是背景音过大或纯音乐。")
            
        sub_dir = os.path.join(tmp_dir, "subtitles")
        os.makedirs(sub_dir, exist_ok=True)
        
        if video_hash:
            base_name = f"subtitles_{video_hash}"
        else:
            base_name = f"subtitles_{uuid.uuid4().hex[:8]}"
        srt_path_local = os.path.join(sub_dir, f"{base_name}_local.srt")
        
        with open(srt_path_local, "w", encoding="utf-8") as f:
            f.write('\n'.join(srt_lines).strip() + "\n")
            
        if progress_callback:
            progress_callback(f"✅ 字幕生成成功！(耗时: {elapsed:.1f}秒)")
            
        if api_key:
            if not llm_model_name or "自动" in llm_model_name:
                llm_model_name = "gemini-2.5-flash"
            srt_path_ai = os.path.join(sub_dir, f"{base_name}_ai.srt")
            polish_srt_with_llm(srt_path_local, srt_path_ai, api_key, base_url, llm_model_name, progress_callback)
            if os.path.exists(srt_path_ai):
                return srt_path_ai
            return srt_path_local
            
        return srt_path_local
        
    except Exception as e:
        if progress_callback:
            progress_callback(f"❌ 生成字幕失败: {str(e)}")
        raise

def burn_subtitles(video_path: str, srt_path: str, style_string: str = "", progress_callback=None) -> str:
    """视频字幕压制 (整合)"""
    if progress_callback:
        progress_callback("正在进行硬字幕压制...")
    
    video_path_obj = Path(video_path)
    output_filename = f"{video_path_obj.stem}_with_sub{video_path_obj.suffix}"
    
    abs_srt_path = Path(srt_path).absolute().as_posix()
    abs_srt_path = abs_srt_path.replace(':', '\\:')
    
    if style_string:
        vf_param = f"subtitles='{abs_srt_path}':force_style='{style_string}'"
    else:
        vf_param = f"subtitles='{abs_srt_path}'"
        
    cmd = [
        get_ffmpeg_path(),
        "-y",
        "-i", video_path,
        "-vf", vf_param,
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-c:a", "copy",
        output_filename
    ]
    
    try:
        result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
        if progress_callback:
            progress_callback(f"✅ 字幕压制成功！已保存为: {output_filename}")
        return str(Path(output_filename).absolute())
    except subprocess.CalledProcessError as e:
        if progress_callback:
            err_msg = e.stderr.decode('utf-8', errors='ignore') if e.stderr else str(e)
            progress_callback(f"❌ 压制字幕失败 FFmpeg 报错信息:\n{err_msg}")
        raise
