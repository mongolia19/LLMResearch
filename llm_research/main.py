"""
Main entry point for the LLMResearch CLI.
"""

import os
import sys
import click
import getpass
from typing import List, Optional, Dict, Any

from llm_research.config import Config
from llm_research.llm.base import BaseLLM
from llm_research.llm.openai import OpenAILLM
from llm_research.llm.custom import CustomLLM
from llm_research.file_handler import FileHandler
from llm_research.conversation import Conversation
from llm_research.reasoning import Reasoning
from llm_research.web_search import get_web_search_tool


def get_llm_provider(config: Config, provider_name: Optional[str] = None) -> BaseLLM:
    """
    Get an LLM provider instance based on the configuration.
    
    Args:
        config: The configuration manager
        provider_name: The name of the provider to use (optional)
        
    Returns:
        An LLM provider instance
    """
    # Get the provider configuration
    provider_config = config.get_provider_config(provider_name)
    
    # Check if the API key is set
    if not provider_config.get("api_key"):
        # Prompt for the API key
        api_key = getpass.getpass(f"Enter API key for {provider_name or 'default provider'}: ")
        provider_config["api_key"] = api_key
        
        # Save the API key
        config.set_provider_config(provider_name or config.config.get("default_provider", "openai"), provider_config)
    
    # Create the LLM provider instance
    provider_type = provider_config.get("type", "openai")
    
    if provider_type == "openai":
        return OpenAILLM(
            model=provider_config.get("model", "gpt-3.5-turbo"),
            base_url=provider_config.get("base_url", "https://api.openai.com/v1"),
            api_key=provider_config["api_key"]
        )
    else:
        return CustomLLM(
            model=provider_config.get("model", "default"),
            base_url=provider_config.get("base_url", ""),
            api_key=provider_config["api_key"],
            **provider_config.get("options", {})
        )


@click.group()
@click.version_option()
def cli():
    """
    LLMResearch - A tool for LLM-based research and multi-step reasoning.
    """
    pass


@cli.command()
@click.option("--provider", "-p", help="The LLM provider to use")
@click.option("--file", "-f", multiple=True, help="Path to a file to read")
@click.option("--topic", "-t", help="The topic to research")
@click.option("--steps", "-s", type=int, default=3, help="Number of reasoning steps")
@click.option("--retries", "-r", type=int, default=3, help="Maximum number of retry attempts per subtask")
@click.option("--temperature", type=float, default=0.7, help="Sampling temperature")
@click.option("--max-tokens", type=int, help="Maximum number of tokens to generate")
@click.option("--web-search/--no-web-search", default=True, help="Enable/disable web search")
@click.option("--bocha-api-key", help="Bocha API key for web search")
def reason(
    provider: Optional[str],
    file: List[str],
    topic: Optional[str],
    steps: int,
    retries: int,
    temperature: float,
    max_tokens: Optional[int],
    web_search: bool,
    bocha_api_key: Optional[str]
):
    """
    Perform multi-step reasoning on a topic or file.
    """
    # Load the configuration
    config = Config()
    
    # Get the LLM provider
    llm = get_llm_provider(config, provider)
    
    # Initialize web search tool if enabled
    web_search_tool = None
    if web_search:
        try:
            # Get the API key from the parameter, environment variable, or config
            api_key = bocha_api_key or os.environ.get("BOCHA_API_KEY")
            
            # If no API key is provided, check the config
            if not api_key:
                provider_config = config.get_provider_config("bocha")
                api_key = provider_config.get("api_key") if provider_config else None
            
            # If still no API key, prompt the user
            if not api_key:
                api_key = getpass.getpass("Enter Bocha API key: ")
                
                # Save the API key in the config
                if api_key:
                    bocha_config = {
                        "api_key": api_key,
                        "type": "web_search"
                    }
                    config.set_provider_config("bocha", bocha_config)
            
            if api_key:
                web_search_tool = get_web_search_tool(api_key=api_key)
                click.echo("Web search enabled using Bocha API")
            else:
                click.echo("Web search disabled: No API key provided", err=True)
        except Exception as e:
            click.echo(f"Error initializing web search: {e}", err=True)
    
    # Create the reasoning manager
    reasoning = Reasoning(llm, max_steps=steps, temperature=temperature, web_search=web_search_tool)
    
    # Read files if provided
    context = ""
    if file:
        file_handler = FileHandler()
        for f in file:
            try:
                content = file_handler.read_file(f)
                context += f"\n\n--- {os.path.basename(f)} ---\n\n{content}"
            except Exception as e:
                click.echo(f"Error reading file {f}: {e}", err=True)
    
    # Check if we have a topic or files
    if not topic and not file:
        topic = click.prompt("Enter a topic to research")
    
    # Perform the reasoning
    if topic:
        click.echo(f"Researching topic: {topic}")
        result = reasoning.solve_task(
            task=topic,
            context=context if context else None,
            max_tokens=max_tokens,
            max_retries=retries,
            web_search_enabled=web_search
        )
    else:
        click.echo("Analyzing files...")
        result = reasoning.chain_of_thought(
            question="What are the key insights from these documents?",
            context=context,
            max_tokens=max_tokens
        )
    
    # Print the result
    click.echo("\nResult:")
    click.echo(result)


@cli.command()
@click.option("--provider", "-p", help="The LLM provider to use")
@click.option("--file", "-f", multiple=True, help="Path to a file to read")
@click.option("--prompt", help="The initial prompt")
@click.option("--temperature", type=float, default=0.7, help="Sampling temperature")
@click.option("--max-tokens", type=int, help="Maximum number of tokens to generate")
def generate(
    provider: Optional[str],
    file: List[str],
    prompt: Optional[str],
    temperature: float,
    max_tokens: Optional[int]
):
    """
    Generate content based on files and a prompt.
    """
    # Load the configuration
    config = Config()
    
    # Get the LLM provider
    llm = get_llm_provider(config, provider)
    
    # Read files if provided
    context = ""
    if file:
        file_handler = FileHandler()
        for f in file:
            try:
                content = file_handler.read_file(f)
                context += f"\n\n--- {os.path.basename(f)} ---\n\n{content}"
            except Exception as e:
                click.echo(f"Error reading file {f}: {e}", err=True)
    
    # Check if we have a prompt
    if not prompt:
        if context:
            prompt = click.prompt("Enter a prompt for content generation")
        else:
            prompt = click.prompt("Enter a prompt for content generation (no files provided)")
    
    # Create the full prompt
    full_prompt = prompt
    if context:
        full_prompt = f"{prompt}\n\nContext:\n{context}"
    
    # Generate the content
    click.echo("Generating content...")
    response = llm.generate(
        prompt=full_prompt,
        max_tokens=max_tokens,
        temperature=temperature
    )
    
    # Print the result
    click.echo("\nGenerated content:")
    click.echo(response["text"])


@cli.command()
@click.option("--provider", "-p", help="The LLM provider to use")
@click.option("--file", "-f", multiple=True, help="Path to a file to read")
@click.option("--system-message", "-s", help="The system message")
@click.option("--temperature", type=float, default=0.7, help="Sampling temperature")
@click.option("--max-tokens", type=int, help="Maximum number of tokens to generate")
def chat(
    provider: Optional[str],
    file: List[str],
    system_message: Optional[str],
    temperature: float,
    max_tokens: Optional[int]
):
    """
    Start an interactive chat session.
    """
    # Load the configuration
    config = Config()
    
    # Get the LLM provider
    llm = get_llm_provider(config, provider)
    
    # Set up the system message
    if not system_message:
        if file:
            system_message = "You are a helpful assistant. Answer questions based on the provided documents."
        else:
            system_message = "You are a helpful assistant. Answer questions to the best of your ability."
    
    # Create the conversation manager
    conversation = Conversation(llm, system_message=system_message)
    
    # Read files if provided
    if file:
        file_handler = FileHandler()
        context = ""
        for f in file:
            try:
                content = file_handler.read_file(f)
                context += f"\n\n--- {os.path.basename(f)} ---\n\n{content}"
            except Exception as e:
                click.echo(f"Error reading file {f}: {e}", err=True)
        
        # Add the context as a user message
        if context:
            conversation.add_message("user", f"Here are the documents to reference:\n{context}")
            conversation.add_message("assistant", "I'll reference these documents when answering your questions.")
    
    # Start the chat loop
    click.echo("Starting chat session. Type 'exit' or 'quit' to end the session.")
    click.echo("Type 'clear' to clear the conversation history.")
    click.echo("Type 'save <filename>' to save the conversation.")
    click.echo("Type 'load <filename>' to load a conversation.")
    click.echo()
    
    while True:
        # Get user input
        user_input = input("> ")
        
        # Check for special commands
        if user_input.lower() in ["exit", "quit"]:
            break
        elif user_input.lower() == "clear":
            conversation.clear_conversation()
            click.echo("Conversation history cleared.")
            continue
        elif user_input.lower().startswith("save "):
            filename = user_input[5:].strip()
            try:
                conversation.save_conversation(filename)
                click.echo(f"Conversation saved to {filename}")
            except Exception as e:
                click.echo(f"Error saving conversation: {e}", err=True)
            continue
        elif user_input.lower().startswith("load "):
            filename = user_input[5:].strip()
            try:
                conversation.load_conversation(filename)
                click.echo(f"Conversation loaded from {filename}")
            except Exception as e:
                click.echo(f"Error loading conversation: {e}", err=True)
            continue
        
        # Add the user message
        conversation.add_message("user", user_input)
        
        # Generate the response
        click.echo("Thinking...")
        try:
            response = conversation.generate_response(
                max_tokens=max_tokens,
                temperature=temperature
            )
            click.echo(f"Assistant: {response}")
        except Exception as e:
            click.echo(f"Error generating response: {e}", err=True)


@cli.group()
def config():
    """
    Manage LLM provider configurations.
    """
    pass


@config.command("list")
def config_list():
    """
    List all configured LLM providers.
    """
    # Load the configuration
    config = Config()
    
    # Get the list of providers
    providers = config.list_providers()
    default_provider = config.config.get("default_provider")
    
    # Print the providers
    click.echo("Configured LLM providers:")
    for provider in providers:
        if provider == default_provider:
            click.echo(f"* {provider} (default)")
        else:
            click.echo(f"  {provider}")


@config.command("show")
@click.argument("provider", required=False)
def config_show(provider: Optional[str]):
    """
    Show the configuration for a provider.
    """
    # Load the configuration
    config = Config()
    
    # Get the provider configuration
    try:
        provider_config = config.get_provider_config(provider)
        
        # Print the configuration
        click.echo(f"Configuration for {provider or 'default provider'}:")
        for key, value in provider_config.items():
            if key == "api_key":
                click.echo(f"  {key}: {'*' * 8}")
            else:
                click.echo(f"  {key}: {value}")
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)


@config.command("add")
@click.option("--name", "-n", required=True, help="The name of the provider")
@click.option("--base-url", "-u", required=True, help="The base URL for the API")
@click.option("--model", "-m", required=True, help="The model name")
@click.option("--type", "-t", default="openai", help="The provider type (openai or custom)")
@click.option("--set-default", "-d", is_flag=True, help="Set as the default provider")
def config_add(name: str, base_url: str, model: str, type: str, set_default: bool):
    """
    Add a new LLM provider configuration.
    """
    # Load the configuration
    config = Config()
    
    # Create the provider configuration
    provider_config = {
        "base_url": base_url,
        "model": model,
        "type": type,
        "api_key": ""
    }
    
    # Set the provider configuration
    config.set_provider_config(name, provider_config)
    
    # Set as default if requested
    if set_default:
        config.set_default_provider(name)
    
    # Prompt for the API key
    api_key = getpass.getpass(f"Enter API key for {name} (leave empty to set later): ")
    if api_key:
        config.set_api_key(name, api_key)
    
    click.echo(f"Provider {name} added successfully.")


@config.command("set-key")
@click.option("--name", "-n", help="The name of the provider")
def config_set_key(name: Optional[str]):
    """
    Set the API key for a provider.
    """
    # Load the configuration
    config = Config()
    
    # Get the provider name
    if not name:
        providers = config.list_providers()
        if not providers:
            click.echo("No providers configured.", err=True)
            return
        
        default_provider = config.config.get("default_provider")
        if default_provider:
            name = default_provider
        else:
            name = providers[0]
    
    # Prompt for the API key
    api_key = getpass.getpass(f"Enter API key for {name}: ")
    
    # Set the API key
    try:
        config.set_api_key(name, api_key)
        click.echo(f"API key for {name} set successfully.")
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)


@config.command("set-default")
@click.argument("provider")
def config_set_default(provider: str):
    """
    Set the default LLM provider.
    """
    # Load the configuration
    config = Config()
    
    # Set the default provider
    try:
        config.set_default_provider(provider)
        click.echo(f"Default provider set to {provider}.")
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)


@config.command("delete")
@click.argument("provider")
def config_delete(provider: str):
    """
    Delete a provider configuration.
    """
    # Load the configuration
    config = Config()
    
    # Delete the provider
    try:
        config.delete_provider(provider)
        click.echo(f"Provider {provider} deleted successfully.")
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)


def main():
    """
    Main entry point for the CLI.
    """
    try:
        cli()
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()