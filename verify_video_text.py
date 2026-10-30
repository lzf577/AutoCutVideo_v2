import os
import time
from dotenv import load_dotenv
import google.generativeai as genai
from moviepy.editor import VideoFileClip

def extract_audio(video_path, audio_path):
    print(f"1. 正在从视频提取音频...")
    print(f"-> 源视频: {video_path}")
    video = VideoFileClip(video_path)
    if video.audio is None:
        raise ValueError("视频中没有音频轨道！")
    video.audio.write_audiofile(audio_path, logger=None)
    print(f"-> 音频提取完成: {audio_path}")

def transcribe_audio(audio_path, api_key):
    print(f"\n2. 正在上传音频到 Gemini (AI Studio) 进行语音转文本...")
    genai.configure(api_key=api_key)
    
    # 上传文件
    audio_file = genai.upload_file(path=audio_path)
    print(f"-> 文件上传成功 (URI: {audio_file.uri})")
    
    # 生成内容
    print(f"\n3. 正在请求 Gemini 2.5 Flash 提取精确字幕，请稍候...")
    model = genai.GenerativeModel(model_name="models/gemini-2.5-flash")
    
    prompt = "请将这段音频完整、原封不动地逐句转录为文本，不要做任何总结、省略或修改。尽可能保留语音中的自然停顿，分段输出。"
    
    response = model.generate_content([prompt, audio_file])
    
    result_text = response.text
    
    print("\n" + "="*20 + " 音频转录结果 " + "="*20 + "\n")
    print(result_text)
    print("\n" + "="*54 + "\n")
    
    # 存入文件
    output_txt = "video_transcript.txt"
    with open(output_txt, "w", encoding="utf-8") as f:
        f.write(result_text)
    print(f"[OK] 转录结果已保存到当前目录的 {output_txt}")
    
    # 清理云端上传的文件
    try:
        genai.delete_file(audio_file.name)
        print("-> 已清理云端临时音频文件。")
    except:
        pass

if __name__ == "__main__":
    load_dotenv()
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("[Error] 请确保 .env 文件中配置了 GEMINI_API_KEY")
        exit(1)
        
    # 用户提供的源视频路径
    video_file = r"d:\Users\lzf\Downloads\内部模型测试版_V.1.0.mp4"
    audio_temp_file = "temp_audio_for_transcription.mp3"
    
    if not os.path.exists(video_file):
        print(f"[Error] 找不到视频文件: {video_file}")
        exit(1)
        
    try:
        extract_audio(video_file, audio_temp_file)
        transcribe_audio(audio_temp_file, api_key)
    except Exception as e:
        print(f"\n[Error] 发生错误: {str(e)}")
    finally:
        # 无论成功失败，都清理本地提取的临时音频
        if os.path.exists(audio_temp_file):
            os.remove(audio_temp_file)
