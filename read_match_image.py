import os
import google.generativeai as genai
from dotenv import load_dotenv

def analyze_matches(image_path, api_key):
    genai.configure(api_key=api_key)
    
    print(f"Uploading {image_path} to Gemini...")
    f = genai.upload_file(path=image_path)
        
    model = genai.GenerativeModel(model_name="models/gemini-2.5-flash")
    
    prompt = """
    图片中是一个足球比赛赛程表。
    为了测试我们刚写好的AI预测提示词（该提示词包含两套轨道：一套专门抓“实力悬殊的碾压局”，另一套专门排雷“五五开的混沌局”），
    请你从图片中选出2场最适合用来做测试的比赛，并直接输出比赛名称。
    
    选择标准：
    1. 选一场【实力悬殊】的比赛（豪门/强队 打 弱队/鱼腩），用来测试AI能否果断识别“降维打击”。
    2. 选一场【实力接近或可能爆冷】的比赛（五五开、中游对决、或强队客场存在隐患），用来测试AI的“排雷预警”和“盘口熔断机制”。
    
    请告诉我你推荐哪两场，并简短说明推荐理由（哪场用于测试碾压，哪场用于测试排雷）。
    """
    
    print("Analyzing matches with Gemini 2.5 Flash...")
    contents = [prompt, f]
    response = model.generate_content(contents)
    
    print("\n--- ANALYSIS RESULT ---\n")
    print(response.text)
    
    print("Cleaning up...")
    try:
        genai.delete_file(f.name)
    except:
        pass

if __name__ == "__main__":
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    image_path = r"d:\提示词调教\photo_2026-07-25_10-34-48.jpg"
    
    if not os.path.exists(image_path):
        print(f"Error: Image file not found at {image_path}")
    else:
        analyze_matches(image_path, api_key)
