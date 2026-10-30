import os
import random
import shutil
import re
from moviepy.editor import VideoFileClip, CompositeVideoClip

def parse_time(time_str):
    """将 SRT 时间戳 '00:00:04,305' 转为秒数 float"""
    h, m, s_ms = time_str.split(':')
    s, ms = s_ms.split(',')
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0

def parse_srt(srt_path):
    """提取 SRT 文件中所有的句子时间段"""
    subtitles = []
    with open(srt_path, 'r', encoding='utf-8') as f:
        content = f.read()
    # 正则匹配时间轴行
    pattern = re.compile(r'(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})')
    matches = pattern.findall(content)
    for start_str, end_str in matches:
        start_time = parse_time(start_str)
        end_time = parse_time(end_str)
        subtitles.append((start_time, end_time))
    return subtitles

def slice_video(input_video, output_dir, needed_duration):
    """步骤一：将源素材视频切碎到指定目录（智能按需裁剪）"""
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir)

    print(f"🎬 [步骤 1/3] 开始处理素材视频 '{input_video}' ...")
    try:
        clip = VideoFileClip(input_video)
    except Exception as e:
        print(f"❌ 加载素材视频失败: {e}")
        return False

    duration = clip.duration
    current_time = 0.0
    index = 1

    # 实际需要裁剪的总长度（取素材真实长度和所需长度的最小值）
    target_duration = min(duration, needed_duration)

    print(f"✂️ 智能测算：只需裁剪约 {target_duration:.1f} 秒素材，正在按需切分...")
    
    while current_time < target_duration:
        chunk_length = random.uniform(5.0, 10.0)
        if current_time + chunk_length > target_duration:
            chunk_length = target_duration - current_time
            
        end_time = current_time + chunk_length
        if chunk_length < 1.0:
            break
            
        sub_clip = clip.subclip(current_time, end_time)
        out_file = os.path.join(output_dir, f"segment_{index:03d}.mp4")
        
        sub_clip.write_videofile(
            out_file, codec="libx264", audio=False, fps=clip.fps, preset="fast", logger=None
        )
        current_time = end_time
        index += 1
        
    clip.close()
    print(f"✅ 素材切片完成！存入临时目录: '{output_dir}/'\n")
    return True

def insert_b_rolls_with_srt(base_video_path, b_roll_dir, srt_path, output_path):
    """步骤二和三：根据 SRT 字幕精准踩点拼接并渲染"""
    print(f"🎬 [步骤 2/3] 加载基础视频 '{base_video_path}' 和字幕 '{srt_path}'...")
    try:
        base_clip = VideoFileClip(base_video_path)
    except Exception as e:
        print(f"❌ 加载基础视频失败: {e}")
        return

    base_size = base_clip.size
    base_fps = base_clip.fps
    
    # 确保文件按生成序号（如 segment_001.mp4）升序排序，以实现真正的顺序插入
    b_roll_files = sorted([os.path.join(b_roll_dir, f) for f in os.listdir(b_roll_dir) if f.endswith('.mp4')])
    if not b_roll_files:
        print("❌ 未在目录中找到切片素材！")
        return
        
    b_roll_clips = [VideoFileClip(f) for f in b_roll_files]
    
    # 核心：读取字幕时间轴
    subtitles = parse_srt(srt_path)
    overlay_clips = []
    
    print(f"🎯 成功解析到 {len(subtitles)} 句字幕，开始进行智能踩点排版...")
    
    covered_count = 0
    b_roll_index = 0  # 追踪当前该使用哪一个切片
    # 防止连续两句话都插 B-roll 导致画面太碎，加一个标志位
    just_inserted = False 
    
    for i, (start_t, end_t) in enumerate(subtitles):
        sentence_duration = end_t - start_t
        
        # 优雅过滤算法：
        # 1. 句子长度必须大于 2 秒（太短闪过去刺眼）
        # 2. 上一句话如果插过了，这句话就不插（留白给幻灯片）
        # 3. 只有大约 40% 的概率选中
        if sentence_duration > 2.0 and not just_inserted and random.random() < 0.4:
            
            # 按顺序获取切片，如果超出总量则利用取模(%)自动循环回到第一个
            src_clip = b_roll_clips[b_roll_index % len(b_roll_clips)]
            b_roll_index += 1
            
            # 为了防止超过素材长度，取最小值
            actual_duration = min(sentence_duration, src_clip.duration)
            
            # 按顺序使用时，从该切片的第0秒开始，保持画面连贯性
            clip_start = 0.0
            
            # 精准切出和这句话一样长的素材
            sub_clip = src_clip.subclip(clip_start, clip_start + actual_duration)
            
            # 设置时间、尺寸，并添加极其优雅的 0.5秒 淡入淡出特效
            sub_clip = (sub_clip.resize(newsize=base_size)
                                .set_start(start_t)
                                .crossfadein(0.5)
                                .crossfadeout(0.5))
            
            overlay_clips.append(sub_clip)
            covered_count += 1
            just_inserted = True
            
            print(f"   [✨ 命中] 第 {i+1} 句 | 时段 {start_t:.1f}s - {end_t:.1f}s | 优雅插入动态画面")
        else:
            just_inserted = False

    print(f"\n🚀 [步骤 3/3] 踩点排版完毕！共完美覆盖了 {covered_count} 句话。开始合成最终视频！")
    
    # 将基础视频和所有踩点特效视频合并
    final_video = CompositeVideoClip([base_clip] + overlay_clips)
    
    final_video.write_videofile(
        output_path, 
        codec="libx264", 
        audio_codec="aac", 
        fps=base_fps,
        threads=4,
        preset='medium'
    )
    
    print(f"\n🎉 优雅大作完成！全自动混剪视频已保存至: {output_path}")
    
    base_clip.close()
    for c in b_roll_clips:
        c.close()

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🚀 AutoCutVideo 混剪脚本 v3.0 (智能 SRT 踩点版)")
    print("="*60 + "\n")

    # 配置你的文件路径 (极致规范化)
    BASE1 = "base1.mp4"                   # 基础视频
    BASE2 = "base2.mp4"                   # 素材视频
    B_ROLL_DIR = "base2"                  # 素材缓存
    SRT_FILE = "base1.srt"                # 基础视频对应的字幕
    OUTPUT_VIDEO = "out_base1.mp4"        # 输出的新名字
    
    if not os.path.exists(BASE1):
        print(f"❌ 找不到基础视频: {BASE1}")
    elif not os.path.exists(BASE2):
        print(f"❌ 找不到素材视频: {BASE2}")
    elif not os.path.exists(SRT_FILE):
        print(f"❌ 找不到字幕文件: {SRT_FILE}")
    else:
        # 智能侦测：先获取 base1 的时长
        print(f"🔍 智能侦测：正在评估 '{BASE1}' 所需的弹药量...")
        with VideoFileClip(BASE1) as b1_clip:
            base1_duration = b1_clip.duration
            
        # 准备 1.5 倍的 B-roll 素材就绝对够用了（保证有一定随机挑选的余地）
        needed_b_roll_duration = base1_duration * 1.5
        
        # 1. 按需自动切片
        success = slice_video(BASE2, B_ROLL_DIR, needed_b_roll_duration)
        
        # 2. 结合 SRT 智能踩点合成
        if success:
            insert_b_rolls_with_srt(BASE1, B_ROLL_DIR, SRT_FILE, OUTPUT_VIDEO)
