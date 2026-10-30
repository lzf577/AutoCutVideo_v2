import sys, io, os, re, difflib
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'd:/AutoCutVideo_v2/AutoCutVideo_Lite')
from rapidocr_onnxruntime import RapidOCR
from pipeline.pdf_extractor import extract_images_from_pdf

srt_file = 'd:/AutoCutVideo_v2/AutoCutVideo_Lite/test1/tmp_autocut/transcript_polished.srt'
if not os.path.exists(srt_file):
    srt_file = 'd:/AutoCutVideo_v2/AutoCutVideo_Lite/test1/tmp_autocut/transcript.srt'

if not os.path.exists(srt_file):
    from pipeline.audio_transcriber import extract_audio, transcribe_audio_to_srt
    v = 'd:/AutoCutVideo_v2/AutoCutVideo_Lite/test1/1.mp4'
    a = 'd:/AutoCutVideo_v2/AutoCutVideo_Lite/test1/tmp_autocut/extracted_audio.mp3'
    if not os.path.exists(a):
        extract_audio(v, a, trim_start=0, trim_end=3)
    transcribe_audio_to_srt(a, srt_file, model_name='base', device='auto')

with open(srt_file, 'r', encoding='utf-8') as f:
    srt_content = f.read()

sub_matches = re.findall(r'(\d+)\n(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2}),(\d{3})\n([^\n]+)', srt_content)
subs = []
for item in sub_matches:
    idx, h1, m1, s1, ms1, h2, m2, s2, ms2, text = item
    t1 = int(h1)*3600 + int(m1)*60 + int(s1) + int(ms1)/1000.0
    t2 = int(h2)*3600 + int(m2)*60 + int(s2) + int(ms2)/1000.0
    subs.append({'idx': int(idx), 'start': t1, 'end': t2, 'text': text})

pdf_path = 'd:/AutoCutVideo_v2/AutoCutVideo_Lite/test1/1.pdf'
out_dir = 'd:/AutoCutVideo_v2/AutoCutVideo_Lite/test1/tmp_autocut/slides'
images = extract_images_from_pdf(pdf_path, out_dir, dpi=150)

engine = RapidOCR()
slide_info = []
for idx, img_path in enumerate(images, 1):
    res, _ = engine(img_path)
    text_corpus = ' '.join([line[1] for line in res]) if res else ''
    slide_info.append({'slide_idx': idx, 'path': img_path, 'text': text_corpus})

matched_timeline = []
last_matched_time = 0.0

for s in slide_info:
    slide_text = s['text']
    keywords = [w for w in re.findall(r'[\u4e00-\u9fa5a-zA-Z0-9]+', slide_text) if len(w) >= 2 and w not in ['GeminiNotebook', 'Notebook', 'Gemini']]
    
    best_time = None
    best_score = 0
    best_sub_idx = -1
    
    for sub in subs:
        if sub['start'] < last_matched_time - 3.0:
            continue
        
        score = 0
        for kw in keywords:
            if kw in sub['text']:
                score += len(kw) * 3
            elif len(kw) >= 3 and difflib.SequenceMatcher(None, kw, sub['text']).ratio() > 0.6:
                score += len(kw) * 1.5
        
        if score > best_score:
            best_score = score
            best_time = sub['start']
            best_sub_idx = sub['idx']
            
    if best_time is not None and best_score >= 5:
        matched_timeline.append({
            'slide': s['slide_idx'],
            'start_time': round(best_time, 2),
            'keywords': keywords[:3],
            'score': best_score,
            'sub_text': subs[best_sub_idx-1]['text'] if best_sub_idx > 0 else ''
        })
        last_matched_time = best_time
    else:
        matched_timeline.append({
            'slide': s['slide_idx'],
            'start_time': None,
            'keywords': keywords[:3],
            'score': 0,
            'sub_text': ''
        })

print('\n=== PDF 幻灯片与字幕智能关键词匹配结果 ===')
for m in matched_timeline:
    st = m['start_time']
    st_str = f"{st:.1f}s" if st is not None else "自适应插值"
    print(f"Slide {m['slide']:02d} -> 呈现时间: {st_str:10s} | 命中字幕: {m['sub_text']}")
