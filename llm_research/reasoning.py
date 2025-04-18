"""
Multi-step reasoning for complex tasks.
"""

import time
from typing import List, Dict, Any, Optional, Union, Callable
from dataclasses import dataclass, field

from llm_research.llm.base import BaseLLM
from llm_research.conversation import Conversation
from llm_research.web_search import BochaWebSearch
from llm_research.url_extractor import get_url_extractor


@dataclass
class ReasoningStep:
    """
    A step in a multi-step reasoning process.
    """
    prompt: str
    response: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class Reasoning:
    """
    Multi-step reasoning for complex tasks.
    
    This class handles breaking down complex tasks into subtasks,
    managing sequential LLM calls, and aggregating results.
    """
    
    def __init__(
        self,
        llm: BaseLLM,
        max_steps: int = 5,
        temperature: float = 0.7,
        web_search: Optional[BochaWebSearch] = None,
        extract_url_content: bool = True,
        ws_handler: Optional[Callable[[str], None]] = None,
        timeout: Optional[float] = 30.0
    ):
        """
        Initialize the reasoning manager.
        
        Args:
            llm: The LLM provider to use
            max_steps: Maximum number of reasoning steps
            temperature: Sampling temperature for LLM calls
            web_search: Web search tool for retrieving information (optional)
            extract_url_content: Whether to extract content from URLs found in search results (default: True)
            ws_handler: WebSocket handler function for sending logs to UI (optional)
            timeout: Maximum time in seconds for each reasoning step (default: 30.0)
        """
        self.llm = llm
        self.max_steps = max_steps
        self.temperature = temperature
        self.web_search = web_search
        self.extract_url_content = extract_url_content
        self.url_extractor = get_url_extractor() if extract_url_content else None
        self.steps: List[ReasoningStep] = []
        self.ws_handler = ws_handler
        self.timeout = timeout

    def _log(self, message: Union[str, Dict[str, Any]]) -> None:
        """Send log message to UI if ws_handler is available"""
        if self.ws_handler:
            if isinstance(message, str):
                self.ws_handler({
                    "type": "log",
                    "message": message,
                    "timestamp": time.time()
                })
            else:
                # If it's already a dictionary, ensure it has a timestamp
                if "timestamp" not in message:
                    message["timestamp"] = time.time()
                self.ws_handler(message)
    
    def add_step(self, prompt: str, response: str = "", metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Add a reasoning step.
        
        Args:
            prompt: The prompt for this step
            response: The response for this step (optional)
            metadata: Additional metadata for this step (optional)
        """
        self.steps.append(ReasoningStep(
            prompt=prompt,
            response=response,
            metadata=metadata or {}
        ))
    
    def get_steps(self) -> List[ReasoningStep]:
        """
        Get all reasoning steps.
        
        Returns:
            A list of reasoning steps
        """
        return self.steps
    
    def get_last_step(self) -> Optional[ReasoningStep]:
        """
        Get the last reasoning step.
        
        Returns:
            The last reasoning step, or None if there are no steps
        """
        if not self.steps:
            return None
        
        return self.steps[-1]
    
    def execute_step(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        timeout: Optional[float] = None,
        **kwargs
    ) -> str:
        """
        Execute a reasoning step.
        
        Args:
            prompt: The prompt for this step
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature
            timeout: Maximum time in seconds for this step (default: instance timeout)
            **kwargs: Additional parameters for the LLM
            
        Returns:
            The generated response
            
        Raises:
            TimeoutError: If the step exceeds the timeout duration
        """
        # Use instance timeout if not specified
        timeout = timeout if timeout is not None else self.timeout
        
        # Show thinking indicator
        step_num = len(self.steps) + 1
        print(f"💭 步骤 {step_num}: 模型思考中... (timeout: {timeout}s)")
        
        # Send step start event
        self._log({
            "type": "step_start",
            "step_num": step_num,
            "message": f"💭 步骤 {step_num}: 模型思考中... (timeout: {timeout}s)",
            "prompt": prompt
        })
        
        # Use the provided temperature or the default
        temp = temperature if temperature is not None else self.temperature
        
        try:
            # Generate the response with timeout
            response = self.llm.generate(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temp,
                timeout=timeout,
                **kwargs
            )
            
            response_text = response["text"]
            
        except TimeoutError:
            error_msg = f"❌ 步骤 {step_num} 超时 (超过 {timeout} 秒)"
            print(error_msg)
            self._log({
                "type": "step_error",
                "step_num": step_num,
                "message": error_msg,
                "error": "timeout"
            })
            raise TimeoutError(error_msg)
            
        except Exception as e:
            error_msg = f"❌ 步骤 {step_num} 出错: {str(e)}"
            print(error_msg)
            self._log({
                "type": "step_error",
                "step_num": step_num,
                "message": error_msg,
                "error": str(e)
            })
            raise
        
        # Check if the response contains a search request
        if self.web_search and "SEARCH:" in response_text:
            # Extract the search query
            lines = response_text.split("\n")
            search_queries = []
            
            for i, line in enumerate(lines):
                if line.strip().startswith("SEARCH:"):
                    query = line.strip()[len("SEARCH:"):].strip()
                    search_queries.append((i, query))
            
            # If we found search queries, perform the searches and update the response
            if search_queries:
                print(f"🔍 检测到搜索请求，执行网络搜索...")
                
                for idx, query in search_queries:
                    print(f"🌐 搜索查询: \"{query}\"")
                    search_results = self.web_search.search(query=query)
                    
                    # Extract content from URLs if enabled
                    extracted_contents = []
                    if self.extract_url_content and self.url_extractor:
                        # Check if search was successful
                        print(f"🔍 搜索结果: {search_results}")
                        if search_results["success"] and search_results.get("results"):
                            urls = []
                            url_summaries = []
                            
                            # Collect URLs and their summaries
                            print(f"🔍 处理 {len(search_results['results'])} 个搜索结果")
                            for i, result in enumerate(search_results["results"]):
                                print(f"🔍 处理结果 {i+1}: {result['name']}")
                                urls.append(result["url"])
                                url_summaries.append({
                                    "url": result["url"],
                                    "title": result["name"],
                                    "summary": result["summary"]
                                })
                            print(f"✅ 收集到 {len(urls)} 个URL")
                            
                            if urls:
                                print(f"📄 从搜索结果中发现 {len(urls)} 个URL，提取内容...")
                                
                                # Create a prompt to ask the LLM which URLs to extract content from
                                url_selection_prompt = f"Based on the following search results for the query '{query}', which URLs would be most relevant to extract full content from? Select up to 3 URLs that seem most promising based on their summaries.\n\n"
                                
                                # Add formatted summaries for the LLM to evaluate
                                for i, summary in enumerate(url_summaries, start=1):
                                    url_selection_prompt += f"{i}. {summary['title']}\n   URL: {summary['url']}\n   Summary: {summary['summary']}\n\n"
                                
                                url_selection_prompt += "List the numbers of the most relevant URLs (e.g., '1, 3, 5'):"
                                
                                # Get the LLM's recommendation on which URLs to extract
                                url_selection_response = self.llm.generate(
                                    prompt=url_selection_prompt,
                                    max_tokens=50,
                                    temperature=0.3
                                )
                                
                                # Parse the response to get the selected URL indices
                                selected_indices = []
                                selection_text = url_selection_response["text"].strip()
                                print(f"🔍 URL选择响应: {selection_text}")
                                print(f"🔍 可用URL数量: {len(urls)}")
                                
                                # Try to parse numbers from the response
                                import re
                                numbers = re.findall(r'\d+', selection_text)
                                print(f"🔍 解析到的数字: {numbers}")
                                
                                # Only accept numbers that could be valid indices (1-N)
                                max_valid_number = len(urls)
                                valid_numbers = [num for num in numbers if num.isdigit() and 1 <= int(num) <= max_valid_number]
                                print(f"🔍 有效数字范围: 1-{max_valid_number}")
                                print(f"🔍 有效数字: {valid_numbers}")
                                
                                for num in valid_numbers:
                                    try:
                                        idx = int(num) - 1  # Convert to 0-based index
                                        print(f"🔍 尝试索引: {idx}")
                                        if 0 <= idx < len(urls):
                                            selected_indices.append(idx)
                                            print(f"✅ 有效索引: {idx}")
                                        else:
                                            print(f"❌ 无效索引: {idx} (超出范围)")
                                    except ValueError as e:
                                        print(f"❌ 数值转换错误: {e}")
                                        continue
                                
                                # Limit to at most 3 URLs
                                selected_indices = selected_indices[:3]
                                
                                # Extract content from the selected URLs
                                for url_idx in selected_indices:
                                    url = urls[url_idx]
                                    try:
                                        print(f"📥 提取URL内容: {url}")
                                        content = self.url_extractor.extract_content(url, output_format="markdown")
                                        
                                        # Truncate content if it's too long (to avoid token limits)
                                        max_content_length = 4000
                                        if len(content) > max_content_length:
                                            content = content[:max_content_length] + "...\n[Content truncated due to length]"
                                        
                                        extracted_contents.append(f"Extracted content from {url}:\n\n{content}\n\n")
                                        print(f"✅ 成功提取内容，长度: {len(content)} 字符")
                                    except Exception as e:
                                        print(f"❌ 提取内容失败: {str(e)}")
                    
                    # Format the search results for inclusion in the prompt
                    formatted_search_results = self.web_search.format_search_results(search_results)
                    
                    # Add the extracted contents to the formatted search results
                    if extracted_contents:
                        formatted_search_results += "\n\n" + "\n".join(extracted_contents)
                    
                    # Replace the search line with the query and results
                    lines[idx] = f"SEARCH: {query}\n\nSearch Results:\n{formatted_search_results}\n"
                
                # Reconstruct the response with search results
                updated_prompt = prompt + "\n\n" + "\n".join(lines)
                
                # Generate a new response with the search results
                print(f"💭 使用搜索结果重新生成回答...")
                new_response = self.llm.generate(
                    prompt=updated_prompt,
                    max_tokens=max_tokens,
                    temperature=temp,
                    **kwargs
                )
                
                # Update the response text
                response_text = new_response["text"]
        
        # Add the step
        self.add_step(prompt, response_text)
        
        # Send step complete event
        self._log({
            "type": "step_complete",
            "step_num": step_num,
            "message": f"✅ 步骤 {step_num} 完成",
            "response": response_text
        })
        
        return response_text
    
    def chain_of_thought(
        self,
        question: str,
        context: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> str:
        """
        Perform chain-of-thought reasoning.
        
        Args:
            question: The question to answer
            context: Additional context (optional)
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional parameters for the LLM
            
        Returns:
            The final answer
        """
        # Construct the prompt
        prompt = "Let's solve this step-by-step:\n\n"
        
        if context:
            prompt += f"Context:\n{context}\n\n"
        
        prompt += f"Question: {question}\n\n"
        prompt += "Reasoning:"
        
        # Execute the reasoning step
        reasoning = self.execute_step(
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs
        )
        
        # Extract the answer from the reasoning
        answer_prompt = f"Based on the following reasoning, provide a concise answer to the question: '{question}'\n\n"
        answer_prompt += f"Reasoning:\n{reasoning}\n\n"
        answer_prompt += "Answer:"
        
        # Execute the answer step
        answer = self.execute_step(
            prompt=answer_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs
        )
        
        return answer
    
    def task_decomposition(
        self,
        task: str,
        context: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> List[str]:
        """
        Decompose a complex task into subtasks.
        
        Args:
            task: The task to decompose
            context: Additional context (optional)
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional parameters for the LLM
            
        Returns:
            A list of subtasks
        """
        print(f"\n🔍 分析任务: \"{task}\"")
        print("正在将任务分解为子任务...\n")
        
        # Send task decomposition start event
        self._log({
            "type": "decomposition_start",
            "message": f"🔍 分析任务: \"{task}\"\n正在将任务分解为子任务...",
            "task": task
        })
        
        max_retries = 2
        retry_count = 0
        
        while True:
            # Construct the prompt
            prompt = "Break down the following task into smaller, manageable subtasks:\n\n"
            
            if context:
                prompt += f"Context:\n{context}\n\n"
            
            prompt += f"Task: {task}\n\n"
            
            # If this is a retry, add instructions to limit the number of subtasks
            if retry_count > 0:
                prompt += f"Important: Please limit your response to at most {self.max_steps} subtasks. "
                prompt += f"The previous breakdown had too many subtasks ({len(subtasks)}).\n\n"
            
            prompt += "Subtasks (numbered list):"
            
            # Execute the decomposition step
            decomposition = self.execute_step(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )
            
            # Parse the subtasks
            subtasks = []
            for line in decomposition.split("\n"):
                line = line.strip()
                if line and (line[0].isdigit() or line[0] == "-"):
                    # Remove the number/bullet and any following punctuation
                    subtask = line.lstrip("0123456789.-) \t")
                    if subtask:
                        subtasks.append(subtask)
            
            # Check if we have too many subtasks
            if len(subtasks) <= self.max_steps * 1.5 or retry_count >= max_retries:
                break
            
            # If we have too many subtasks, retry
            retry_count += 1
            print(f"\n⚠️ 生成的子任务数量 ({len(subtasks)}) 远超最大步骤数 ({self.max_steps})")
            print(f"正在重新分解任务 (尝试 {retry_count}/{max_retries})...\n")
            
            # Send retry event
            self._log({
                "type": "decomposition_retry",
                "message": f"⚠️ 生成的子任务数量 ({len(subtasks)}) 远超最大步骤数 ({self.max_steps})\n正在重新分解任务 (尝试 {retry_count}/{max_retries})...",
                "retry_count": retry_count,
                "max_retries": max_retries
            })
        
        # Display the subtasks
        print("\n📋 已将任务分解为以下子任务:")
        for i, subtask in enumerate(subtasks):
            print(f"  {i+1}. {subtask}")
        print()
        
        # Send decomposition complete event
        subtasks_formatted = "\n".join([f"{i+1}. {subtask}" for i, subtask in enumerate(subtasks)])
        self._log({
            "type": "decomposition_complete",
            "message": f"📋 已将任务分解为以下子任务:\n{subtasks_formatted}",
            "subtasks": subtasks
        })
        
        return subtasks
    
    def execute_subtasks(
        self,
        subtasks: List[str],
        context: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        max_retries: int = 3,  # New parameter for maximum retries
        **kwargs
    ) -> List[str]:
        """
        Execute a list of subtasks.
        
        Args:
            subtasks: The subtasks to execute
            context: Additional context (optional)
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature
            max_retries: Maximum number of retry attempts for each subtask (default: 3)
            **kwargs: Additional parameters for the LLM
            
        Returns:
            A list of responses for each subtask
        """
        responses = []
        total_subtasks = len(subtasks)
        
        for i, subtask in enumerate(subtasks):
            # Send subtask start event
            self._log({
                "type": "subtask_start",
                "message": f"\n🔄 执行子任务 {i+1}/{total_subtasks}: \"{subtask}\"\n思考中...",
                "subtask_index": i,
                "subtask": subtask,
                "total_subtasks": total_subtasks
            })
            
            # Track retry attempts
            retry_count = 0
            subtask_completed = False
            
            # Keep trying until the subtask is completed or max retries is reached
            while not subtask_completed and retry_count <= max_retries:
                if retry_count > 0:
                    print(f"🔁 重试子任务 {i+1} (尝试 {retry_count}/{max_retries})...")
                    
                    # Send retry event
                    self._log({
                        "type": "subtask_retry",
                        "message": f"🔁 重试子任务 {i+1} (尝试 {retry_count}/{max_retries})...",
                        "subtask_index": i,
                        "retry_count": retry_count,
                        "max_retries": max_retries
                    })
                
                # Construct the prompt
                prompt = f"Subtask {i+1}/{len(subtasks)}: {subtask}\n\n"
                
                if context:
                    prompt += f"Context:\n{context}\n\n"
                
                # Add previous subtask results as context
                if responses:
                    prompt += "Previous results:\n"
                    for j, (prev_task, prev_response) in enumerate(zip(subtasks[:i], responses)):
                        prompt += f"Subtask {j+1}: {prev_task}\nResult: {prev_response}\n\n"
                
                # Add web search tool instructions if available
                if self.web_search:
                    prompt += "Tools available:\n"
                    prompt += "1. Web Search Tool - You can search the internet for information by using the following format:\n"
                    prompt += "   SEARCH: your search query\n"
                    prompt += "   This will return search results from the web that you can use to answer the question.\n\n"
                
                prompt += f"Execute subtask: {subtask}\n\n"
                prompt += "Result:"
                
                # Execute the subtask
                response = self.execute_step(
                    prompt=prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    **kwargs
                )
                
                # Log the response for debugging
                result_summary = response[:100] + "..." if len(response) > 100 else response
                print(f"📝 子任务 {i+1} 结果: {result_summary}")
                
                # Validate if the subtask is completed
                print("🔍 验证子任务是否完成...")
                
                # Send validation start event
                self._log({
                    "type": "subtask_validation_start",
                    "message": f"🔍 验证子任务 {i+1} 是否完成...",
                    "subtask_index": i
                })
                subtask_completed = self._validate_subtask_completion(
                    subtask=subtask,
                    response=response,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    **kwargs
                )
                
                if subtask_completed:
                    print(f"✅ 子任务 {i+1} 完成")
                    
                    # Send subtask complete event
                    self._log({
                        "type": "subtask_complete",
                        "message": f"✅ 子任务 {i+1}/{total_subtasks} 完成",
                        "subtask_index": i,
                        "subtask": subtask,
                        "response": response
                    })
                    
                    responses.append(response)
                else:
                    print(f"❌ 子任务 {i+1} 未完成")
                    
                    # Send subtask incomplete event
                    self._log({
                        "type": "subtask_incomplete",
                        "message": f"❌ 子任务 {i+1}/{total_subtasks} 未完成",
                        "subtask_index": i,
                        "subtask": subtask,
                        "response": response
                    })
                    
                    retry_count += 1
                    
                    if retry_count > max_retries:
                        print(f"⚠️ 达到最大重试次数 ({max_retries})，使用最后一次结果")
                        
                        # Send max retries event
                        self._log({
                            "type": "subtask_max_retries",
                            "message": f"⚠️ 达到最大重试次数 ({max_retries})，使用最后一次结果",
                            "subtask_index": i,
                            "subtask": subtask,
                            "response": response
                        })
                        
                        responses.append(response)
                    else:
                        print(f"准备重试子任务 {i+1}...")
        
        return responses
    
    def _validate_subtask_completion(
        self,
        subtask: str,
        response: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        timeout: Optional[float] = None,
        **kwargs
    ) -> bool:
        """
        Validate if a subtask is completed successfully.
        
        Args:
            subtask: The subtask to validate
            response: The response to validate
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature
            timeout: Maximum time in seconds for validation
            **kwargs: Additional parameters for the LLM
            
        Returns:
            True if the subtask is completed, False otherwise
        """
        try:
            # Construct the validation prompt
            validation_prompt = """Evaluate if the following subtask has been completed successfully based on the response.
            
            Instructions:
            1. Only answer with "Yes" or "No"
            2. Do not provide any explanation
            3. Consider the response complete if it addresses the subtask
            
            Subtask: {subtask}
            
            Response: {response}
            
            Answer:""".format(subtask=subtask, response=response)
            
            # Execute the validation step with timeout
            print("💭 验证中...")
            validation_response = self.llm.generate(
                prompt=validation_prompt,
                max_tokens=10,  # Strict limit for yes/no response
                temperature=0.1,  # Very low temperature for deterministic response
                timeout=timeout or self.timeout,
                **kwargs
            )
            
            # Extract and clean the validation result
            validation_text = validation_response["text"].strip().lower()
            validation_text = validation_text.split()[0]  # Take only first word
            
            # Log the validation response for debugging
            print(f"🔍 验证结果: {validation_text}")
            
            # Check if the validation response indicates completion
            return validation_text.startswith("yes")
            
        except Exception as e:
            print(f"❌ 验证错误: {str(e)}")
            # If validation fails, assume the subtask is incomplete
            return False
    
    def aggregate_results(
        self,
        task: str,
        subtasks: List[str],
        results: List[str],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> str:
        """
        Aggregate the results of multiple subtasks.
        
        Args:
            task: The original task
            subtasks: The subtasks that were executed
            results: The results of each subtask
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional parameters for the LLM
            
        Returns:
            The aggregated result
        """
        print("\n🧩 整合所有子任务结果")
        print("生成最终答案...\n")
        
        # Send aggregation start event
        self._log({
            "type": "aggregation_start",
            "message": "🧩 整合所有子任务结果\n生成最终答案...",
            "task": task,
            "subtasks_count": len(subtasks)
        })
        
        # Construct the prompt
        prompt = f"Original task: {task}\n\n"
        prompt += "Subtasks and results:\n"
        
        for i, (subtask, result) in enumerate(zip(subtasks, results)):
            prompt += f"Subtask {i+1}: {subtask}\nResult: {result}\n\n"
        
        prompt += "Aggregate the results of the subtasks to provide a comprehensive response to the original task.\n\n"
        prompt += "Final result:"
        
        # Execute the aggregation step
        aggregation = self.execute_step(
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs
        )
        
        print("\n✨ 任务完成!")
        
        # Send aggregation complete event
        self._log({
            "type": "aggregation_complete",
            "message": "✨ 任务完成!",
            "result": aggregation
        })
        
        return aggregation
    
    def solve_task(
        self,
        task: str,
        context: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        max_retries: int = 3,  # Parameter for maximum retries
        web_search_enabled: bool = True,  # Enable/disable web search for this task
        extract_url_content: Optional[bool] = None,  # Enable/disable URL content extraction
        **kwargs
    ) -> str:
        """
        Solve a complex task using multi-step reasoning.
        
        Args:
            task: The task to solve
            context: Additional context (optional)
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature
            max_retries: Maximum number of retry attempts for each subtask (default: 3)
            web_search_enabled: Whether to enable web search for this task (default: True)
            extract_url_content: Whether to extract content from URLs found in search results (default: None, uses the instance setting)
            **kwargs: Additional parameters for the LLM
            
        Returns:
            The final result
        """
        self._log("\n==== 开始多步骤推理 ====")
        self._log(f"任务: \"{task}\"")
        self._log(f"最大步骤数: {self.max_steps}")
        self._log("=======================\n")
        
        # Decompose the task into subtasks
        subtasks = self.task_decomposition(
            task=task,
            context=context,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs
        )
        
        # Limit the number of subtasks to max_steps
        # Note: If the model generates fewer subtasks than max_steps,
        # we'll just use those without requiring exactly max_steps
        if len(subtasks) > self.max_steps:
            print(f"\n⚠️ 执行的子任务数量将限制为最大步骤数 ({self.max_steps})")
            print(f"只执行前 {self.max_steps} 个子任务\n")
            subtasks = subtasks[:self.max_steps]
        
        # Store the original settings
        original_web_search = self.web_search
        original_extract_url_content = self.extract_url_content
        original_url_extractor = self.url_extractor
        
        # Temporarily disable web search if requested
        if not web_search_enabled:
            self.web_search = None
            print("🔍 网络搜索功能已禁用")
        elif self.web_search:
            print("🔍 网络搜索功能已启用")
        
        # Temporarily modify URL extraction setting if specified
        if extract_url_content is not None:
            self.extract_url_content = extract_url_content
            self.url_extractor = get_url_extractor() if extract_url_content else None
            
            if extract_url_content:
                print("📄 URL内容提取功能已启用")
            else:
                print("📄 URL内容提取功能已禁用")
        
        try:
            # Execute the subtasks
            results = self.execute_subtasks(
                subtasks=subtasks,
                context=context,
                max_tokens=max_tokens,
                temperature=temperature,
                max_retries=max_retries,  # Pass the max_retries parameter
                **kwargs
            )
        finally:
            # Restore the original settings
            self.web_search = original_web_search
            self.extract_url_content = original_extract_url_content
            self.url_extractor = original_url_extractor
        
        # Aggregate the results
        final_result = self.aggregate_results(
            task=task,
            subtasks=subtasks,
            results=results,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs
        )
        
        print("\n==== 推理过程完成 ====\n")
        
        return final_result