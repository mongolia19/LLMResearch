"""
Multi-step reasoning for complex tasks.
"""

import time
from typing import List, Dict, Any, Optional, Union, Callable
from dataclasses import dataclass, field

from llm_research.llm.base import BaseLLM
from llm_research.conversation import Conversation


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
        temperature: float = 0.7
    ):
        """
        Initialize the reasoning manager.
        
        Args:
            llm: The LLM provider to use
            max_steps: Maximum number of reasoning steps
            temperature: Sampling temperature for LLM calls
        """
        self.llm = llm
        self.max_steps = max_steps
        self.temperature = temperature
        self.steps: List[ReasoningStep] = []
    
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
        **kwargs
    ) -> str:
        """
        Execute a reasoning step.
        
        Args:
            prompt: The prompt for this step
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional parameters for the LLM
            
        Returns:
            The generated response
        """
        # Use the provided temperature or the default
        temp = temperature if temperature is not None else self.temperature
        
        # Show thinking indicator
        step_num = len(self.steps) + 1
        print(f"💭 步骤 {step_num}: 模型思考中...")
        
        # Generate the response
        response = self.llm.generate(
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temp,
            **kwargs
        )
        
        # Add the step
        self.add_step(prompt, response["text"])
        
        return response["text"]
    
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
        
        # Display the subtasks
        print("\n📋 已将任务分解为以下子任务:")
        for i, subtask in enumerate(subtasks):
            print(f"  {i+1}. {subtask}")
        print()
        
        return subtasks
    
    def execute_subtasks(
        self,
        subtasks: List[str],
        context: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> List[str]:
        """
        Execute a list of subtasks.
        
        Args:
            subtasks: The subtasks to execute
            context: Additional context (optional)
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional parameters for the LLM
            
        Returns:
            A list of responses for each subtask
        """
        responses = []
        total_subtasks = len(subtasks)
        
        for i, subtask in enumerate(subtasks):
            print(f"\n🔄 执行子任务 {i+1}/{total_subtasks}: \"{subtask}\"")
            print("思考中...\n")
            
            # Construct the prompt
            prompt = f"Subtask {i+1}/{len(subtasks)}: {subtask}\n\n"
            
            if context:
                prompt += f"Context:\n{context}\n\n"
            
            # Add previous subtask results as context
            if responses:
                prompt += "Previous results:\n"
                for j, (prev_task, prev_response) in enumerate(zip(subtasks[:i], responses)):
                    prompt += f"Subtask {j+1}: {prev_task}\nResult: {prev_response}\n\n"
            
            prompt += f"Execute subtask: {subtask}\n\n"
            prompt += "Result:"
            
            # Execute the subtask
            response = self.execute_step(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )
            
            # Display the result summary
            print(f"✅ 子任务 {i+1} 完成")
            result_summary = response[:100] + "..." if len(response) > 100 else response
            print(f"结果摘要: {result_summary}\n")
            
            responses.append(response)
        
        return responses
    
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
        
        return aggregation
    
    def solve_task(
        self,
        task: str,
        context: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> str:
        """
        Solve a complex task using multi-step reasoning.
        
        Args:
            task: The task to solve
            context: Additional context (optional)
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional parameters for the LLM
            
        Returns:
            The final result
        """
        print("\n==== 开始多步骤推理 ====")
        print(f"任务: \"{task}\"")
        print(f"最大步骤数: {self.max_steps}")
        print("=======================\n")
        
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
        
        # Execute the subtasks
        results = self.execute_subtasks(
            subtasks=subtasks,
            context=context,
            max_tokens=max_tokens,
            temperature=temperature,
            **kwargs
        )
        
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