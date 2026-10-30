import re

with open('d:\\AutoCutVideo_v2\\timeline_renderer.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace block 1: Remove moviepy logic
block1_regex = re.compile(r'    # ----------------------------------------------------\n    # 0\. 预处理：合成辅助视频 \(B-Roll\) 层\n    # ----------------------------------------------------\n.*?    # ----------------------------------------------------\n    # 1\. 导出 SRT \(将字幕轨道重新组装为 SRT 文件\)', re.DOTALL)

content = block1_regex.sub('    # ----------------------------------------------------\\n    # 1. 导出 SRT (将字幕轨道重新组装为 SRT 文件)', content)

# Replace block 2: Add broll collection and filtergraph
block2_target = '''    inputs = ["-i", video_path]
    
    # 这里如果有额外的音频轨，可以加上，但当前主视频自带音频，简单起见如果Audio为空则用原声。
    # TODO: 若用户分离了音频轨，则需要 -i 音频文件并 -map
    
    # 收集图片轨道片段
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
    
    current_stream_idx = 1 # 0 is main video'''

block2_replacement = '''    inputs = ["-i", video_path]
    
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
            prev_label = cur_label'''

content = content.replace(block2_target, block2_replacement)

with open('d:\\AutoCutVideo_v2\\timeline_renderer.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Replacement done.")
