"""
Demo: Autonomous Multi-Agent Routing
=====================================
Demonstration of the Router-Arbiter autonomous agent system.
"""

import logging
import json
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.tree import Tree

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

console = Console()


def demo_fast_path():
    """Demonstrate fast path routing."""
    console.print("\n[bold cyan]═══ Fast Path Demo ═══[/bold cyan]\n")
    
    from agents.autonomous_orchestrator import get_autonomous_orchestrator
    
    orchestrator = get_autonomous_orchestrator()
    
    queries = [
        "Hello!",
        "What is Python?",
        "Tell me about STARK",
    ]
    
    for query in queries:
        console.print(f"\n[yellow]Query:[/yellow] {query}")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Processing...", total=None)
            
            result = orchestrator.predict(query)
            
            progress.update(task, completed=True)
        
        console.print(Panel(
            f"[green]Response:[/green] {result['response'][:200]}...\n\n"
            f"[dim]Source: {result.get('source', 'unknown')} | "
            f"Latency: {result['latency_ms']:.0f}ms | "
            f"Path: {result.get('path', 'unknown')}[/dim]",
            title="Result",
            border_style="green",
        ))


def demo_deep_path():
    """Demonstrate deep path routing."""
    console.print("\n[bold magenta]═══ Deep Path Demo ═══[/bold magenta]\n")
    
    from agents.autonomous_orchestrator import get_autonomous_orchestrator
    
    orchestrator = get_autonomous_orchestrator()
    
    queries = [
        "Create a plan to build a todo list app",
        "How would you implement a binary search tree?",
        "Design a system architecture for a chat application",
    ]
    
    for query in queries:
        console.print(f"\n[yellow]Query:[/yellow] {query}")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Planning...", total=None)
            
            result = orchestrator.predict(query)
            
            progress.update(task, completed=True)
        
        console.print(Panel(
            f"[green]Response:[/green] {result['response'][:300]}...\n\n"
            f"[dim]Source: {result.get('source', 'unknown')} | "
            f"Latency: {result['latency_ms']:.0f}ms | "
            f"Path: {result.get('path', 'unknown')}[/dim]",
            title="Result",
            border_style="magenta",
        ))


def demo_arbiter_selection():
    """Demonstrate arbiter selection between paths."""
    console.print("\n[bold blue]═══ Arbiter Selection Demo ═══[/bold blue]\n")
    
    from agents.specialists import ArbiterAgent
    
    arbiter = ArbiterAgent()
    
    # Simulate candidates from fast and deep paths
    candidates = [
        {
            "answer": "Python is a programming language.",
            "confidence": 0.7,
            "source": "fast",
        },
        {
            "answer": "Python is a high-level, interpreted programming language known for its simplicity and readability. Created by Guido van Rossum in 1991.",
            "confidence": 0.9,
            "source": "deep",
        },
    ]
    
    console.print("[yellow]Candidates:[/yellow]")
    for i, candidate in enumerate(candidates, 1):
        console.print(f"\n{i}. [cyan]{candidate['source']}[/cyan] (confidence: {candidate['confidence']})")
        console.print(f"   {candidate['answer'][:100]}...")
    
    result = arbiter.run("What is Python?", {"candidates": candidates})
    
    if result.success:
        data = json.loads(result.output)
        console.print(Panel(
            f"[green]Selected:[/green] {data['source']} path\n"
            f"[dim]Confidence: {data['confidence']} | "
            f"Alternatives: {data['alternatives']}[/dim]",
            title="Arbiter Decision",
            border_style="blue",
        ))


def demo_agent_stats():
    """Show agent statistics."""
    console.print("\n[bold white]═══ Agent Statistics ═══[/bold white]\n")
    
    from agents.autonomous_orchestrator import get_autonomous_orchestrator
    
    orchestrator = get_autonomous_orchestrator()
    
    stats = orchestrator.get_stats()
    
    tree = Tree("[bold]Autonomous Orchestrator Stats[/bold]")
    tree.add(f"Total Agents: {stats['total_agents']}")
    tree.add(f"Total Executions: {stats['total_executions']}")
    
    agents_tree = tree.add("[cyan]Agents[/cyan]")
    for agent_name, agent_stats in stats.get("agents", {}).items():
        agent_node = agents_tree.add(f"[yellow]{agent_name}[/yellow]")
        agent_node.add(f"Type: {agent_stats['type']}")
        agent_node.add(f"Executions: {agent_stats['executions']}")
        agent_node.add(f"Success Rate: {agent_stats['success_rate']:.1%}")
        if agent_stats['executions'] > 0:
            agent_node.add(f"Avg Time: {agent_stats['avg_time_ms']:.0f}ms")
    
    console.print(tree)


def main():
    """Run all demos."""
    console.print(Panel(
        "[bold]STARK Autonomous Multi-Agent System Demo[/bold]\n\n"
        "Demonstrating Router-Arbiter architecture with Fast and Deep paths.",
        border_style="bold blue",
    ))
    
    try:
        demo_fast_path()
        demo_deep_path()
        demo_arbiter_selection()
        demo_agent_stats()
        
        console.print("\n[bold green]✓ Demo complete![/bold green]\n")
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Demo interrupted[/yellow]\n")
    except Exception as e:
        console.print(f"\n[bold red]Error: {e}[/bold red]\n")
        logger.error("Demo failed", exc_info=True)


if __name__ == "__main__":
    main()
