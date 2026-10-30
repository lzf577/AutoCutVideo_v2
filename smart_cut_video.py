import os
import json
import subprocess
import shutil
import imageio_ffmpeg

def parse_time(time_str):
    # e.g. "00:00:03,440" -> seconds (float)
    h, m, s_ms = time_str.split(':')
    s, ms = s_ms.split(',')
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0

def get_ffmpeg_path():
    try:
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"

from moviepy.editor import VideoFileClip, concatenate_videoclips

def cut_video(source_video, json_path, output_video):
    if not os.path.exists(json_path):
        print(f"找不到字幕数据文件: {json_path}")
        return
        
    if not os.path.exists(source_video):
        print(f"找不到源视频文件: {source_video}")
        return

    with open(json_path, 'r', encoding='utf-8') as f:
        kept_subtitles = json.load(f)

    if not kept_subtitles:
        print("没有需要保留的片段。")
        return
    
    PADDING_START = 0.15  # 往前多保留 0.15 秒
    PADDING_END = 0.2     # 往后多保留 0.2 秒
    MIN_DELETE_GAP = 15.0 # 方案A：如果两句废话之间的间隔小于 15 秒，强行保留，不切！

    # 合并相邻或有重叠的时间段
    merged_segments = []
    for sub in kept_subtitles:
        t_start, t_end = sub['timestamp'].split(" --> ")
        start_sec = max(0.0, parse_time(t_start) - PADDING_START)
        end_sec = parse_time(t_end) + PADDING_END
        
        if not merged_segments:
            merged_segments.append([start_sec, end_sec])
        else:
            last_segment = merged_segments[-1]
            # 方案A：容忍度调大，小于 MIN_DELETE_GAP 秒的废话片段被忽略（合并保留）
            if start_sec - last_segment[1] <= MIN_DELETE_GAP:
                last_segment[1] = max(last_segment[1], end_sec)
            else:
                merged_segments.append([start_sec, end_sec])
                
    print(f"\n【方案A：大块切除分析】")
    print(f"原始保留 {len(kept_subtitles)} 句。")
    print(f"设定废话容忍度为 {MIN_DELETE_GAP} 秒。")
    print(f"合并后，总计只需切出 {len(merged_segments)} 个大片段。")
    
    total_kept_duration = sum(seg[1] - seg[0] for seg in merged_segments)
    print(f"合并后预计总时长: {total_kept_duration:.2f} 秒\n")
    
    print("加载源视频...")
    video = VideoFileClip(source_video)
    
    import numpy as np
    import moviepy.audio.fx.all as afx
    
    def make_black(img):
        return np.zeros_like(img)

    clips = []
    for i, segment in enumerate(merged_segments):
        start_sec = segment[0]
        end_sec = min(segment[1], video.duration)
        print(f"[{i+1}/{len(merged_segments)}] 正在截取: {start_sec:.3f}s -> {end_sec:.3f}s")
        # 截取片段
        clip = video.subclip(start_sec, end_sec)
        clips.append(clip)
        
        # 在片段之间插入 0.5秒 的黑屏+静音过渡（如果是最后一个片段则不加）
        if i < len(merged_segments) - 1:
            print(f"  -> 插入 0.5 秒静音黑屏过渡")
            # 巧妙的做法：直接截取原视频 0.5 秒，将画面变黑，声音变零
            transition = video.subclip(0, 0.5).fl_image(make_black).fx(afx.volumex, 0.0)
            clips.append(transition)
            
    print("正在无缝拼接所有片段...")
    final_video = concatenate_videoclips(clips)
    
    print("开始渲染导出最终视频 (这可能需要一些时间)...")
    final_video.write_videofile(
        output_video,
        codec="libx264",
        audio_codec="aac",
        temp_audiofile="temp-audio.m4a",
        remove_temp=True,
        fps=video.fps,
        logger=None # 隐藏进度条以避免命令行编码问题
    )
    
    # 释放资源
    video.close()
    for c in clips:
        c.close()
    final_video.close()
    
    print(f"合并完成！最终视频输出为: {output_video}")

if __name__ == "__main__":
    source = r"z:\01体彩赛事\7.25赛事\芬超-瑞典超数据\雅罗vs塞伊奈_韦斯特罗斯vs厄尔格里特.mp4"
    json_path = "subtitles_kept.json"
    output = "精简版_视频.mp4"
    
    cut_video(source, json_path, output)
