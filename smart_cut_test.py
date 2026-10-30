import os
import re
import json
from dotenv import load_dotenv
from openai import OpenAI

def parse_srt(srt_path):
    with open(srt_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Match blocks in SRT
    pattern = re.compile(r'(\d+)\n(\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3})\n(.*?)(?=\n\n|\Z)', re.DOTALL)
    matches = pattern.findall(content)
    
    subtitles = []
    for match in matches:
        subtitles.append({
            "id": int(match[0]),
            "timestamp": match[1],
            "text": match[2].strip().replace('\n', ' ')
        })
    return subtitles

def call_gemini(api_key, base_url, model_name, subtitles):
    client = OpenAI(
        api_key=api_key,
        base_url=base_url
    )
    
    # 构建包含所有字幕的字符串，提供给大模型
    subs_text = "\n".join([f"{sub['id']}: {sub['text']}" for sub in subtitles])
    
    system_prompt = (
        "你是一个专业的体育短视频剪辑师。请阅读以下带序号的视频字幕文本。\n"
        "你的任务是：剔除所有的开场白、结尾套话、章节过渡语、情绪渲染的废话、免责声明等无用信息。\n"
        "你只能保留对两场比赛（基本面、战术、市场盘口数据和最终预测）最核心的硬核分析。\n"
        "请务必输出一个纯JSON数组格式的序号列表，表示你需要**保留**的字幕序号。不要输出任何其他文本或Markdown标记。\n"
        "例如：[3, 4, 5, 8, 10]\n"
    )

    print(f"正在请求 Gemini 模型 ({model_name})，等待回复...")
    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "这是视频的源字幕文本，请剔除废话，只保留核心硬核分析的序号列表，格式为JSON数组：\n\n" + subs_text}
        ],
        temperature=0.1 # 使用低 temperature 保证输出格式稳定
    )
    
    result = response.choices[0].message.content.strip()
    
    # 尝试清理可能带有的 markdown code block 标记
    if result.startswith("```json"):
        result = result[7:]
    if result.startswith("```"):
        result = result[3:]
    if result.endswith("```"):
        result = result[:-3]
        
    try:
        kept_ids = json.loads(result.strip())
        if not isinstance(kept_ids, list):
            raise ValueError("返回的不是一个列表")
        return [int(x) for x in kept_ids]
    except Exception as e:
        print("解析大模型返回结果失败:", result)
        raise e

def main():
    load_dotenv()
    
    api_key = os.getenv("GEMINI_API_KEY")
    base_url = os.getenv("BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")
    model_name = os.getenv("MODEL_NAME", "gemini-2.5-flash")
    
    if not api_key:
        print("错误：未能从 .env 读取到 GEMINI_API_KEY")
        return

    srt_path = r"z:\01体彩赛事\7.25赛事\芬超-瑞典超数据\tmp_autocut\subtitles\subtitles_12155b42_ai.srt"
    
    if not os.path.exists(srt_path):
        print(f"错误：找不到文件 {srt_path}")
        return
        
    print(f"开始解析源字幕: {srt_path}")
    subtitles = parse_srt(srt_path)
    print(f"共解析到 {len(subtitles)} 句字幕。")
    
    kept_ids = call_gemini(api_key, base_url, model_name, subtitles)
    
    # 手动强制保留的字幕序号（例如：开场白、结尾、免责声明等）
    force_keep_ids = [1, 175, 178, 179]
    original_kept_count = len(kept_ids)
    
    # 合并 AI 决定保留的 和 手动强制保留的，并去重排序
    kept_ids_set = set(kept_ids)
    kept_ids_set.update(force_keep_ids)
    kept_ids = sorted(list(kept_ids_set))
    
    print(f"\nAI 原始保留 {original_kept_count} 句，加上手动强制保留，最终共保留 {len(kept_ids)} 句，最终删减 {len(subtitles) - len(kept_ids)} 句。")
    
    print("\n================== 被删除的废话 ==================")
    for sub in subtitles:
        if sub['id'] not in kept_ids:
            print(f"[删除] [{sub['id']}] {sub['text']}")
            
    print("\n================== 被保留的干货 ==================")
    kept_subtitles = []
    for sub in subtitles:
        if sub['id'] in kept_ids:
            print(f"[保留] [{sub['id']}] {sub['text']}")
            kept_subtitles.append(sub)
            
    # 将结果保存到文件，用于后续裁剪
    output_path = "subtitles_kept.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(kept_subtitles, f, ensure_ascii=False, indent=2)
    print(f"\n保留的字幕数据已保存至: {output_path}")

if __name__ == "__main__":
    main()
