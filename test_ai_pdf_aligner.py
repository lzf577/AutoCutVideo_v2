import sys, io, os, json, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'd:/AutoCutVideo_v2/AutoCutVideo_Lite')
from rapidocr_onnxruntime import RapidOCR
from pipeline.pdf_extractor import extract_images_from_pdf
from google import genai
from dotenv import load_dotenv

load_dotenv('d:/AutoCutVideo_v2/AutoCutVideo_Lite/.env')
api_key = os.getenv('GEMINI_API_KEY')

pdf_path = 'd:/AutoCutVideo_v2/AutoCutVideo_Lite/test1/1.pdf'
out_dir = 'd:/AutoCutVideo_v2/AutoCutVideo_Lite/test1/tmp_autocut/slides'
images = extract_images_from_pdf(pdf_path, out_dir, dpi=150)

engine = RapidOCR()
slide_cards = []
for idx, img_path in enumerate(images, 1):
    res, _ = engine(img_path)
    lines = [l[1] for l in res] if res else []
    slide_cards.append({'slide_index': idx, 'ocr_text': ' | '.join(lines)})

srt_path = 'd:/AutoCutVideo_v2/AutoCutVideo_Lite/test1/tmp_autocut/transcript_polished.srt'
if not os.path.exists(srt_path):
    srt_path = 'd:/AutoCutVideo_v2/AutoCutVideo_Lite/test1/tmp_autocut/transcript.srt'

with open(srt_path, 'r', encoding='utf-8') as f:
    srt_text = f.read()

prompt = f"""你是一位专业视频剪辑师。请根据以下 18 张 PDF 幻灯片的 OCR 核心内容，结合视频的 SRT 解说词时间轴，计算出每一张幻灯片在视频中最佳呈现的起止时间点 (start_time, end_time)。

【PDF 幻灯片内容列表】:
{json.dumps(slide_cards, ensure_ascii=False, indent=2)}

【完整视频字幕时间轴 (SRT)】:
{srt_text}

【要求】:
1. 每一页幻灯片必须与解说词中讨论的具体比赛、盘口、数据、结论精准对齐。
2. 严格按 JSON 数组输出：
[
  {{"slide_index": 1, "start_time": 0.0, "end_time": 13.5, "topic": "开篇介绍"}},
  ...
]
只输出纯 JSON，不要 markdown 代码块包裹。
"""

client = genai.Client(api_key=api_key)
resp = client.models.generate_content(
    model='gemini-2.5-flash',
    contents=prompt
)
raw_res = resp.text.strip()
raw_res = re.sub(r'^```json\s*|^```\s*|```$', '', raw_res).strip()
print(raw_res)
