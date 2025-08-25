#!/usr/bin/env python3
"""
Test script for contact enrichment functionality
"""
import sys
from pathlib import Path
from rich.console import Console
from rich.table import Table

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from perplexity_client import PerplexityClient
from contact_enricher import ContactParser, ContactEnricher, EnrichmentExporter

console = Console()

def test_enrichment():
    """Test the enrichment functionality with sample data"""
    
    console.print("[bold cyan]Contact Enrichment Test[/bold cyan]\n")
    
    # Check for config
    if not Path("config.json").exists():
        console.print("[red]Error: config.json not found. Please set up your API keys first.[/red]")
        return
    
    # Load config
    config = Config("config.json")
    
    # Initialize Perplexity client
    client = PerplexityClient(
        api_key=config.perplexity_api_key,
        model=config.perplexity_model,
        rate_limit_delay=config.rate_limit_delay
    )
    
    # Parse sample contacts
    sample_file = "sample_contacts.csv"
    if not Path(sample_file).exists():
        console.print(f"[yellow]Creating sample contacts file: {sample_file}[/yellow]")
        # Create a minimal sample file
        with open(sample_file, 'w') as f:
            f.write("name,company,email,phone\n")
            f.write("Tim Cook,Apple,,\n")
            f.write("Satya Nadella,Microsoft,,\n")
            f.write("Sundar Pichai,Google,,\n")
    
    console.print(f"[cyan]Loading contacts from {sample_file}...[/cyan]")
    contacts = ContactParser.parse_file(sample_file)
    
    # Show original contacts
    console.print(f"\n[bold]Original Contacts ({len(contacts)} total):[/bold]")
    table = Table()
    table.add_column("Name", style="cyan")
    table.add_column("Company", style="magenta")
    table.add_column("Email", style="green")
    table.add_column("Phone", style="yellow")
    
    for contact in contacts[:5]:  # Show first 5
        table.add_row(
            contact.name or "-",
            contact.company or "-",
            contact.email or "Missing",
            contact.phone or "Missing"
        )
    
    console.print(table)
    
    # Count missing info
    missing_email = sum(1 for c in contacts if not c.email)
    missing_phone = sum(1 for c in contacts if not c.phone)
    
    console.print(f"\n[bold]Enrichment Opportunities:[/bold]")
    console.print(f"  • Missing emails: {missing_email}")
    console.print(f"  • Missing phones: {missing_phone}")
    
    # Test enrichment on first 3 contacts
    console.print("\n[cyan]Testing enrichment on first 3 contacts...[/cyan]")
    
    enricher = ContactEnricher(
        perplexity_client=client,
        rate_limit_delay=1.0,
        batch_size=3
    )
    
    # Enrich only first 3 for testing
    test_contacts = contacts[:3]
    results = enricher.enrich_contacts(test_contacts)
    
    # Show results
    console.print("\n[bold]Enrichment Results:[/bold]")
    results_table = Table()
    results_table.add_column("Name", style="cyan")
    results_table.add_column("Status", style="magenta")
    results_table.add_column("Found Email", style="green")
    results_table.add_column("Found Phone", style="yellow")
    results_table.add_column("Confidence", style="blue")
    
    for result in results:
        status_color = "green" if result.status == "enriched" else "red"
        results_table.add_row(
            result.original.name or result.original.company,
            f"[{status_color}]{result.status}[/{status_color}]",
            result.enriched.primary_email if result.enriched else "-",
            result.enriched.primary_phone if result.enriched else "-",
            f"{result.confidence:.2f}" if result.enriched else "-"
        )
    
    console.print(results_table)
    
    # Export results
    console.print("\n[cyan]Exporting results...[/cyan]")
    exporter = EnrichmentExporter()
    csv_file = exporter.export_results(results, "csv")
    console.print(f"[green]✓ Exported to: {csv_file}[/green]")
    
    # Test the new enrich_contact method
    console.print("\n[bold cyan]Testing Direct Enrichment Method:[/bold cyan]")
    
    test_result = client.enrich_contact(
        name="Elon Musk",
        company="Tesla",
        title="CEO",
        location="Austin, TX"
    )
    
    if test_result:
        console.print(f"[green]✓ Found contact information:[/green]")
        console.print(f"  Name: {test_result.name}")
        console.print(f"  Company: {test_result.company}")
        console.print(f"  Email: {test_result.primary_email}")
        console.print(f"  Phone: {test_result.primary_phone}")
        console.print(f"  Confidence: {test_result.confidence_score:.2f}")
    else:
        console.print("[yellow]No enrichment data found[/yellow]")

if __name__ == "__main__":
    test_enrichment()