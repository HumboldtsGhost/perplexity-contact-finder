#!/usr/bin/env python3
"""
Smart Contact Finder - AI-powered contact discovery with Perplexity
Main entry point for the application
"""
import argparse
import sys
import os
from pathlib import Path
from typing import List, Optional
import logging

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table
import questionary
import pyfiglet

from config import Config
from smart_enrichment import SmartEnrichmentEngine
from data_exporter import DataExporter

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('smart_finder.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

console = Console()

def show_welcome():
    """Display welcome screen"""
    console.clear()
    
    # ASCII art header
    ascii_art = pyfiglet.figlet_format("Smart Finder", font="slant")
    console.print(f"[bold cyan]{ascii_art}[/bold cyan]")
    
    console.print("[bold]AI-Powered Contact Discovery System[/bold]")
    console.print("[dim]Find the right contacts with intelligent search[/dim]\n")
    
    # Features panel
    features = """
    ✨ AI understands what contacts you need
    🔍 Generates optimized Perplexity searches
    📊 Bulk enrichment with progress tracking
    ✅ Preview and edit queries before running
    📁 Export to CSV, Excel, or JSON
    """
    
    console.print(Panel(features, title="Features", border_style="cyan"))

def setup_config():
    """Interactive configuration setup"""
    console.print("\n[bold]🔧 Configuration Setup[/bold]\n")
    
    config = Config()
    
    # Check for existing config
    if Path("config.json").exists():
        console.print("[green]✓ Found existing configuration[/green]")
        config = Config("config.json")
    
    # Check required API keys
    missing_keys = []
    
    if not config.perplexity_api_key:
        missing_keys.append("Perplexity")
    if not config.anthropic_api_key:
        missing_keys.append("Anthropic")
    
    if missing_keys:
        console.print(f"[yellow]⚠️  Missing API keys: {', '.join(missing_keys)}[/yellow]\n")
        
        if Confirm.ask("Would you like to set up API keys now?"):
            # Perplexity API key
            if not config.perplexity_api_key:
                key = Prompt.ask("Enter your Perplexity API key", password=True)
                config.set_api_key('perplexity', key)
            
            # Anthropic API key
            if not config.anthropic_api_key:
                console.print("\n[dim]Default Anthropic key will be used if not provided[/dim]")
                key = Prompt.ask("Enter your Anthropic API key (or press Enter for default)", 
                                password=True, default="")
                if key:
                    config.set_api_key('anthropic', key)
                else:
                    # Use the default key provided by user
                    pass  # User needs to set their own API key
            
            # Save configuration
            config.save_to_file()
            console.print("\n[green]✓ Configuration saved[/green]")
    
    # Set default Anthropic key if still missing
    if not config.anthropic_api_key:
        pass  # User needs to set their own API key
    
    return config

def main_menu():
    """Display main menu and get user choice"""
    console.print("\n[bold]Main Menu[/bold]")
    
    choices = [
        "🔍 Find contacts with uploaded list",
        "✍️  Find contacts with manual entry",
        "📋 View previous searches",
        "⚙️  Configure API keys",
        "❓ Help",
        "❌ Exit"
    ]
    
    choice = questionary.select(
        "What would you like to do?",
        choices=choices
    ).ask()
    
    return choice

def run_enrichment_with_file(engine: SmartEnrichmentEngine):
    """Run enrichment with uploaded file"""
    console.print("\n[bold]📁 Upload Company List[/bold]")
    
    # Get file path
    file_path = Prompt.ask("Enter path to company list (CSV, TXT, or JSON)")
    
    if not Path(file_path).exists():
        console.print(f"[red]❌ File not found: {file_path}[/red]")
        return
    
    try:
        # Parse companies
        console.print(f"\n[cyan]Loading companies from {file_path}...[/cyan]")
        companies, metadata = engine.parse_companies_file(file_path)
        
        if not companies:
            console.print("[yellow]No companies found in file[/yellow]")
            return
        
        console.print(f"[green]✓ Loaded {len(companies)} companies[/green]")
        
        # Show detected type if available
        if metadata.get('detected_type'):
            console.print(f"[cyan]📊 Detected type: {metadata['detected_type']}[/cyan]")
        
        if metadata.get('columns'):
            console.print(f"[dim]Columns found: {', '.join(metadata['columns'][:5])}{'...' if len(metadata['columns']) > 5 else ''}[/dim]")
        
        # Start interactive session
        job = engine.start_interactive_session(companies)
        
        # Preview and edit queries
        job.queries = engine.preview_queries(job)
        
        # Confirm execution
        console.print(f"\n[bold]Ready to execute {len(job.queries)} queries[/bold]")
        if not Confirm.ask("Proceed with enrichment?"):
            console.print("[yellow]Enrichment cancelled[/yellow]")
            return
        
        # Execute enrichment
        results = engine.execute_enrichment(job)
        
        # Export results
        if results and Confirm.ask("\nExport results?"):
            format_choice = questionary.select(
                "Choose export format:",
                choices=["CSV", "Excel", "JSON", "All formats"]
            ).ask()
            
            if format_choice == "All formats":
                engine.export_results(job, "csv")
                engine.export_results(job, "excel")
                engine.export_results(job, "json")
            else:
                engine.export_results(job, format_choice.lower())
    
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        logger.error(f"Enrichment error: {str(e)}", exc_info=True)

def run_enrichment_manual(engine: SmartEnrichmentEngine):
    """Run enrichment with manual entry"""
    console.print("\n[bold]✍️ Manual Contact Search[/bold]")
    
    # Get search criteria directly
    console.print("\n[dim]Describe what you're looking for in natural language[/dim]")
    search_description = Prompt.ask(
        "What contacts do you need?",
        default="Find CEOs and CTOs at tech companies in San Francisco with email and phone"
    )
    
    # Let AI understand the requirements
    requirements = engine.ai_assistant.understand_requirements(search_description)
    
    # Show interpreted requirements
    console.print("\n[bold]I understood you're looking for:[/bold]")
    console.print(f"  Roles: {', '.join(requirements['roles'])}")
    console.print(f"  Contact info: {', '.join(requirements['contact_types'])}")
    if requirements.get('industry_context'):
        console.print(f"  Context: {requirements['industry_context']}")
    
    # Ask for specific companies or general search
    company_input = Prompt.ask(
        "\nEnter specific companies (comma-separated) or 'general' for broad search",
        default="general"
    )
    
    companies = []
    if company_input.lower() != "general":
        companies = [c.strip() for c in company_input.split(',')]
    
    # Generate queries
    if companies:
        job = engine.start_interactive_session(companies)
    else:
        # For general search, create generic queries
        console.print("\n[cyan]Generating search queries...[/cyan]")
        generic_queries = []
        for role in requirements['roles'][:3]:
            query = f"Find {role} {' '.join(requirements['contact_types'])} contact information {requirements.get('industry_context', '')}"
            generic_queries.append(query)
        
        # Create a simple job
        import uuid
        from ai_assistant import QuerySuggestion
        job = engine.current_job = type('obj', (object,), {
            'job_id': str(uuid.uuid4())[:8],
            'companies': [],
            'requirements': requirements,
            'queries': [QuerySuggestion(
                query=q,
                role=requirements['roles'][0] if requirements['roles'] else "Contact",
                company="General Search",
                contact_types=requirements['contact_types'],
                confidence=0.8,
                reasoning="General search query"
            ) for q in generic_queries],
            'total_queries': len(generic_queries),
            'results': [],
            'status': 'pending',
            'completed_queries': 0,
            'success_count': 0,
            'error_count': 0
        })()
    
    # Preview and execute
    job.queries = engine.preview_queries(job)
    
    if Confirm.ask("\nProceed with search?"):
        results = engine.execute_enrichment(job)
        
        if results and Confirm.ask("\nExport results?"):
            format_choice = questionary.select(
                "Choose export format:",
                choices=["CSV", "Excel", "JSON"]
            ).ask()
            engine.export_results(job, format_choice.lower())

def show_help():
    """Display help information"""
    console.print("\n[bold]📚 Help & Documentation[/bold]\n")
    
    help_text = """
    [bold]Getting Started:[/bold]
    1. Set up your API keys (Perplexity required, Anthropic optional)
    2. Choose to upload a company list or enter search manually
    3. Tell the AI what contacts you're looking for
    4. Review and edit the generated queries
    5. Run the enrichment and export results
    
    [bold]File Formats:[/bold]
    • CSV: Must have a column named 'company', 'Company', or 'organization'
    • TXT: One company per line
    • JSON: Array of strings or object with 'companies' array
    
    [bold]Tips:[/bold]
    • Be specific about roles (e.g., "Principal" for schools, "CEO" for companies)
    • The AI will suggest appropriate roles based on your company list
    • You can edit any query before running it
    • Export to Excel for best formatting
    
    [bold]API Keys:[/bold]
    • Perplexity: Get at https://www.perplexity.ai/settings/api
    • Anthropic: Optional, enhances AI capabilities
    """
    
    console.print(Panel(help_text, title="Help", border_style="cyan"))
    
    Prompt.ask("\nPress Enter to continue")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Smart Contact Finder - AI-powered contact discovery')
    
    parser.add_argument('-f', '--file', help='Company list file (CSV, TXT, or JSON)')
    parser.add_argument('-o', '--output', choices=['csv', 'excel', 'json'], 
                       default='csv', help='Output format')
    parser.add_argument('--setup', action='store_true', help='Run configuration setup')
    parser.add_argument('--no-preview', action='store_true', 
                       help='Skip query preview and run immediately')
    
    args = parser.parse_args()
    
    # Show welcome
    show_welcome()
    
    # Setup configuration
    if args.setup:
        setup_config()
        return
    
    # Load configuration
    try:
        config = setup_config()
    except Exception as e:
        console.print(f"[red]Configuration error: {str(e)}[/red]")
        return
    
    # Initialize engine
    try:
        engine = SmartEnrichmentEngine(config)
    except ValueError as e:
        console.print(f"[red]Initialization error: {str(e)}[/red]")
        console.print("[yellow]Run with --setup to configure API keys[/yellow]")
        return
    
    # If file provided via command line, process it
    if args.file:
        try:
            companies = engine.parse_companies_file(args.file)
            job = engine.start_interactive_session(companies)
            
            if not args.no_preview:
                job.queries = engine.preview_queries(job)
            
            results = engine.execute_enrichment(job)
            
            if results:
                engine.export_results(job, args.output)
        except Exception as e:
            console.print(f"[red]Error: {str(e)}[/red]")
        return
    
    # Interactive mode
    while True:
        choice = main_menu()
        
        if not choice or "Exit" in choice:
            console.print("\n[bold green]Thanks for using Smart Contact Finder! 👋[/bold green]")
            break
        
        elif "uploaded list" in choice:
            run_enrichment_with_file(engine)
        
        elif "manual entry" in choice:
            run_enrichment_manual(engine)
        
        elif "previous searches" in choice:
            console.print("[yellow]Search history not yet implemented[/yellow]")
        
        elif "Configure" in choice:
            setup_config()
            # Reinitialize engine with new config
            config = Config("config.json")
            engine = SmartEnrichmentEngine(config)
        
        elif "Help" in choice:
            show_help()

if __name__ == "__main__":
    main()