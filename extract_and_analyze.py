import os
import google.generativeai as genai
from dotenv import load_dotenv
from moviepy.editor import VideoFileClip

def extract_frames(video_path, output_dir, interval=15):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    print(f"Extracting frames every {interval} seconds from {video_path}...")
    clip = VideoFileClip(video_path)
    duration = clip.duration
    
    frame_paths = []
    for t in range(0, int(duration), interval):
        frame_path = os.path.join(output_dir, f"frame_{t:03d}.jpg")
        clip.save_frame(frame_path, t=t)
        frame_paths.append(frame_path)
        print(f"Saved {frame_path}")
        
    clip.close()
    return frame_paths

def analyze_frames(frame_paths, api_key):
    genai.configure(api_key=api_key)
    
    print("Uploading frames to Gemini...")
    uploaded_files = []
    for path in frame_paths:
        f = genai.upload_file(path=path)
        uploaded_files.append(f)
        
    model = genai.GenerativeModel(model_name="models/gemini-2.5-flash")
    
    prompt = """
    你现在是一个专业的短视频/PPT视觉设计师，以及AI提示词工程师。
    这些图片是从一个由Google NotebookLM / Studio引擎自动生成的体育赛事分析视频中，每隔15秒截取的一张画面。
    用户反馈：“画面风格很难看，太死板，文字不够大。”

    请仔细观察这些截图的视觉设计排版。
    请输出以下分析：
    1. 【当前视觉风格诊断】：详细描述当前画面的呆板和难看体现在哪里？文字大小是否足够应对手机缩放？视觉上缺乏哪些生动感？
    2. 【提示词重塑建议】：基于用户的需求（再生动一点、好看一点、字体再大一点），我应该如何在提示词中增加具有极高“画面表现力”的指令？
    给出具体可直接替换到我的系统提示词（如背景描述、图表动效、字体夸张程度、排版布局等）中的强力约束词和段落。
    """
    
    print("Analyzing frames with Gemini 2.5 Flash...")
    # Pass prompt and all uploaded files to the model
    contents = [prompt] + uploaded_files
    response = model.generate_content(contents)
    
    print("\n--- ANALYSIS RESULT ---\n")
    print(response.text)
    
    with open("video_visual_analysis.txt", "w", encoding="utf-8") as f:
        f.write(response.text)
        
    print("Cleaning up uploaded files...")
    for f in uploaded_files:
        try:
            genai.delete_file(f.name)
        except:
            pass

if __name__ == "__main__":
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    video_path = r"d:\提示词调教\内部模型测试版_V.1.0.mp4"
    output_dir = "extracted_frames"
    
    if not os.path.exists(video_path):
        print(f"Error: Video file not found at {video_path}")
        # Try the other path just in case
        alt_path = r"d:\Users\lzf\Downloads\内部模型测试版_V.1.0.mp4"
        if os.path.exists(alt_path):
            print(f"Found video at alternative path: {alt_path}")
            video_path = alt_path
        else:
            exit(1)
            
    frames = extract_frames(video_path, output_dir)
    analyze_frames(frames, api_key)
