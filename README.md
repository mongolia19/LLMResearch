# LLMResearch

A command-line tool for LLM-based research, multi-step reasoning, and content generation.

## Features

- Support for different LLM providers (OpenAI and compatible APIs)
- Custom configuration for base URL, API key, and model name
- Local file reading and processing
- Multi-step reasoning and writing generation
- Interactive command-line interface with progress indicators
- Continuous conversation with clarifying questions
- Detailed progress feedback during multi-step reasoning

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/LLMResearch.git
cd LLMResearch

# Install dependencies
pip install -r requirements.txt

# Install the package in development mode
pip install -e .

# Create a .env file from the example
cp .env.example .env
# Edit the .env file with your API keys and configuration
```

## Usage

### Basic Usage

```bash
# Start an interactive session
python -m llm_research

# Process a file and start a conversation about it
python -m llm_research --file path/to/document.txt

# Use a specific LLM configuration
python -m llm_research --config openai_gpt4
```

### Configuration

#### Using the CLI

```bash
# Add a new LLM configuration
python -m llm_research config add --name my_llm --base-url https://api.example.com --model model_name

# Set API key (will prompt securely)
python -m llm_research config set-key --name my_llm
```

#### Using Environment Variables (.env file)

You can configure LLM providers using environment variables in a `.env` file:

```
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-3.5-turbo

# Custom LLM Provider Configuration
CUSTOM_LLM_NAME=my_custom_llm
CUSTOM_LLM_API_KEY=your_custom_api_key_here
CUSTOM_LLM_BASE_URL=https://api.example.com
CUSTOM_LLM_MODEL=model_name

# Default LLM Provider
DEFAULT_LLM_PROVIDER=openai
```

This approach is particularly useful for development and testing, as it allows you to quickly switch between different LLM providers without modifying the code.

### Advanced Usage

```bash
# Multi-step reasoning on a specific topic
python -m llm_research reason --topic "Global warming causes" --steps 3

# Generate content based on multiple files
python -m llm_research generate --files doc1.txt,doc2.txt --prompt "Summarize these documents"
```

#### About Reasoning Steps

The `--steps` parameter in the reasoning command sets the maximum number of reasoning steps the model will use. This is an upper limit, not a requirement:

- If the model naturally completes the task in fewer steps than specified, it will stop when the task is complete.
- If the model would need more steps than specified, it will be limited to the maximum number of steps.
- If the model generates significantly more subtasks than the maximum steps (over 1.5x the limit), it will automatically retry the task decomposition up to 2 times, asking the model to provide fewer subtasks.

For example, if you set `--steps 5` but the model only needs 3 steps to reach a conclusion, it will use just 3 steps. This is efficient and doesn't force unnecessary computation.

#### Subtask Retry Mechanism

The system now includes a subtask retry mechanism that validates the completion of each subtask:

- After executing a subtask, the system calls the LLM to evaluate if the subtask was completed successfully
- If the subtask is determined to be incomplete, the system will retry it up to a configurable number of times
- The `--retries` parameter (or `max_retries` in the API) controls the maximum number of retry attempts per subtask (default: 3)
- If a subtask still fails after the maximum number of retries, the system will use the last response and continue with the next subtask

This mechanism improves the reliability of multi-step reasoning by ensuring each step is properly completed before moving on to the next one. It's particularly useful for complex tasks where the model might initially provide incomplete or incorrect responses.

Example usage:
```bash
# Run reasoning with custom retry settings
python -m llm_research reason --topic "Complex physics problem" --steps 5 --retries 5

# Use the example script
python examples/retry_reasoning.py --task "Analyze the impact of quantum computing on cryptography" --retries 4
```

#### Progress Indicators

When running multi-step reasoning, the system now provides detailed progress indicators:

- Shows when the model is analyzing the task and breaking it down into subtasks
- Displays the list of subtasks that will be executed
- Indicates when each subtask is being processed
- Shows a summary of each subtask's result
- Provides overall progress tracking from start to finish

This improves the user experience by providing visibility into the reasoning process, rather than making you wait without feedback during long-running operations.

Example output:
```
==== 开始多步骤推理 ====
任务: "分析全球变暖的主要原因"
最大步骤数: 3
=======================

🔍 分析任务: "分析全球变暖的主要原因"
正在将任务分解为子任务...

💭 步骤 1: 模型思考中...

📋 已将任务分解为以下子任务:
  1. 研究温室气体排放的影响
  2. 分析人类活动对全球变暖的贡献
  3. 调查自然因素在全球变暖中的作用

🔄 执行子任务 1/3: "研究温室气体排放的影响"
思考中...

💭 步骤 2: 模型思考中...
✅ 子任务 1 完成
结果摘要: 温室气体排放是全球变暖的主要驱动因素。这些气体包括二氧化碳、甲烷、氧化亚氮和氟化气体...

[其他子任务执行过程...]

🧩 整合所有子任务结果
生成最终答案...

💭 步骤 5: 模型思考中...

✨ 任务完成!

==== 推理过程完成 ====

结果:
全球变暖的主要原因可以分为人为因素和自然因素，但科学共识表明人为因素是主导...
```

## License

MIT