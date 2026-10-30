import os
import google.generativeai as genai
from dotenv import load_dotenv

def analyze_pdf(pdf_path, api_key):
    genai.configure(api_key=api_key)
    
    print("Uploading PDF to Gemini...")
    pdf_file = genai.upload_file(path=pdf_path)
    print(f"Uploaded as {pdf_file.uri}")
    
    model = genai.GenerativeModel(model_name="models/gemini-2.5-flash")
    
    prompt = """
    你现在是一个专业的短视频/PPT视觉设计师，以及AI提示词工程师。
    这份PDF是由Google NotebookLM / Studio引擎自动生成的体育赛事分析视频的幻灯片/概览视觉画面。
    请仔细观察PDF里每一页图片的设计排版、内容排布、图文匹配度，以及视觉冲击力。
    
    请输出以下分析：
    1. 【当前视觉质量评估】：详细描述当前的图片效果。存在哪些优点？又有哪些明显的缺点或“AI幻觉/呆板排版”问题？比如：配图是否过于通用？文字是不是太多或太小？是否符合“硬核赛事分析师”的冷酷专业基调？
    2. 【提示词优化建议】：基于上述缺点，我应该在当前的提示词（尤其是【画面提示】和【输出格式模板】部分）中增加或修改哪些具体指令，才能逼迫NotebookLM/Studio输出更精美、更专业、更符合“大号球场放大镜”调性的图片？
    给出具体可复制的提示词修改建议。
    """
    
    print("Analyzing with Gemini 2.5 Flash...")
    response = model.generate_content([prompt, pdf_file])
    
    print("\n--- ANALYSIS RESULT ---\n")
    print(response.text)
    
    with open("pdf_analysis_result.txt", "w", encoding="utf-8") as f:
        f.write(response.text)
        
    try:
        genai.delete_file(pdf_file.name)
    except:
        pass

if __name__ == "__main__":
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    pdf_path = r"d:\提示词调教\Matchday_Strategic_Intelligence.pdf"
    analyze_pdf(pdf_path, api_key)
