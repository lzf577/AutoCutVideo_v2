import os
import subprocess
import re
import math
from typing import Callable
from pathlib import Path
from timeline_model import Timeline, TrackType
from cover_templates import COVER_TEMPLATES

def get_ffmpeg_path():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"

def _time_to_srt_format(ms: int) -> str:
    h = ms // 3600000; ms %= 3600000
    m = ms // 60000;   ms %= 60000
    s = ms // 1000;    ms %= 1000
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def get_video_dimensions(video_path: str):
    import re
    import json
    
    # 首选方案：尝试使用 ffmpeg 直接获取分辨率，因为有些环境（如 imageio_ffmpeg）可能没有附带 ffprobe
    ffmpeg = get_ffmpeg_path()
    try:
        result = subprocess.run(
            [ffmpeg, "-i", video_path],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        output = result.stderr.decode("utf-8", errors="ignore")
        match = re.search(r"Video:.*?(\d{3,})x(\d{3,})", output)
        if match:
            return int(match.group(1)), int(match.group(2))
    except Exception:
        pass

    # 备选方案：尝试使用 ffprobe 获取精确 json
    ffprobe = ffmpeg.replace("ffmpeg", "ffprobe")
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
        
    return 1920, 1080

def generate_text_overlay_png(vw: int, vh: int, cover_title: str, cover_subtitle: str,
                              font_path: str, cover_title_y: int, cover_spacing: int, 
                              cover_title_scale: int, cover_subtitle_scale: int, tmp_dir: str, 
                              cover_template: str, custom_title_style: str, custom_subtitle_style: str) -> str:
    from PIL import Image, ImageFont, ImageDraw
    import emoji
    import os
    
    img = Image.new("RGBA", (vw, vh), (0, 0, 0, 0))
    
    if cover_template == "custom":
        t_style = custom_title_style if custom_title_style else r"fontcolor=white:fontsize=min(w\,h)/8"
        s_style = custom_subtitle_style if custom_subtitle_style else r"fontcolor=white:fontsize=min(w\,h)/15"
    else:
        tmpl = COVER_TEMPLATES.get(cover_template, COVER_TEMPLATES["classic_white_yellow"])
        t_style = tmpl.get("title_style", r"fontcolor=white:fontsize=min(w\,h)/8")
        s_style = tmpl.get("subtitle_style", r"fontcolor=yellow:fontsize=min(w\,h)/15")
        
    def parse_style(style_str, scale_percent):
        from PIL import ImageColor
        def resolve_color(c_str):
            if not c_str: return 'black'
            alpha = 255
            if '@' in c_str:
                parts = c_str.split('@')
                c_str = parts[0]
                try: alpha = int(float(parts[1]) * 255)
                except: pass
            try:
                rgb = ImageColor.getrgb(c_str)
                if len(rgb) == 3: return rgb + (alpha,)
                elif len(rgb) == 4: return rgb[:3] + (alpha,)
                return rgb
            except: return c_str

        style = {
            'color': resolve_color('white'),
            'size': min(vw, vh) // 10,
            'stroke_width': 0,
            'stroke_fill': resolve_color('black'),
            'shadow_x': 0,
            'shadow_y': 0,
            'shadow_color': resolve_color('black'),
            'box': False,
            'box_color': resolve_color('black'),
            'box_borderw': 0
        }
        min_wh = min(vw, vh)
        for part in style_str.split(':'):
            part = part.strip()
            if not part or '=' not in part: continue
            k, v = part.split('=', 1)
            if k == 'fontcolor': style['color'] = resolve_color(v)
            elif k == 'fontsize':
                s_expr = v.replace(r'min(w\,h)', str(min_wh)).replace(r'min(w,h)', str(min_wh))
                try: style['size'] = int(eval(s_expr))
                except: pass
            elif k == 'borderw':
                try: style['stroke_width'] = int(v)
                except: pass
            elif k == 'bordercolor': style['stroke_fill'] = resolve_color(v)
            elif k == 'shadowx':
                try: style['shadow_x'] = int(v)
                except: pass
            elif k == 'shadowy':
                try: style['shadow_y'] = int(v)
                except: pass
            elif k == 'shadowcolor': style['shadow_color'] = resolve_color(v)
            elif k == 'box': style['box'] = (v == '1')
            elif k == 'boxcolor': style['box_color'] = resolve_color(v)
            elif k == 'boxborderw':
                try: style['box_borderw'] = int(v)
                except: pass
                
        # Apply scaling
        scale_factor = scale_percent / 100.0
        style['size'] = max(1, int(style['size'] * scale_factor))
        style['stroke_width'] = max(0, int(style['stroke_width'] * scale_factor))
        style['shadow_x'] = int(style['shadow_x'] * scale_factor)
        style['shadow_y'] = int(style['shadow_y'] * scale_factor)
        style['box_borderw'] = max(0, int(style['box_borderw'] * scale_factor))
        
        return style
        
    t_style_dict = parse_style(t_style, cover_title_scale)
    s_style_dict = parse_style(s_style, cover_subtitle_scale)
    
    real_font_path = font_path.replace("C\\:", "C:")
    if not os.path.exists(real_font_path):
        real_font_path = "C:/Windows/Fonts/msyhbd.ttc"
        if not os.path.exists(real_font_path):
            real_font_path = "C:/Windows/Fonts/simhei.ttf"

    t_font = ImageFont.truetype(real_font_path, t_style_dict['size'])
    s_font = ImageFont.truetype(real_font_path, s_style_dict['size'])
    
    emoji_font_path = "C:/Windows/Fonts/seguiemj.ttf"
    if not os.path.exists(emoji_font_path):
        emoji_font_path = real_font_path
        
    t_font_emoji = ImageFont.truetype(emoji_font_path, t_style_dict['size'])
    s_font_emoji = ImageFont.truetype(emoji_font_path, s_style_dict['size'])
    
    draw = ImageDraw.Draw(img)
    
    def tokenize_text(text):
        res = []
        emoji_list = emoji.emoji_list(text)
        last = 0
        for e in emoji_list:
            start, end = e['match_start'], e['match_end']
            if start > last:
                res.append({"type": "text", "text": text[last:start]})
            res.append({"type": "emoji", "text": text[start:end]})
            last = end
        if last < len(text):
            res.append({"type": "text", "text": text[last:]})
        return res

    def measure_mixed_text(text, font_main, font_emoji):
        total_w = 0
        for t in tokenize_text(text):
            if t["type"] == "emoji":
                total_w += draw.textlength(t["text"], font=font_emoji)
            else:
                total_w += draw.textlength(t["text"], font=font_main)
        return total_w

    def draw_line(line, font_main, font_emoji, style_dict, y):
        text_w = measure_mixed_text(line, font_main, font_emoji)
        x = (vw - text_w) / 2
        
        # 1. Draw box if needed
        if style_dict['box']:
            bw = style_dict['box_borderw']
            h = style_dict['size']
            draw.rectangle(
                [x - bw, y - bw, x + text_w + bw, y + h + bw],
                fill=style_dict['box_color']
            )
            
        # 2. Draw shadow if needed
        sx = style_dict['shadow_x']
        sy = style_dict['shadow_y']
        
        # We will use left-middle anchor for perfect emoji-text vertical alignment
        draw_y = y + style_dict['size'] // 2
        emoji_y_shift = int(style_dict['size'] * 0.08) # Visual correction for Segoe UI Emoji
        
        if sx != 0 or sy != 0:
            cx = x + sx
            cy = draw_y + sy
            for t in tokenize_text(line):
                f = font_emoji if t["type"] == "emoji" else font_main
                if t["type"] != "emoji":
                    draw.text((cx, cy), t["text"], font=f, fill=style_dict['shadow_color'], anchor="lm")
                cx += draw.textlength(t["text"], font=f)
                
        # 3. Draw actual text (with stroke)
        cx = x
        for t in tokenize_text(line):
            f = font_emoji if t["type"] == "emoji" else font_main
            if t["type"] == "emoji":
                draw.text((cx, draw_y + emoji_y_shift), t["text"], font=f, embedded_color=True, anchor="lm")
            else:
                draw.text((cx, draw_y), t["text"], font=f, fill=style_dict['color'],
                          stroke_width=style_dict['stroke_width'], stroke_fill=style_dict['stroke_fill'], anchor="lm")
            cx += draw.textlength(t["text"], font=f)

    title_lines_count = 0
    title_total_h = 0
    if cover_title:
        lines = [line for line in cover_title.split('\n') if line.strip()]
        title_lines_count = len(lines)
        for i, line in enumerate(lines):
            y = int(vh * cover_title_y / 100 + i * (t_style_dict['size'] * 1.2))
            draw_line(line, t_font, t_font_emoji, t_style_dict, y)
        title_total_h = title_lines_count * (t_style_dict['size'] * 1.2)
            
    if cover_subtitle:
        lines = [line for line in cover_subtitle.split('\n') if line.strip()]
        for i, line in enumerate(lines):
            y = int(vh * cover_title_y / 100 + title_total_h + vh * cover_spacing / 100 + i * (s_style_dict['size'] * 1.2))
            draw_line(line, s_font, s_font_emoji, s_style_dict, y)
            
    output_png = os.path.join(tmp_dir, "cover_text_overlay.png")
    img.save(output_png)
    return output_png

def render_timeline(timeline: Timeline, output_path: str, tmp_dir: str, subtitle_style: str = "", hw_accel: str = "auto", trim_start_s: int = 0, trim_end_s: int = 2, cover_path: str = "", cover_duration: float = 0.5, broll_transition: str = "random", cover_title: str = "", cover_subtitle: str = "", cover_font: str = "微软雅黑(加粗)", cover_template: str = "classic_white_yellow", cover_custom_title: str = "", cover_custom_subtitle: str = "", cover_title_y: int = 50, cover_spacing: int = 2, cover_title_scale: int = 100, cover_subtitle_scale: int = 100, progress_callback=None) -> str:
    """
    将 Timeline 数据模型编译为最终的 FFmpeg 命令并执行。
    """
    if progress_callback:
        progress_callback("🎬 正在准备渲染轨道...")
        
    ffmpeg = get_ffmpeg_path()
    
    # 提取各轨道数据
    video_tracks = timeline.get_tracks_by_type(TrackType.VIDEO)
    image_tracks = timeline.get_tracks_by_type(TrackType.IMAGE)
    logo_tracks = timeline.get_tracks_by_type(TrackType.LOGO)
    subtitle_tracks = timeline.get_tracks_by_type(TrackType.SUBTITLE)
    audio_tracks = timeline.get_tracks_by_type(TrackType.AUDIO)
    
    # 目前假设只有一个主视频作为底轨
    main_video_clip = None
    if video_tracks and video_tracks[0].clips:
        main_video_clip = video_tracks[0].clips[0]
        
    if not main_video_clip:
        raise ValueError("时间轴上没有主视频轨！")
        
    # 获取主视频的真实分辨率
    video_path = main_video_clip.source_path
    vw, vh = get_video_dimensions(video_path)

    # ----------------------------------------------------
    # 1. 导出 SRT (将字幕轨道重新组装为 SRT 文件)
    # ----------------------------------------------------
    srt_path = None
    if subtitle_tracks and subtitle_tracks[0].clips:
        srt_path = os.path.join(tmp_dir, "render_temp_subtitles.srt")
        with open(srt_path, "w", encoding="utf-8") as f:
            for idx, clip in enumerate(subtitle_tracks[0].clips):
                start_str = _time_to_srt_format(clip.start_time)
                end_str = _time_to_srt_format(clip.end_time)
                f.write(f"{idx+1}\n")
                f.write(f"{start_str} --> {end_str}\n")
                f.write(f"{clip.source_path}\n\n") # source_path 存的是文字
                
    # ----------------------------------------------------
    # 2. 构建 FFmpeg 输入和 Filtergraph (处理图片覆盖)
    # ----------------------------------------------------
    inputs = []
    if hw_accel != "libx264":
        inputs.extend(["-hwaccel", "auto"])
    inputs.extend(["-i", video_path])
    
    # 这里如果有额外的音频轨，可以加上，但当前主视频自带音频，简单起见如果Audio为空则用原声。
    # TODO: 若用户分离了音频轨，则需要 `-i` 音频文件并 `-map`
    
    # 收集所有片段
    broll_clips = []
    broll_tracks = timeline.get_tracks_by_type(TrackType.BROLL)
    if broll_tracks:
        for track in broll_tracks:
            broll_clips.extend(track.clips)

    image_clips = []
    if image_tracks:
        for track in image_tracks:
            image_clips.extend(track.clips)
            
    logo_clips = []
    if logo_tracks:
        for track in logo_tracks:
            logo_clips.extend(track.clips)
            
    filter_parts = []
    prev_label = "0:v"
    
    current_stream_idx = 1 # 0 is main video
    
    # ----------------------------------------------------
    # 插入 B-Roll (辅助视频)
    # ----------------------------------------------------
    if broll_clips:
        import random
        from pathlib import Path
        if progress_callback:
            progress_callback(f"🎬 准备通过 FFmpeg 极速混合 {len(broll_clips)} 个辅助画面 (B-Roll)...")
            
        for idx, clip in enumerate(broll_clips):
            start_s = clip.start_time / 1000.0
            actual_duration_s = clip.duration / 1000.0
            clip_start_s = clip.meta.get("broll_start", 0)
            
            abs_broll = Path(clip.source_path).absolute().as_posix()
            inputs.extend(["-ss", f"{clip_start_s:.3f}", "-t", f"{actual_duration_s:.3f}", "-i", abs_broll])
            
            broll_idx = current_stream_idx
            current_stream_idx += 1
            
            if broll_transition == "random":
                transition = random.choice(["smooth", "fast", "hard", "slow", "fade_black"])
            else:
                transition = broll_transition
                
            fade_d = 0.5
            if transition == "fast": fade_d = 0.2
            elif transition == "slow": fade_d = 0.8
            elif transition == "hard": fade_d = 0.0
            elif transition == "fade_black": fade_d = 0.5
            
            broll_scaled = f"broll_scaled_{idx}"
            if transition == "fade_black":
                fade_filter = ""
                if fade_d > 0:
                    fade_filter = f",fade=t=in:st=0:d={fade_d},fade=t=out:st={max(0, actual_duration_s - fade_d):.3f}:d={fade_d}"
                filter_parts.append(
                    f"[{broll_idx}:v]scale={vw}:{vh}:force_original_aspect_ratio=increase,crop={vw}:{vh},setsar=1,format=yuv420p{fade_filter},setpts=PTS-STARTPTS+{start_s:.3f}/TB[{broll_scaled}]"
                )
            else:
                fade_filter = ",format=yuva420p"
                if fade_d > 0:
                    fade_filter += f",fade=t=in:st=0:d={fade_d}:alpha=1,fade=t=out:st={max(0, actual_duration_s - fade_d):.3f}:d={fade_d}:alpha=1"
                filter_parts.append(
                    f"[{broll_idx}:v]scale={vw}:{vh}:force_original_aspect_ratio=increase,crop={vw}:{vh},setsar=1{fade_filter},setpts=PTS-STARTPTS+{start_s:.3f}/TB[{broll_scaled}]"
                )
                
            cur_label = f"broll_overlay_{idx}"
            end_s = start_s + actual_duration_s
            filter_parts.append(
                f"[{prev_label}][{broll_scaled}]overlay=enable='between(t,{start_s:.3f},{end_s:.3f})':eof_action=pass[{cur_label}]"
            )
            prev_label = cur_label
    
    if image_clips:
        if progress_callback:
            progress_callback(f"🖼️ 共有 {len(image_clips)} 个图片覆盖效果需要渲染...")
            
        # 优化点：生成全局统一的背景变暗逻辑，避免每一层插图都套用一次变暗滤镜导致性能暴跌
        # 既然图片已经全屏铺满了，如果你不希望背景变暗可以去掉这段。这里暂且保留作为转场或半透明层备用。
        enable_exprs = []
        for clip in image_clips:
            start_s = clip.start_time / 1000.0
            end_s = clip.end_time / 1000.0
            enable_exprs.append(f"between(t,{start_s:.3f},{end_s:.3f})")
            
        combined_enable = "+".join(enable_exprs)
        bg_dark = "bg_dark"
        
        # 将原视频在所有需要的插图时间段统一压暗
        filter_parts.append(
            f"[{prev_label}]colorchannelmixer=rr=0.3:gg=0.3:bb=0.3:"
            f"enable='{combined_enable}'[{bg_dark}]"
        )
        prev_label = bg_dark
            
        for idx, clip in enumerate(image_clips):
            stream_idx = current_stream_idx
            current_stream_idx += 1
            start_s = clip.start_time / 1000.0
            end_s = clip.end_time / 1000.0
            clip_duration = end_s - start_s
            
            # 优化：只生成该片段所需时长的图片流，而不是整个视频时长
            inputs += ["-loop", "1", "-t", f"{clip_duration:.3f}", "-i", clip.source_path]
            
            cur_label = f"v{idx + 1}"
            scaled = f"scaled{idx + 1}"
            # 1. 自动计算原视频长宽比和图片的长宽比
            try:
                from PIL import Image
                with Image.open(clip.source_path) as img:
                    iw, ih = img.size
            except Exception:
                # 兼容性后备方案，如果读取失败再尝试之前的逻辑
                iw, ih = get_video_dimensions(clip.source_path)
                
            video_ratio = vw / vh
            image_ratio = iw / ih
            
            # 2. 得出最终的计算比例 (去除了原本的5%余量，让图片能全屏铺满)
            safe_margin = 1.0 
            if image_ratio > video_ratio:
                # 图片的长宽比更大（偏宽），以屏幕宽度为基准计算最终高度，保证宽度不溢出
                target_w = int(vw * safe_margin)
                target_h = int(target_w / image_ratio)
            else:
                # 图片的长宽比更小（偏高），以屏幕高度为基准计算最终宽度，保证高度不溢出
                target_h = int(vh * safe_margin)
                target_w = int(target_h * image_ratio)
                
            # 确保最终宽高是偶数，防止某些编码器报错
            target_w = target_w - (target_w % 2)
            target_h = target_h - (target_h % 2)
            
            # 3. 把咱们精确计算的绝对宽高交给 FFmpeg 缩放
            filter_parts.append(
                f"[{stream_idx}:v]scale={target_w}:{target_h},"
                f"setsar=1,setpts=PTS-STARTPTS+{start_s:.3f}/TB[{scaled}]"
            )
            
            # 居中覆盖
            filter_parts.append(
                f"[{prev_label}][{scaled}]overlay=(W-w)/2:(H-h)/2:"
                f"enable='between(t,{start_s:.3f},{end_s:.3f})':eof_action=pass[{cur_label}]"
            )
            prev_label = cur_label

    # 加入 Logo Clips
    if logo_clips:
        if progress_callback:
            progress_callback(f"🌟 正在添加 {len(logo_clips)} 个视频Logo...")
            
        for idx, clip in enumerate(logo_clips):
            logo_path = clip.source_path
            if not os.path.exists(logo_path):
                continue
                
            start_s = clip.start_time / 1000.0
            end_s = clip.end_time / 1000.0
            clip_duration = end_s - start_s
            abs_logo = Path(logo_path).absolute().as_posix()
            logo_suffix = Path(logo_path).suffix.lower()
            if logo_suffix in (".mp4", ".mov", ".webm", ".avi", ".mkv"):
                inputs.extend(["-stream_loop", "-1", "-t", f"{clip_duration:.3f}", "-i", abs_logo])
            else:
                inputs.extend(["-loop", "1", "-t", f"{clip_duration:.3f}", "-i", abs_logo])
            
            logo_idx = current_stream_idx
            current_stream_idx += 1
            
            logo_x_val = clip.meta.get("x", 0)
            logo_y_val = clip.meta.get("y", 0)
            logo_scale_val = clip.meta.get("scale", 100)
            
            # 以右下角为基准0坐标：W-w 减去横向边距，H-h 减去纵向边距
            logo_x = f"W-w-{logo_x_val}"
            logo_y = f"H-h-{logo_y_val}"
            
            logo_label = f"v_with_logo_{idx}"
            
            enable_str = f":enable='between(t,{start_s:.3f},{end_s:.3f})'"
                
            if logo_scale_val != 100:
                scaled_logo_label = f"logo_scaled_{idx}"
                scale_factor = float(logo_scale_val) / 100.0
                filter_parts.append(
                    f"[{logo_idx}:v]scale=trunc(iw*{scale_factor}):trunc(ih*{scale_factor})[{scaled_logo_label}]"
                )
                filter_parts.append(
                    f"[{prev_label}][{scaled_logo_label}]overlay={logo_x}:{logo_y}{enable_str}[{logo_label}]"
                )
            else:
                filter_parts.append(
                    f"[{prev_label}][{logo_idx}:v]overlay={logo_x}:{logo_y}{enable_str}[{logo_label}]"
                )
            prev_label = logo_label

    # 加入字幕 (在最顶层)
    if srt_path:
        if progress_callback:
            progress_callback("📝 正在应用字幕硬编码...")
        abs_srt = Path(srt_path).absolute().as_posix().replace(':', '\\:')
        sub_label = "v_out"
        if style_string := subtitle_style:
            filter_parts.append(f"[{prev_label}]subtitles='{abs_srt}':force_style='{style_string}'[{sub_label}]")
        else:
            filter_parts.append(f"[{prev_label}]subtitles='{abs_srt}'[{sub_label}]")
        prev_label = sub_label

    audio_label = "0:a"
    
    # ----------------------------------------------------
    # 处理掐头去尾 (使用 trim 滤镜以支持后续 concat)
    # ----------------------------------------------------
    if trim_start_s > 0 or trim_end_s > 0:
        duration = main_video_clip.duration / 1000.0
        target_to = duration - trim_end_s
        if target_to > trim_start_s:
            v_trim_label = "trimmed_v"
            a_trim_label = "trimmed_a"
            filter_parts.append(f"[{prev_label}]trim=start={trim_start_s}:end={target_to},setpts=PTS-STARTPTS[{v_trim_label}]")
            filter_parts.append(f"[{audio_label}]atrim=start={trim_start_s}:end={target_to},asetpts=PTS-STARTPTS[{a_trim_label}]")
            prev_label = v_trim_label
            audio_label = a_trim_label

    # ----------------------------------------------------
    # 处理视频封面 (使用 concat 拼接在最前面)
    # ----------------------------------------------------
    if cover_path and os.path.exists(cover_path):
        if progress_callback:
            progress_callback("🖼️ 正在处理并拼接视频封面...")
        cover_v_idx = current_stream_idx
        abs_cover = Path(cover_path).absolute().as_posix()
        inputs.extend(["-loop", "1", "-t", f"{cover_duration:.3f}", "-i", abs_cover])
        current_stream_idx += 1
        
        cover_a_idx = current_stream_idx
        inputs.extend(["-f", "lavfi", "-t", f"{cover_duration:.3f}", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"])
        current_stream_idx += 1
        
        cover_scaled_label = "cover_scaled"
        filter_parts.append(f"[{cover_v_idx}:v]scale={vw}:{vh}:force_original_aspect_ratio=increase,crop={vw}:{vh},setsar=1,fps=30[{cover_scaled_label}]")
        
        # --- Add Cover Text ---
        cover_text_label = cover_scaled_label
        
        font_map = {
            "微软雅黑(加粗)": "C:/Windows/Fonts/msyhbd.ttc",
            "微软雅黑": "C:/Windows/Fonts/msyh.ttc",
            "黑体": "C:/Windows/Fonts/simhei.ttf",
            "楷体": "C:/Windows/Fonts/simkai.ttf",
            "宋体": "C:/Windows/Fonts/simsun.ttc"
        }
        font_path = font_map.get(cover_font, "C:/Windows/Fonts/msyhbd.ttc")
        
        if cover_title or cover_subtitle:
            current_cover_label = cover_scaled_label
            
            text_png_path = generate_text_overlay_png(
                vw, vh, cover_title, cover_subtitle, font_path, cover_title_y, cover_spacing, 
                cover_title_scale, cover_subtitle_scale, tmp_dir, 
                cover_template, cover_custom_title, cover_custom_subtitle
            )
            
            text_png_path_ff = text_png_path.replace('\\', '/')
            inputs.extend(["-i", text_png_path_ff])
            
            text_img_idx = current_stream_idx
            current_stream_idx += 1
            
            next_label = "cover_text_applied"
            filter_parts.append(f"[{current_cover_label}][{text_img_idx}:v]overlay=0:0[{next_label}]")
            current_cover_label = next_label
            
            cover_text_label = current_cover_label
        
        main_v_fps_label = "main_v_fps"
        main_a_resampled_label = "main_a_resampled"
        filter_parts.append(f"[{prev_label}]fps=30[{main_v_fps_label}]")
        filter_parts.append(f"[{audio_label}]aformat=sample_rates=44100:channel_layouts=stereo[{main_a_resampled_label}]")
        
        concat_v_label = "v_out_concat"
        concat_a_label = "a_out_concat"
        filter_parts.append(f"[{cover_text_label}][{cover_a_idx}:a][{main_v_fps_label}][{main_a_resampled_label}]concat=n=2:v=1:a=1[{concat_v_label}][{concat_a_label}]")
        
        prev_label = concat_v_label
        audio_label = concat_a_label

    cmd = [ffmpeg, "-y", *inputs]
    
    if filter_parts:
        filter_complex = ";".join(filter_parts)
        cmd.extend(["-filter_complex", filter_complex, "-map", f"[{prev_label}]", "-map", f"[{audio_label}]"])
    else:
        cmd.extend(["-c:v", "copy", "-c:a", "copy"]) # 什么都没有的话直接copy

    base_cmd = cmd.copy()
    
    # 定义编码器尝试列表：优先尝试各大厂商的硬件加速(GPU)，最后保底使用CPU(libx264)
    if hw_accel == "auto":
        encoders = [
            ("h264_qsv", ["-preset", "fast"]),     # Intel 核心显卡加速
            ("h264_nvenc", ["-preset", "fast"]),   # NVIDIA 显卡加速
            ("h264_amf", []),                      # AMD 显卡加速
            ("libx264", ["-preset", "fast", "-crf", "23"])  # 纯 CPU 编码保底
        ]
    elif hw_accel == "libx264":
        encoders = [("libx264", ["-preset", "fast", "-crf", "23"])]
    elif hw_accel == "h264_nvenc":
        encoders = [("h264_nvenc", ["-preset", "fast"]), ("libx264", ["-preset", "fast", "-crf", "23"])]
    elif hw_accel == "h264_amf":
        encoders = [("h264_amf", []), ("libx264", ["-preset", "fast", "-crf", "23"])]
    elif hw_accel == "h264_qsv":
        encoders = [("h264_qsv", ["-preset", "fast"]), ("libx264", ["-preset", "fast", "-crf", "23"])]
    else:
        encoders = [("libx264", ["-preset", "fast", "-crf", "23"])]
    
    if progress_callback:
        progress_callback("⚙️ 开始最终合并与渲染，尝试调用 GPU 硬件加速...")
        
    success = False
    last_err = ""
    
    for vcodec, extra_args in encoders:
        current_cmd = base_cmd + ["-c:v", vcodec] + extra_args + ["-c:a", "aac"]
        current_cmd.append(output_path)
        
        try:
            subprocess.run(current_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
            success = True
            if progress_callback:
                progress_callback(f"🎉 视频渲染成功！(使用了 {vcodec} 编码器)\n文件已保存到：\n{output_path}")
            return output_path
        except subprocess.CalledProcessError as e:
            err = e.stderr.decode('utf-8', errors='ignore')
            if progress_callback:
                progress_callback(f"❌ 渲染失败:\n{err}")
            return f"FFmpeg Error: {err}"
    
def generate_cover_preview(cover_path: str, output_jpg_path: str, tmp_dir: str, video_path: str = "",
                           cover_title: str = "", cover_subtitle: str = "", cover_font: str = "微软雅黑(加粗)", 
                           cover_template: str = "classic_white_yellow", cover_custom_title: str = "", 
                           cover_custom_subtitle: str = "", cover_title_y: int = 50, cover_spacing: int = 2, 
                           cover_title_scale: int = 100, cover_subtitle_scale: int = 100, orientation: str = None) -> bool:
    """生成单帧封面预览"""
    if not cover_path or not os.path.exists(cover_path):
        return False
        
    vw, vh = 1080, 1920 # 默认竖屏
    if orientation == "landscape":
        vw, vh = 1920, 1080
    elif orientation == "portrait":
        vw, vh = 1080, 1920
    elif video_path and os.path.exists(video_path):
        vw, vh = get_video_dimensions(video_path)
        
    # 构建 filter
    filter_parts = []
    cover_scaled_label = "cover_scaled"
    filter_parts.append(f"[0:v]scale={vw}:{vh}:force_original_aspect_ratio=increase,crop={vw}:{vh},setsar=1[{cover_scaled_label}]")
    
    font_map = {
        "微软雅黑(加粗)": "C:/Windows/Fonts/msyhbd.ttc",
        "微软雅黑": "C:/Windows/Fonts/msyh.ttc",
        "黑体": "C:/Windows/Fonts/simhei.ttf",
        "楷体": "C:/Windows/Fonts/simkai.ttf",
        "宋体": "C:/Windows/Fonts/simsun.ttc"
    }
    font_path = font_map.get(cover_font, "C:/Windows/Fonts/msyhbd.ttc")
    
    current_cover_label = cover_scaled_label
    extra_inputs = []
    
    if cover_title or cover_subtitle:
        text_png_path = generate_text_overlay_png(
            vw, vh, cover_title, cover_subtitle, font_path, cover_title_y, cover_spacing, 
            cover_title_scale, cover_subtitle_scale, tmp_dir, 
            cover_template, cover_custom_title, cover_custom_subtitle
        )
        
        text_png_path_ff = text_png_path.replace('\\', '/')
        extra_inputs.extend(["-i", text_png_path_ff])
        
        next_label = "cover_text_applied"
        filter_parts.append(f"[{current_cover_label}][1:v]overlay=0:0[{next_label}]")
        current_cover_label = next_label
            
    filter_complex = ";".join(filter_parts)
    
    ffmpeg_cmd = [
        get_ffmpeg_path(),
        "-y",
        "-i", Path(cover_path).absolute().as_posix()
    ]
    ffmpeg_cmd.extend(extra_inputs)
    ffmpeg_cmd.extend([
        "-filter_complex", filter_complex,
        "-map", f"[{current_cover_label}]",
        "-vframes", "1",
        output_jpg_path
    ])
    
    try:
        subprocess.run(ffmpeg_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg Preview Error: {e.stderr.decode('utf-8', errors='ignore')}")
        return False
