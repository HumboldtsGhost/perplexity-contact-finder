"""
Smart Enrichment Engine - AI-powered contact discovery with Perplexity
"""
import csv
import json
import logging
import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.panel import Panel

from ai_assistant import AIAssistant, QuerySuggestion
from perplexity_client import PerplexityClient, ContactInfo
from config import Config

logger = logging.getLogger(__name__)
console = Console()

@dataclass
class EnrichmentJob:
    """Represents a complete enrichment job"""
    job_id: str
    companies: List[str]
    requirements: Dict
    queries: List[QuerySuggestion]
    results: List[ContactInfo] = field(default_factory=list)
    status: str = "pending"  # pending, running, completed, failed
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    total_queries: int = 0
    completed_queries: int = 0
    success_count: int = 0
    error_count: int = 0

class SmartEnrichmentEngine:
    """Main engine for AI-powered contact enrichment"""
    
    def __init__(self, config: Config):
        """Initialize the enrichment engine"""
        self.config = config
        
        # Initialize AI Assistant
        if not config.anthropic_api_key:
            raise ValueError("Anthropic API key is required for smart enrichment")
        self.ai_assistant = AIAssistant(
            api_key=config.anthropic_api_key,
            model=config.anthropic_model
        )
        
        # Initialize Perplexity Client
        if not config.perplexity_api_key:
            raise ValueError("Perplexity API key is required")
        self.perplexity_client = PerplexityClient(
            api_key=config.perplexity_api_key,
            model=config.perplexity_model,
            rate_limit_delay=config.rate_limit_delay
        )
        
        self.current_job: Optional[EnrichmentJob] = None
        self.job_history: List[EnrichmentJob] = []
    
    def parse_companies_file(self, file_path: str) -> Tuple[List[str], Dict[str, Any]]:
        """Parse companies from uploaded file and extract metadata
        Returns: (companies_list, metadata_dict)
        """
        file_path = Path(file_path)
        companies = []
        metadata = {
            'columns': [],
            'sample_data': [],
            'detected_type': None,
            'additional_context': {}
        }
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        extension = file_path.suffix.lower()
        
        try:
            if extension == '.csv':
                with open(file_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    metadata['columns'] = reader.fieldnames or []
                    
                    for i, row in enumerate(reader):
                        # Store first 3 rows as sample
                        if i < 3:
                            metadata['sample_data'].append(row)
                        
                        # Try common column names for company/organization
                        company = (row.get('School Name') or row.get('school_name') or
                                 row.get('company') or row.get('Company') or 
                                 row.get('organization') or row.get('Organization') or
                                 row.get('name') or row.get('Name') or
                                 row.get('school') or row.get('School'))
                        
                        # Add context from other columns
                        if company:
                            # Check if it's a school based on columns or content
                            if any('school' in str(col).lower() for col in metadata['columns']):
                                metadata['detected_type'] = 'schools'
                            
                            # Add location context if available
                            location_parts = []
                            if row.get('City'):
                                location_parts.append(row.get('City'))
                            if row.get('State'):
                                location_parts.append(row.get('State'))
                            
                            if location_parts:
                                full_company = f"{company.strip()} {' '.join(location_parts)}"
                            else:
                                full_company = company.strip()
                            
                            companies.append(full_company)
                    
                    # Analyze columns to provide context
                    if 'Grade' in ' '.join(metadata['columns']) or 'School' in ' '.join(metadata['columns']):
                        metadata['detected_type'] = 'educational_institutions'
                        metadata['additional_context']['grades'] = True
                    
                    if 'Charter' in metadata['columns']:
                        metadata['additional_context']['has_charter_info'] = True
                    
                    if 'District' in metadata['columns']:
                        metadata['additional_context']['has_district_info'] = True
            
            elif extension == '.txt':
                with open(file_path, 'r', encoding='utf-8') as f:
                    companies = [line.strip() for line in f if line.strip()]
                    metadata['detected_type'] = 'text_list'
            
            elif extension == '.json':
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        companies = [str(item).strip() for item in data]
                    elif isinstance(data, dict):
                        # Try to find companies array
                        companies = data.get('companies', data.get('organizations', []))
                    metadata['detected_type'] = 'json_data'
            
            else:
                raise ValueError(f"Unsupported file format: {extension}")
        
        except Exception as e:
            logger.error(f"Error parsing file: {str(e)}")
            raise
        
        # Remove duplicates while preserving order
        seen = set()
        unique_companies = []
        for company in companies:
            if company and company not in seen:
                seen.add(company)
                unique_companies.append(company)
        
        return unique_companies, metadata
    
    def start_interactive_session(self, companies: List[str] = None) -> EnrichmentJob:
        """Start an interactive session to understand requirements"""
        
        console.print("\n[bold cyan]🤖 AI-Powered Contact Discovery[/bold cyan]")
        console.print("[dim]I'll help you find the right contacts for your outreach[/dim]\n")
        
        # If no companies provided, ask if user wants to enter manually
        if not companies:
            console.print("[yellow]No companies list provided.[/yellow]")
            manual_input = Prompt.ask("Enter companies (comma-separated) or 'skip' to continue")
            
            if manual_input.lower() != 'skip':
                companies = [c.strip() for c in manual_input.split(',')]
        
        # Show company summary
        if companies:
            console.print(f"\n[green]✓ Loaded {len(companies)} companies/organizations[/green]")
            
            # Show sample
            sample = companies[:5]
            console.print("\n[bold]Sample entries:[/bold]")
            for i, company in enumerate(sample, 1):
                console.print(f"  {i}. {company}")
            
            if len(companies) > 5:
                console.print(f"  ... and {len(companies) - 5} more")
        
        # AI suggests roles based on companies with detailed analysis
        role_suggestions = {}
        selected_roles = []
        
        if companies:
            console.print("\n[cyan]🤖 Analyzing your organizations to suggest relevant contacts...[/cyan]")
            role_suggestions = self.ai_assistant.suggest_roles_for_industry(companies)
            
            if role_suggestions:
                # Show industry detection
                console.print(f"\n[bold green]Industry Detected: {role_suggestions.get('industry_type', 'Unknown')}[/bold green]")
                
                if role_suggestions.get('insights'):
                    console.print(f"[dim]{role_suggestions['insights']}[/dim]")
                
                # Show primary roles with reasons
                console.print("\n[bold]🎯 PRIMARY ROLES (Recommended):[/bold]")
                primary_roles = role_suggestions.get('primary_roles', [])
                for i, role_info in enumerate(primary_roles, 1):
                    console.print(f"  {i}. [cyan]{role_info['role']}[/cyan]")
                    console.print(f"     [dim]→ {role_info['reason']}[/dim]")
                
                # Show secondary roles
                console.print("\n[bold]📋 SECONDARY ROLES (Optional):[/bold]")
                secondary_roles = role_suggestions.get('secondary_roles', [])
                for i, role_info in enumerate(secondary_roles, 1):
                    console.print(f"  {i}. [yellow]{role_info['role']}[/yellow]")
                    console.print(f"     [dim]→ {role_info['reason']}[/dim]")
                
                # Quick selection options
                console.print("\n[bold]Quick Selection:[/bold]")
                console.print("  1. Use all PRIMARY roles (recommended)")
                console.print("  2. Use PRIMARY + SECONDARY roles")
                console.print("  3. Custom selection")
                console.print("  4. Enter your own roles")
                
                choice = Prompt.ask("Choose option", choices=["1", "2", "3", "4"], default="1")
                
                if choice == "1":
                    selected_roles = [r['role'] for r in primary_roles]
                    console.print(f"[green]✓ Selected PRIMARY roles: {', '.join(selected_roles)}[/green]")
                
                elif choice == "2":
                    selected_roles = [r['role'] for r in primary_roles] + [r['role'] for r in secondary_roles]
                    console.print(f"[green]✓ Selected ALL roles: {', '.join(selected_roles)}[/green]")
                
                elif choice == "3":
                    # Custom selection with checkboxes
                    console.print("\n[bold]Select roles to search for:[/bold]")
                    all_roles = primary_roles + secondary_roles
                    
                    for i, role_info in enumerate(all_roles, 1):
                        is_primary = role_info in primary_roles
                        default = is_primary  # Default to selecting primary roles
                        
                        role_type = "[PRIMARY]" if is_primary else "[SECONDARY]"
                        if Confirm.ask(f"  Include {role_info['role']} {role_type}?", default=default):
                            selected_roles.append(role_info['role'])
                    
                    if selected_roles:
                        console.print(f"\n[green]✓ Selected roles: {', '.join(selected_roles)}[/green]")
                    else:
                        console.print("[yellow]No roles selected, using defaults[/yellow]")
                        selected_roles = [r['role'] for r in primary_roles[:2]]
                
                elif choice == "4":
                    # Manual entry
                    pass  # Will fall through to manual prompt below
        
        # If no roles selected yet or choice 4, ask for manual input
        if not selected_roles:
            # Prepare default based on suggestions
            default_roles = ', '.join([r['role'] for r in role_suggestions.get('primary_roles', [])[:3]]) if role_suggestions else "CEO, Manager"
            
            roles_input = Prompt.ask(
                "\nEnter roles/positions to find (comma-separated)",
                default=default_roles
            )
            selected_roles = [r.strip() for r in roles_input.split(',')]
        
        roles = selected_roles
        
        # 2. Ask for contact types
        console.print("\n[bold]What contact information do you need?[/bold]")
        contact_types = []
        
        if Confirm.ask("  Email addresses?", default=True):
            contact_types.append("email")
        if Confirm.ask("  Phone numbers?", default=True):
            contact_types.append("phone")
        if Confirm.ask("  LinkedIn profiles?", default=False):
            contact_types.append("linkedin")
        if Confirm.ask("  Mailing addresses?", default=False):
            contact_types.append("address")
        
        # 3. Any additional criteria
        additional = Prompt.ask(
            "\nAny additional criteria? (e.g., 'senior level only', 'specific department')",
            default=""
        )
        
        # Build requirements dict
        requirements = {
            'roles': roles,
            'contact_types': contact_types,
            'additional_criteria': additional,
            'suggested_roles': suggested_roles
        }
        
        # Generate queries
        console.print("\n[cyan]Generating search queries...[/cyan]")
        queries = self.ai_assistant.generate_queries(
            companies=companies or ["General search"],
            requirements=requirements,
            max_queries_per_company=len(roles) if len(roles) <= 2 else 2
        )
        
        # Create job
        import uuid
        job = EnrichmentJob(
            job_id=str(uuid.uuid4())[:8],
            companies=companies or [],
            requirements=requirements,
            queries=queries,
            total_queries=len(queries)
        )
        
        self.current_job = job
        return job
    
    def preview_queries(self, job: EnrichmentJob, max_display: int = 10) -> List[QuerySuggestion]:
        """Preview and optionally edit queries before execution"""
        
        console.print(f"\n[bold]📝 Query Preview[/bold]")
        console.print(f"Generated {len(job.queries)} queries total\n")
        
        # Show sample queries
        sample_queries = job.queries[:max_display]
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("#", style="dim", width=4)
        table.add_column("Company", style="cyan", width=30)
        table.add_column("Role", style="yellow", width=20)
        table.add_column("Query", style="green", width=50)
        
        for i, query_suggestion in enumerate(sample_queries, 1):
            table.add_row(
                str(i),
                query_suggestion.company[:27] + "..." if len(query_suggestion.company) > 30 else query_suggestion.company,
                query_suggestion.role,
                query_suggestion.query[:47] + "..." if len(query_suggestion.query) > 50 else query_suggestion.query
            )
        
        console.print(table)
        
        if len(job.queries) > max_display:
            console.print(f"\n[dim]... and {len(job.queries) - max_display} more queries[/dim]")
        
        # Options for editing
        console.print("\n[bold]Options:[/bold]")
        console.print("  1. Run all queries as shown")
        console.print("  2. Edit specific queries")
        console.print("  3. Regenerate all queries")
        console.print("  4. Add custom queries")
        console.print("  5. Export queries for review")
        
        choice = Prompt.ask("Choose option", choices=["1", "2", "3", "4", "5"], default="1")
        
        if choice == "1":
            return job.queries
        
        elif choice == "2":
            # Edit specific queries
            while True:
                query_num = Prompt.ask("Enter query number to edit (or 'done')")
                if query_num.lower() == 'done':
                    break
                
                try:
                    idx = int(query_num) - 1
                    if 0 <= idx < len(job.queries):
                        old_query = job.queries[idx].query
                        new_query = Prompt.ask(f"Edit query", default=old_query)
                        job.queries[idx].query = new_query
                        console.print("[green]✓ Query updated[/green]")
                except (ValueError, IndexError):
                    console.print("[red]Invalid query number[/red]")
        
        elif choice == "3":
            # Regenerate all queries
            console.print("[cyan]Regenerating queries...[/cyan]")
            job.queries = self.ai_assistant.generate_queries(
                companies=job.companies,
                requirements=job.requirements
            )
            return self.preview_queries(job)  # Recursive call to preview again
        
        elif choice == "4":
            # Add custom queries
            custom_query = Prompt.ask("Enter custom query")
            for company in job.companies[:5]:  # Add for first 5 companies as example
                job.queries.append(QuerySuggestion(
                    query=f"{custom_query} for {company}",
                    role="Custom",
                    company=company,
                    contact_types=job.requirements['contact_types'],
                    confidence=0.8,
                    reasoning="User-defined custom query"
                ))
        
        elif choice == "5":
            # Export queries
            export_file = f"queries_{job.job_id}.txt"
            with open(export_file, 'w') as f:
                for q in job.queries:
                    f.write(f"{q.company}\t{q.role}\t{q.query}\n")
            console.print(f"[green]✓ Exported to {export_file}[/green]")
        
        return job.queries
    
    def execute_enrichment(self, job: EnrichmentJob, batch_size: int = 10) -> List[ContactInfo]:
        """Execute the enrichment job with progress tracking"""
        
        console.print(f"\n[bold green]🚀 Starting Enrichment Job {job.job_id}[/bold green]")
        console.print(f"Processing {len(job.queries)} queries in batches of {batch_size}\n")
        
        job.status = "running"
        results = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TextColumn("[bold blue]{task.fields[status]}"),
            console=console
        ) as progress:
            
            task = progress.add_task(
                f"Enriching contacts...", 
                total=len(job.queries),
                status="Starting..."
            )
            
            # Process in batches
            for i in range(0, len(job.queries), batch_size):
                batch = job.queries[i:i + batch_size]
                batch_results = []
                
                for query_suggestion in batch:
                    progress.update(
                        task, 
                        advance=1,
                        status=f"Searching: {query_suggestion.company[:30]}..."
                    )
                    
                    try:
                        # Execute Perplexity search
                        contacts = self.perplexity_client.search_contact(
                            query=query_suggestion.query,
                            additional_context=f"Looking for {query_suggestion.role} at {query_suggestion.company}"
                        )
                        
                        if contacts:
                            # Add metadata to contacts
                            for contact in contacts:
                                contact.notes = f"Role: {query_suggestion.role} | Query: {query_suggestion.query}"
                                # Set company if not already set
                                if not contact.company:
                                    contact.company = query_suggestion.company
                            
                            batch_results.extend(contacts)
                            job.success_count += len(contacts)
                        
                        job.completed_queries += 1
                        
                    except Exception as e:
                        logger.error(f"Error processing query for {query_suggestion.company}: {str(e)}")
                        job.error_count += 1
                        job.completed_queries += 1
                    
                    # Rate limiting
                    time.sleep(self.config.rate_limit_delay)
                
                results.extend(batch_results)
                
                # Update progress status
                progress.update(
                    task,
                    status=f"Found {len(results)} contacts so far..."
                )
        
        # Update job
        job.results = results
        job.status = "completed"
        job.completed_at = datetime.now().isoformat()
        
        # Show summary
        self._show_enrichment_summary(job)
        
        return results
    
    def _show_enrichment_summary(self, job: EnrichmentJob):
        """Display summary of enrichment job"""
        
        console.print(f"\n[bold]✅ Enrichment Job {job.job_id} Complete[/bold]")
        
        # Create summary table
        table = Table(show_header=False, box=None)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="yellow")
        
        table.add_row("Total Queries", str(job.total_queries))
        table.add_row("Completed", str(job.completed_queries))
        table.add_row("Contacts Found", str(len(job.results)))
        table.add_row("Success Rate", f"{(job.success_count / job.total_queries * 100):.1f}%" if job.total_queries > 0 else "0%")
        table.add_row("Errors", str(job.error_count))
        
        console.print(table)
        
        # Show sample results
        if job.results:
            console.print("\n[bold]Sample Contacts Found:[/bold]")
            sample_table = Table(show_header=True, header_style="bold magenta")
            sample_table.add_column("Name", style="cyan")
            sample_table.add_column("Company", style="yellow")
            sample_table.add_column("Email", style="green")
            sample_table.add_column("Phone", style="blue")
            
            for contact in job.results[:5]:
                sample_table.add_row(
                    contact.name or "-",
                    contact.company or "-",
                    contact.primary_email or "-",
                    contact.primary_phone or "-"
                )
            
            console.print(sample_table)
            
            if len(job.results) > 5:
                console.print(f"[dim]... and {len(job.results) - 5} more contacts[/dim]")
    
    def export_results(self, job: EnrichmentJob, format: str = "csv") -> str:
        """Export enrichment results"""
        from data_exporter import DataExporter
        
        exporter = DataExporter(output_dir="enrichment_output")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"enriched_{job.job_id}_{timestamp}"
        
        if format == "csv":
            filepath = exporter.export_to_csv(job.results, f"{filename}.csv")
        elif format == "excel":
            filepath = exporter.export_to_excel(job.results, f"{filename}.xlsx")
        elif format == "json":
            filepath = exporter.export_to_json(job.results, f"{filename}.json")
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        console.print(f"\n[green]✓ Exported {len(job.results)} contacts to {filepath}[/green]")
        return filepath