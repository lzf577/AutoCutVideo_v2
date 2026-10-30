from google import genai

def list_available_models():
    # 初始化客户端。它会自动从环境变量中读取 GEMINI_API_KEY
    client = genai.Client()
    
    print("正在获取当前 API Key 支持的可用模型列表...\n")
    try:
        # 获取所有可用模型（这里需要以迭代器的形式读取或转成列表）
        models = client.models.list()
        
        antigravity_found = False
        
        print(f"{'模型 ID (name)':<45} | {'显示名称 (display_name)':<35} | {'支持的方法'}")
        print("-" * 110)
        
        for model in models:
            name = model.name
            display_name = model.display_name or "N/A"
            # 不同的 SDK 版本对支持方法的属性命名可能略有不同，这里做个兼容尝试
            actions = getattr(model, 'supported_generation_methods', getattr(model, 'supported_actions', 'Unknown'))
            
            print(f"{name:<45} | {display_name:<35} | {actions}")
            
            if 'antigravity' in name.lower() or 'antigravity' in display_name.lower():
                antigravity_found = True
                
        print("-" * 110)
        
        if antigravity_found:
            print("\n✅ 恭喜！在可用模型列表中找到了包含 'antigravity' 的模型。")
            print("请复制上表中它对应的 【模型 ID (name)】 替换掉我们刚才代码里的 'antigravity'，并留意它支持的方法是不是包含 generateContent。")
            print("如果它不支持 generateContent，则说明该代理模型需要使用特定的 Agent API 进行调用。")
        else:
            print("\n❌ 在你的 API Key 权限下，没有找到任何包含 'antigravity' 的模型。")
            print("虽然你在网页端的用量统计里看到了它，但你的 API Key 当前可能尚未开通调用该特殊代理模型（Agent）的 API 权限，或者该模型尚未正式对外开放 API。")
            
    except Exception as e:
        print(f"获取模型列表失败: {e}")

if __name__ == "__main__":
    list_available_models()
