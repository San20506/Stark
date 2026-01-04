"""
Demo: Code Generation Agent
============================
Interactive demo of CodeAgent capabilities.
"""

import logging
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.progress import Progress, SpinnerColumn, TextColumn
import json

logging.basicConfig(level=logging.INFO)

console = Console()


def demo_simple_generation():
    """Demo simple function generation."""
    console.print("\n[bold cyan]═══ Simple Code Generation ═══[/bold cyan]\n")
    
    from agents.code_agent import get_code_agent
    
    agent = get_code_agent()
    
    requests = [
        "Create a function to calculate fibonacci numbers",
        "Create a function to check if a string is a palindrome",
        "Create a function to find the maximum value in a list",
    ]
    
    for request in requests:
        console.print(f"\n[yellow]Request:[/yellow] {request}")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Generating code...", total=None)
            
            result = agent.run(request)
            
            progress.update(task, completed=True)
        
        if result.success:
            data = json.loads(result.output)
            
            # Show generated code
            code_syntax = Syntax(data["code"], "python", theme="monokai", line_numbers=True)
            console.print(Panel(code_syntax, title="Generated Code", border_style="green"))
            
            # Show stats
            console.print(f"\n[dim]Iterations: {data.get('iterations', 1)} | "
                         f"Execution time: {data.get('execution_time', 0):.2f}s[/dim]")
        else:
            console.print(Panel(f"[red]Failed: {result.error}[/red]", border_style="red"))


def demo_auto_fixing():
    """Demo auto-fixing capabilities."""
    console.print("\n[bold magenta]═══ Auto-Fixing Demo ═══[/bold magenta]\n")
    
    from agents.code_agent import CodeAgent
    
    agent = CodeAgent(max_fix_attempts=3)
    
    # Request something that might need fixing
    request = "Create a binary search function with edge case handling"
    
    console.print(f"\n[yellow]Request:[/yellow] {request}")
    console.print("[dim]This may require multiple iterations...[/dim]\n")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Generating and testing...", total=None)
        
        result = agent.run(request)
        
        progress.update(task, completed=True)
    
    if result.success:
        data = json.loads(result.output)
        
        code_syntax = Syntax(data["code"], "python", theme="monokai", line_numbers=True)
        console.print(Panel(code_syntax, title="Final Code (After Fixing)", border_style="green"))
        
        console.print(f"\n[green]✓ Success after {data.get('iterations', 1)} iteration(s)[/green]")
        console.print(f"[dim]Total time: {data.get('execution_time', 0):.2f}s[/dim]")
    else:
        console.print(Panel(f"[red]Failed after all attempts: {result.error}[/red]", border_style="red"))


def demo_sandbox_safety():
    """Demo sandbox security."""
    console.print("\n[bold red]═══ Sandbox Safety Demo ═══[/bold red]\n")
    
    from agents.code_executor import get_code_executor
    
    executor = get_code_executor()
    
    dangerous_codes = [
        ("Forbidden import (os)", "import os\nos.system('ls')"),
        ("Forbidden import (subprocess)", "import subprocess\nsubprocess.run(['echo', 'hi'])"),
        ("Timeout protection", "import time\ntime.sleep(20)"),
    ]
    
    for name, code in dangerous_codes:
        console.print(f"\n[yellow]Test:[/yellow] {name}")
        
        result = executor.execute(code)
        
        if not result.success:
            console.print(f"[green]✓ Blocked: {result.error}[/green]")
        else:
            console.print(f"[red]✗ Should have been blocked![/red]")


def main():
    """Run all demos."""
    console.print(Panel(
        "[bold]STARK Code Generation  Agent Demo[/bold]\n\n"
        "Demonstrating AI-powered code generation with testing and auto-fixing.",
        border_style="bold blue",
    ))
    
    try:
        demo_simple_generation()
        demo_auto_fixing()
        demo_sandbox_safety()
        
        console.print("\n[bold green]✓ Demo complete![/bold green]\n")
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Demo interrupted[/yellow]\n")
    except Exception as e:
        console.print(f"\n[bold red]Error: {e}[/bold red]\n")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
