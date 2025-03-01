"""
Adapter for reasoning functionality.
"""

from typing import List, Dict, Any, Optional, Callable

from llm_research.llm.base import BaseLLM
from llm_research.reasoning import Reasoning as LLMReasoning
from llm_research.web_search import get_web_search_tool

class ReasoningAdapter:
    """
    Adapter for the LLMResearch reasoning functionality.
    
    This class provides a simplified interface to the LLMResearch reasoning
    functionality for use in the WebUI.
    """
    
    def __init__(
        self,
        llm: BaseLLM,
        max_steps: int = 5,
        temperature: float = 0.7,
        web_search_enabled: bool = True,
        extract_url_content: bool = True,
        ws_handler: Optional[Callable[[str], None]] = None
    ):
        """
        Initialize the reasoning adapter.
        
        Args:
            llm: The LLM provider to use
            max_steps: Maximum number of reasoning steps
            temperature: Sampling temperature for LLM calls
            web_search_enabled: Whether to enable web search
            extract_url_content: Whether to extract content from URLs
            ws_handler: WebSocket handler function for sending logs to UI (optional)
        """
        self.llm = llm
        self.max_steps = max_steps
        self.temperature = temperature
        
        # Initialize web search if enabled
        web_search = None
        if web_search_enabled:
            try:
                web_search = get_web_search_tool()
            except Exception as e:
                print(f"Warning: Failed to initialize web search: {e}")
        
        # Initialize reasoning
        self.reasoning = LLMReasoning(
            llm=llm,
            max_steps=max_steps,
            temperature=temperature,
            web_search=web_search,
            extract_url_content=extract_url_content
        )
        
        # Event handlers
        self.on_task_decomposition = None
        self.on_subtask_start = None
        self.on_subtask_complete = None
        self.on_aggregation_start = None
        self.on_aggregation_complete = None
    
    def task_decomposition(
        self,
        task: str,
        context: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> List[str]:
        """
        Decompose a complex task into subtasks.
        
        Args:
            task: The task to decompose
            context: Additional context (optional)
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature
            
        Returns:
            A list of subtasks
        """
        subtasks = self.reasoning.task_decomposition(
            task=task,
            context=context,
            max_tokens=max_tokens,
            temperature=temperature or self.temperature
        )
        
        # Call event handler if set
        if self.on_task_decomposition:
            self.on_task_decomposition(subtasks)
        
        return subtasks
    
    def execute_step(
        self,
        subtask: str,
        context: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        timeout: Optional[float] = None
    ) -> str:
        """
        Execute a reasoning step.
        
        Args:
            subtask: The subtask to execute
            context: Additional context (optional)
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature
            timeout: Maximum time in seconds for this step
            
        Returns:
            The result of the step
            
        Raises:
            TimeoutError: If the step exceeds the timeout duration
        """
        # Call event handler if set
        if self.on_subtask_start:
            self.on_subtask_start(subtask)
        
        # Construct the prompt
        prompt = f"Task: {subtask}\n\n"
        
        if context:
            prompt += f"Context:\n{context}\n\n"
        
        prompt += "Result:"
        
        # Execute the step
        result = self.reasoning.execute_step(
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature or self.temperature
        )
        
        # Call event handler if set
        if self.on_subtask_complete:
            self.on_subtask_complete(subtask, result)
        
        return result
    
    def aggregate_results(
        self,
        task: str,
        subtasks: List[str],
        results: List[str],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> str:
        """
        Aggregate the results of multiple subtasks.
        
        Args:
            task: The original task
            subtasks: The subtasks that were executed
            results: The results of each subtask
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature
            
        Returns:
            The aggregated result
        """
        # Call event handler if set
        if self.on_aggregation_start:
            self.on_aggregation_start()
        
        # Aggregate the results
        final_result = self.reasoning.aggregate_results(
            task=task,
            subtasks=subtasks,
            results=results,
            max_tokens=max_tokens,
            temperature=temperature or self.temperature
        )
        
        # Call event handler if set
        if self.on_aggregation_complete:
            self.on_aggregation_complete(final_result)
        
        return final_result
    
    def solve_task(
        self,
        task: str,
        context: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        max_retries: int = 3
    ) -> str:
        """
        Solve a complex task using multi-step reasoning.
        
        Args:
            task: The task to solve
            context: Additional context (optional)
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature
            max_retries: Maximum number of retry attempts per subtask
            
        Returns:
            The final result
        """
        return self.reasoning.solve_task(
            task=task,
            context=context,
            max_tokens=max_tokens,
            temperature=temperature or self.temperature,
            max_retries=max_retries
        )
    
    def get_steps(self) -> List[Dict[str, Any]]:
        """
        Get all reasoning steps.
        
        Returns:
            A list of reasoning steps
        """
        return [
            {
                "prompt": step.prompt,
                "response": step.response,
                "timestamp": step.timestamp
            }
            for step in self.reasoning.get_steps()
        ]