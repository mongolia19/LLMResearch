# LLMResearch - 大语言模型研究工具

[English Version](README.md) | [中文版](#)

一个基于大语言模型的研究、多步推理和内容生成命令行工具，专为中国用户优化设计。

## 项目背景

OpenAI的DeepResearch功能非常强大，但其高昂的使用成本让许多开发者望而却步。开源社区中虽然有不少类似项目，但大多依赖Google搜索API或DuckDuckGo等搜索引擎，不仅配置复杂，而且在国内网络环境下难以稳定使用。

正是基于这些痛点，我们萌生了开发一个真正适合中国网络环境的深度研究工具的想法。LLMResearch应运而生，它不仅实现了类DeepResearch的功能，更针对国内用户进行了深度优化，让大语言模型的研究能力真正触手可及。

## 欢迎参与

我们诚挚欢迎各位开发者使用本项目！如果您在使用过程中有任何建议或需求，或者希望贡献代码改进，欢迎提交Issue或Pull Request。让我们共同打造一个更加强大的中文大模型研究工具！

## 主要特色

- **中国无限制运行**：使用博查API进行搜索，确保在中国境内无障碍使用
- **多模型支持**：兼容任何符合OpenAI API格式的大模型
- **深度研究功能**：实现类OpenAI的DeepResearch功能，可指定思考深度和尝试次数
- **实时互联网研究**：结合博查API和URL内容提取，进行深度互联网资料研究
- **多步推理机制**：支持复杂问题的分步推理和验证
- **本地文件处理**：支持本地文件读取和分析
- **交互式命令行界面**：提供进度指示和详细反馈

## 安装指南

```bash
# 克隆仓库
git clone https://github.com/yourusername/LLMResearch.git
cd LLMResearch

# 安装依赖
pip install -r requirements.txt

# 开发模式安装
pip install -e .

# 创建配置文件
cp .env.example .env
# 编辑.env文件配置API密钥
```

## 使用说明

### WebUI使用

```bash
# 启动WebUI服务
python -m llm_research webui

# 访问Web界面
http://localhost:5000
```

### 基础使用

```bash
# 启动交互式会话
python -m llm_research

# 处理文件并开始对话
python -m llm_research --file path/to/document.txt

# 使用特定LLM配置
python -m llm_research --config openai_gpt4
```

### 配置说明

#### 使用命令行配置

```bash
# 添加新LLM配置
python -m llm_research config add --name my_llm --base-url https://api.example.com --model model_name

# 设置API密钥（安全提示）
python -m llm_research config set-key --name my_llm
```

#### 使用环境变量配置（.env文件）

```env
# OpenAI配置
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-3.5-turbo

# 自定义LLM配置
CUSTOM_LLM_NAME=my_custom_llm
CUSTOM_LLM_API_KEY=your_custom_api_key_here
CUSTOM_LLM_BASE_URL=https://api.example.com
CUSTOM_LLM_MODEL=model_name

# 默认LLM提供商
DEFAULT_LLM_PROVIDER=openai

# 博查API配置
# API申请地址：https://open.bochaai.com/
BOCHA_API_KEY=your_bocha_api_key_here
```

### 高级功能

#### 多步推理

```bash
# 指定主题进行多步推理
python -m llm_research reason --topic "全球变暖原因" --steps 3

# 基于多个文件生成内容
python -m llm_research generate --files doc1.txt,doc2.txt --prompt "总结这些文档"
```

#### 推理步骤说明

- `--steps`参数设置最大推理步数
- 模型会根据需要自动调整实际步数
- 包含子任务重试机制，提高可靠性

#### 网络搜索与内容提取

```bash
# 启用网络搜索进行推理
python -m llm_research reason --topic "最新AI发展" --web-search --extract-url

# 使用博查API密钥
python -m llm_research reason --topic "最新AI发展" --bocha-api-key YOUR_API_KEY
```

#### URL内容提取

```bash
# 从URL提取内容
python -m llm_research extract_url --url https://example.com --format markdown

# 保存提取内容
python -m llm_research extract_url --url https://example.com --format text --output extracted_content.txt
```

## 许可证

MIT
