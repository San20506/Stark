#!/usr/bin/env python3
"""
STARK CLI - Interactive Terminal Interface
===========================================
Native Linux terminal interface for the Adaptive Orchestrator.

Usage:
    python stark_cli.py
    python stark_cli.py --debug
"""

import sys
import time
import argparse
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.layout import Layout
from rich.text import Text
from rich.prompt import Prompt
from rich import box

from core.main import get_stark
from core.constants import TASK_MODELS

console = Console()


class StarkCLI:
    """Interactive terminal interface for STARK."""
    
    def __init__(self, debug: bool = False):
        self.debug = debug
        self.stark = None
        self.console = Console()
    
    def show_banner(self):
        """Display STARK banner."""
        banner = """
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║        ███████╗████████╗ █████╗ ██████╗ ██╗  ██╗         ║
║        ██╔════╝╚══██╔══╝██╔══██╗██╔══██╗██║ ██╔╝         ║
║        ███████╗   ██║   ███████║██████╔╝█████╔╝          ║
║        ╚════██║   ██║   ██╔══██║██╔══██╗██╔═██╗          ║
║        ███████║   ██║   ██║  ██║██║  ██║██║  ██╗         ║
║        ╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝         ║
║                                                           ║
║           Adaptive Orchestrator v0.1.0                    ║
║           Multi-Model Intelligent Routing                 ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
        """
        console.print(banner, style="bold cyan")
    
    def show_architecture(self):
        """Display system architecture."""
        arch = """
[bold cyan]System Architecture:[/bold cyan]

Query Input
    ↓
[yellow]TaskDetector[/yellow] (TF-IDF + Keywords)
    ↓
┌───────────────────────────────┐
│ Confidence > 0.6?             │
├───────────────────────────────┤
│ [green]YES[/green] → Direct Routing        │
│    • conversation → llama3.2   │
│    • code_* → qwen3:4b        │
│                               │
│ [yellow]NO[/yellow]  → AdaptiveRouter       │
│    • LLM Analysis             │
│    • Intent Detection         │
│    • Smart Selection          │
└───────────────────────────────┘
    ↓
[bold green]Response[/bold green]
        """
        console.print(Panel(arch, border_style="cyan", expand=False))
    
    def initialize_stark(self):
        """Initialize STARK system."""
        with console.status("[bold green]Initializing STARK...", spinner="dots"):
            self.stark = get_stark()
            self.stark.start()
        console.print("✓ STARK initialized\n", style="bold green")
    
    def process_query(self, query: str):
        """Process a query and display results."""
        start_time = time.time()
        
        # Show processing indicator
        with console.status(f"[bold yellow]Processing: [italic]{query}[/italic]", spinner="dots"):
            result = self.stark.predict(query)
        
        elapsed = time.time() - start_time
        
        # Determine model used
        model = TASK_MODELS.get(result.task, "unknown")
        routing_method = "Direct" if result.confidence >= 0.6 else "Adaptive Router"
        
        # Create results table
        table = Table(title="Routing Decision", box=box.ROUNDED, show_header=True, header_style="bold cyan")
        table.add_column("Metric", style="cyan", width=20)
        table.add_column("Value", style="white")
        
        table.add_row("Task Detected", f"[yellow]{result.task}[/yellow]")
        table.add_row("Confidence", f"[{'green' if result.confidence >= 0.6 else 'yellow'}]{result.confidence:.1%}[/]")
        table.add_row("Model Selected", f"[magenta]{model}[/magenta]")
        table.add_row("Routing Method", f"[blue]{routing_method}[/blue]")
        table.add_row("Latency", f"[red]{result.latency_ms:.0f}ms[/red]")
        table.add_row("Memory Stored", f"[green]{'Yes' if result.memory_stored else 'No'}[/green]")
        
        console.print(table)
        console.print()
        
        # Display response
        response_panel = Panel(
            result.response,
            title="[bold green]Response",
            border_style="green",
            expand=False
        )
        console.print(response_panel)
        console.print()
    
    def show_stats(self):
        """Display system statistics."""
        status = self.stark.status()
        
        stats_table = Table(title="System Statistics", box=box.ROUNDED)
        stats_table.add_column("Metric", style="cyan")
        stats_table.add_column("Value", style="white")
        
        stats_table.add_row("Running", f"[green]{'Yes' if status.running else 'No'}[/green]")
        stats_table.add_row("Queries Processed", str(status.queries_processed))
        stats_table.add_row("Memories Stored", str(status.memories_stored))
        
        if status.uptime_seconds:
            hours = status.uptime_seconds // 3600
            minutes = (status.uptime_seconds % 3600) // 60
            stats_table.add_row("Uptime", f"{hours}h {minutes}m")
        
        console.print(stats_table)
        console.print()
    
    def show_help(self):
        """Display help information."""
        help_text = """
[bold cyan]Available Commands:[/bold cyan]

[green]/help[/green]    - Show this help
[green]/stats[/green]   - Display system statistics
[green]/arch[/green]    - Show architecture diagram
[green]/clear[/green]   - Clear screen
[green]/quit[/green]    - Exit STARK

[bold cyan]Example Queries:[/bold cyan]

[yellow]• Hello STARK![/yellow]
  → Fast response, conversation model

[yellow]• Debug this IndexError[/yellow]
  → Thinking model, deep analysis

[yellow]• Explain Python decorators[/yellow]
  → Code explanation

[yellow]• Make me a sandwich[/yellow]
  → Edge case, router analysis
        """
        console.print(Panel(help_text, border_style="cyan", expand=False))
    
    def run(self):
        """Main interactive loop."""
        self.show_banner()
        console.print()
        self.show_architecture()
        console.print()
        
        self.initialize_stark()
        
        console.print("[dim]Type /help for commands, or enter a query. Ctrl+C to exit.[/dim]\n")
        
        try:
            while True:
                # Get user input
                try:
                    query = Prompt.ask("\n[bold cyan]STARK[/bold cyan]").strip()
                except (EOFError, KeyboardInterrupt):
                    break
                
                if not query:
                    continue
                
                # Handle commands
                if query.startswith('/'):
                    cmd = query.lower()
                    if cmd == '/help':
                        self.show_help()
                    elif cmd == '/stats':
                        self.show_stats()
                    elif cmd == '/arch':
                        self.show_architecture()
                    elif cmd == '/clear':
                        console.clear()
                        self.show_banner()
                    elif cmd == '/quit' or cmd == '/exit':
                        break
                    else:
                        console.print(f"[red]Unknown command: {query}[/red]")
                    continue
                
                # Process query
                try:
                    self.process_query(query)
                except Exception as e:
                    console.print(f"[red]Error: {e}[/red]")
                    if self.debug:
                        import traceback
                        traceback.print_exc()
        
        except KeyboardInterrupt:
            pass
        
        finally:
            console.print("\n[yellow]Shutting down STARK...[/yellow]")
            if self.stark:
                self.stark.stop()
            console.print("[green]Goodbye![/green]\n")


def main():
    parser = argparse.ArgumentParser(description="STARK CLI - Interactive Terminal Interface")
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    args = parser.parse_args()
    
    cli = StarkCLI(debug=args.debug)
    cli.run()


if __name__ == '__main__':
    main()
