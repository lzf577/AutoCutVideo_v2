# 🚀 Gemini API 接入与使用指南

## 📋 目录
1. [快速开始](#快速开始)
2. [详细配置](#详细配置)
3. [在 GUI 中使用](#在-gui-中使用)
4. [常见问题排查](#常见问题排查)
5. [成本控制](#成本控制)

---

## 快速开始

### 第一步：获取 Gemini API Key

1. 访问 **Google AI Studio**: https://aistudio.google.com/apikey
2. 点击 **"Create API Key"** 按钮
3. 复制生成的 API Key（形如 `AIza...`）
4. ⚠️ **保管好 API Key，不要分享给他人！**

### 第二步：配置项目

1. 在项目根目录，将 `.env.example` 复制为 `.env`
   ```bash
   cp .env.example .env
   ```
   或直接创建新文件 `.env`

2. 编辑 `.env` 文件，填入：
   ```env
   GEMINI_API_KEY=你的_API_Key_粘贴在这里
   BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
   MODEL_NAME=gemini-2.5-flash
   AUDIO_BITRATE=128k
   SUBTITLE_LANGUAGE=自动检测 (Auto)
   MAX_CHARS_PER_LINE=30
   ```

### 第三步：运行程序

```bash
# 安装依赖（首次）
pip install -r requirements.txt

# 运行程序
python main.py
```

---

## 详细配置

### 方案 1️⃣：直连 Gemini 官方 API（推荐）

**优点**：
- ✅ 官方渠道，最新模型
- ✅ 配置简单
- ✅ 免费配额充足（非商业用途）

**配置**：
```env
GEMINI_API_KEY=粘贴你的API_Key
BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
MODEL_NAME=gemini-2.5-flash
```

**模型选择建议**：
| 模型 | 适用场景 | 速度 | 精度 | 免费额度 |
|------|--------|------|------|--------|
| `gemini-2.5-flash` | 字幕生成（推荐） | 🚀🚀🚀 | ⭐⭐⭐⭐ | 充足 |
| `gemini-2.5-pro` | 高精度需求 | 🚀 | ⭐⭐⭐⭐⭐ | 有限 |
| `gemini-1.5-flash` | 备选方案 | 🚀🚀🚀 | ⭐⭐⭐⭐ | 充足 |

---

### 方案 2️⃣：使用国内中转服务（需翻墙）

若无法直连 Google 服务，可用第三方中转：

**推荐中转服务**：
- [one-api.com](https://one-api.com) - 支持 Gemini 中转
- [api2d.com](https://api2d.com) - 国内 API 聚合
- [openai-hk.com](https://openai-hk.com) - 香港节点

**配置示例（以 one-api 为例）**：
```env
GEMINI_API_KEY=sk-xxxxx  # 替换为你的 one-api 密钥
BASE_URL=https://api.one-api.com/v1/
MODEL_NAME=gpt-4o-mini  # one-api 映射的模型名
```

---

## 在 GUI 中使用

### 初次运行

1. **启动程序**后，点击菜单栏：**设置 (Settings)** → **大模型设置**

2. **在弹出的对话框中填写**：
   - **API Key**: 粘贴你的 Gemini API Key
   - **Base URL**: `https://generativelanguage.googleapis.com/v1beta/openai/`
   - **模型名称**: 从下拉菜单选择（如 `gemini-2.5-flash`）或手动输入

3. 点击 **保存** 按钮，配置将自动保存到 `.env` 文件

### 使用流程

```
1. 【文件】→ 【导入】→ 选择你的视频文件
   ↓
2. 在视频预览区播放、预览视频
   ↓
3. 【设置】→ 根据需要调整：
   - 大模型（API/模型选择）
   - 音频（码率）
   - 字幕（语言/每行字数/字体）
   ↓
4. 点击【一键生成字幕视频】按钮
   ↓
5. 等待处理完成
   ↓
6. 完成！导出的视频文件会自动打开所在文件夹
```

### 状态监控

处理过程中，下方的 **日志输出框** 会实时显示：
```
✅ 音频提取成功！
   - 正在将音频转换为 Base64 格式...
   - 正在请求生成字幕内容，请稍候...
✅ 字幕生成成功！
✅ 字幕压制成功！
```

---

## 常见问题排查

### ❌ 问题 1：`API Key invalid` 错误

**原因**：API Key 格式错误或已过期

**解决**：
1. 重新访问 https://aistudio.google.com/apikey
2. 创建新的 API Key
3. 确保没有多余的空格或特殊字符
4. 检查 `.env` 文件编码为 UTF-8（避免 BOM）

---

### ❌ 问题 2：`Connection timeout` 错误

**原因**：网络连接问题或 Google 服务在你的地区被限制

**解决**：
- 方案 A：检查网络连接，尝试重新请求
- 方案 B：使用国内中转服务（见方案 2）
- 方案 C：检查防火墙/代理设置

---

### ❌ 问题 3：字幕质量不好

**原因**：
- 音频质量差
- 字幕语言设置错误
- 模型选择不当

**解决**：
1. 试试更换为 `gemini-2.5-pro`（更精准）
2. 调整 **MAX_CHARS_PER_LINE** 参数（缩短每行字数）
3. 检查 **SUBTITLE_LANGUAGE** 设置
4. 确保输入的视频音频清晰

---

### ❌ 问题 4：`.env` 文件被忽略

**原因**：`.gitignore` 中包含了 `.env`

**解决**：
这是正常的！`.env` 文件不应该上传到 Git。
- 确保 `.env` 在本地项目根目录存在
- 验证文件内容：`cat .env`（Linux/Mac）或 `type .env`（Windows）

---

## 成本控制

### 免费额度使用情况

**Google Gemini 官方提供的免费额度**：
- ✅ 每分钟 60 个请求
- ✅ 每天 1,500 个请求
- ⏳ 需要绑定信用卡（不会自动扣费）

### 如何降低成本

| 优化方向 | 方法 | 效果 |
|--------|------|------|
| **模型选择** | 用 flash 替代 pro | 🔻 60% 费用 |
| **音频码率** | 改为 32k 或 16k | 🔻 20-40% 时间 |
| **批量处理** | 一次处理多个视频 | 🔻 网络开销 |

### 成本示例

假设一个 10 分钟的视频：
- **gemini-2.5-flash**: ~¥0.02-0.05
- **gemini-2.5-pro**: ~¥0.30-0.50

---

## 📞 更多帮助

- **官方文档**: https://ai.google.dev/docs
- **API 参考**: https://generativelanguage.googleapis.com/
- **社区支持**: https://github.com/google-gemini/cookbook

---

**祝你使用愉快！🎉**
