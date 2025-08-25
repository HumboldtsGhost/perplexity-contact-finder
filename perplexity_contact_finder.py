#!/usr/bin/env python3
"""
Perplexity Contact Finder - Find and verify contact information
"""
import argparse
import json
import time
import logging
from pathlib import Path
from typing import List, Optional, Dict
import sys
import os
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.panel import Panel
from rich.table import Table
from rich import print as rprint
from rich.prompt import Prompt, Confirm
import questionary
import pyfiglet
from datetime import datetime

from config import Config
from perplexity_client import PerplexityClient, ContactInfo
from email_verifier import EmailVerificationService
from phone_verifier import PhoneVerificationService
from data_exporter import DataExporter
from enhanced_search import EnhancedSearchStrategy
from output_selector import OutputSelector
from contact_enricher import ContactParser, ContactEnricher, EnrichmentExporter

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('contact_finder.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

console = Console()

# Search templates for different industries
SEARCH_TEMPLATES = {
    "local_businesses": {
        "name": "Local Businesses & Services",
        "description": "Find local business owners and service providers",
        "examples": [
            "list of {service_type} companies in {city} {state} with owner names and contact info",
            "{service_type} business owners {city} {state} email and phone directory",
            "all {service_type} contractors {city} area owner contact details",
            "top 10 {service_type} businesses {city} {state} decision maker contacts",
            "{service_type} company owners association {city} member directory"
        ],
        "fields": ["service_type", "city", "state", "county"],
        "multi_result": True
    },
    "smb_by_industry": {
        "name": "Small & Medium Businesses",
        "description": "Find SMB owners and managers by industry/location",
        "examples": [
            "{industry} small business owners {city} {state} contacts",
            "all {industry} companies under 50 employees {state}",
            "{industry} SMB owners association {region} member list",
            "independent {industry} businesses {city} owner contacts",
            "{industry} franchise owners {state} contact information"
        ],
        "fields": ["industry", "city", "state", "region"],
        "multi_result": True
    },
    "contractors_trades": {
        "name": "Contractors & Trade Services",
        "description": "Find contractors, builders, and trade professionals",
        "examples": [
            "list of {trade} contractors {city} {state} with business owner contacts",
            "licensed {trade} company owners {county} county email directory",
            "{trade} contractor association {city} member list with emails",
            "top rated {trade} businesses {city} owner names and phone numbers",
            "all {trade} service companies {city} {state} decision maker contacts"
        ],
        "fields": ["trade", "city", "state", "county"],
        "multi_result": True
    },
    "retail_restaurants": {
        "name": "Retail & Restaurant Businesses",
        "description": "Find retail store and restaurant owners/managers",
        "examples": [
            "{business_type} owners {city} {state} contact list",
            "all {business_type} managers {shopping_area} contact info",
            "independent {business_type} {city} owner emails",
            "{cuisine_type} restaurant owners {city} contacts",
            "franchise {business_type} owners {state} directory"
        ],
        "fields": ["business_type", "city", "state", "shopping_area", "cuisine_type"],
        "multi_result": True
    },
    "professional_services": {
        "name": "Professional Services",
        "description": "Find lawyers, accountants, consultants, etc.",
        "examples": [
            "{profession} firms {city} {state} partner contacts",
            "independent {profession} {city} email list",
            "{specialty} {profession} {state} contact directory",
            "small {profession} practices {county} owner info",
            "{profession} association {state} member contacts"
        ],
        "fields": ["profession", "specialty", "city", "state", "county"],
        "multi_result": True
    },
    "real_estate": {
        "name": "Real Estate Professionals",
        "description": "Find realtors, brokers, property managers",
        "examples": [
            "real estate brokers {city} {state} contact list",
            "property management companies {city} owner contacts",
            "commercial real estate agents {city} emails",
            "{property_type} developers {state} contact info",
            "real estate investors {city} contact directory"
        ],
        "fields": ["city", "state", "property_type"],
        "multi_result": True
    },
    "healthcare_providers": {
        "name": "Healthcare & Medical Practices",
        "description": "Find doctors, dentists, clinics, care facilities",
        "examples": [
            "{specialty} doctors {city} {state} practice contacts",
            "dental offices {city} owner contact information",
            "{care_type} facilities {county} administrator emails",
            "private practice {specialty} {state} contact list",
            "medical clinics {city} manager directory"
        ],
        "fields": ["specialty", "care_type", "city", "state", "county"],
        "multi_result": True
    },
    "business_associations": {
        "name": "Business Associations & Chambers",
        "description": "Find chamber of commerce and business groups",
        "examples": [
            "{city} chamber of commerce board members contacts",
            "{industry} association {state} leadership emails",
            "business networking groups {city} organizer contacts",
            "{city} downtown business association member list",
            "small business alliance {state} directory"
        ],
        "fields": ["city", "state", "industry"],
        "multi_result": True
    },
    "government": {
        "name": "Government Officials",
        "description": "Find government contacts at any level",
        "examples": [
            "{level} government {department} {location} contacts",
            "{title} of {location} contact information",
            "{location} {office} staff directory",
            "all {location} {position} email addresses"
        ],
        "fields": ["level", "department", "location", "title", "office", "position"],
        "multi_result": True
    },
    "nonprofit": {
        "name": "Nonprofit Organizations",
        "description": "Find nonprofit leaders by cause or region",
        "examples": [
            "{cause} nonprofit directors {location} contacts",
            "{organization_type} {location} leadership emails",
            "community organizations {city} contact list",
            "{cause} foundations {state} board members"
        ],
        "fields": ["cause", "location", "city", "state", "organization_type"],
        "multi_result": True
    },
    "custom_search": {
        "name": "Custom Search",
        "description": "Enter your own search query for any type of contact",
        "examples": [
            "Enter any search query for contact information"
        ],
        "fields": [],
        "multi_result": True
    }
}

class ContactFinder:
    """Main contact finder application"""
    
    def __init__(self, config_file: str = 'config.json'):
        """Initialize the contact finder"""
        self.config_file = config_file
        self.config = Config(config_file)
        
        # Validate required API keys
        if not self.config.get_api_key('perplexity'):
            raise ValueError("Perplexity API key is required. Set it in config.json or PERPLEXITY_API_KEY environment variable.")
        
        # Initialize services
        self.perplexity = PerplexityClient(
            api_key=self.config.get_api_key('perplexity'),
            rate_limit_delay=self.config.get_setting('rate_limit_delay'),
            max_retries=self.config.get_setting('max_retries')
        )
        
        self.email_verifier = EmailVerificationService(self.config)
        self.phone_verifier = PhoneVerificationService(self.config)
        self.exporter = DataExporter()
        
        # State management for resume capability
        self.state_file = Path('contact_finder_state.json')
        self.processed_queries = set()
        self.results = []
        
    def load_state(self):
        """Load previous state for resume capability"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                    self.processed_queries = set(state.get('processed_queries', []))
                    # Load previous results
                    for contact_data in state.get('results', []):
                        contact = ContactInfo(**contact_data)
                        self.results.append(contact)
                logger.info(f"Loaded state: {len(self.processed_queries)} queries processed, {len(self.results)} results")
                return True
            except Exception as e:
                logger.error(f"Error loading state: {e}")
        return False
    
    def save_state(self):
        """Save current state for resume capability"""
        try:
            state = {
                'processed_queries': list(self.processed_queries),
                'results': [
                    {
                        'name': c.name,
                        'company': c.company,
                        'primary_email': c.primary_email,
                        'alternate_emails': c.alternate_emails,
                        'primary_phone': c.primary_phone,
                        'alternate_phones': c.alternate_phones,
                        'sources': c.sources,
                        'confidence_score': c.confidence_score,
                        'verification_status': c.verification_status,
                        'notes': c.notes,
                        'date_found': c.date_found
                    }
                    for c in self.results
                ]
            }
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving state: {e}")
    
    def find_contacts(self, queries: List[str], resume: bool = False) -> List[ContactInfo]:
        """Find contacts for a list of queries"""
        if resume:
            self.load_state()
            logger.info(f"Resuming from previous run...")
        
        # Filter out already processed queries
        remaining_queries = [q for q in queries if q not in self.processed_queries]
        
        if not remaining_queries:
            logger.info("All queries already processed")
            return self.results
        
        logger.info(f"Processing {len(remaining_queries)} queries...")
        
        batch_size = self.config.get_setting('batch_size')
        
        for i in range(0, len(remaining_queries), batch_size):
            batch = remaining_queries[i:i + batch_size]
            logger.info(f"Processing batch {i//batch_size + 1} of {(len(remaining_queries)-1)//batch_size + 1}")
            
            for query in batch:
                try:
                    # Search for contacts (returns multiple)
                    logger.info(f"Searching for: {query}")
                    contacts = self.perplexity.search_contact(query)
                    
                    if contacts:
                        logger.info(f"Found {len(contacts)} contacts for: {query}")
                        for contact in contacts:
                            # Verify emails
                            self.email_verifier.verify_all_emails(contact)
                            
                            # Verify phones
                            self.phone_verifier.verify_all_phones(contact)
                            
                            # Add to results
                            self.results.append(contact)
                            logger.info(f"  - {contact.name} at {contact.company} - {contact.primary_email} (Confidence: {contact.confidence_score:.2f})")
                    else:
                        logger.warning(f"No results for: {query}")
                    
                    # Mark as processed
                    self.processed_queries.add(query)
                    
                    # Save state after each successful query
                    self.save_state()
                    
                except Exception as e:
                    logger.error(f"Error processing {query}: {e}")
                    continue
            
            # Respect rate limits between batches
            if i + batch_size < len(remaining_queries):
                time.sleep(2)
        
        return self.results
    
    def export_results(self, format: str = 'both') -> List[str]:
        """Export results in specified format"""
        exported_files = []
        
        if format in ['csv', 'both']:
            # Standard CSV
            csv_file = self.exporter.export_to_csv(self.results)
            exported_files.append(csv_file)
            
            # Apollo CSV
            apollo_file = self.exporter.export_to_apollo_csv(self.results)
            exported_files.append(apollo_file)
        
        if format in ['json', 'both']:
            json_file = self.exporter.export_to_json(self.results)
            exported_files.append(json_file)
        
        # Print summary
        self.exporter.print_summary(self.results)
        
        return exported_files
    
    def clear_state(self):
        """Clear saved state"""
        if self.state_file.exists():
            self.state_file.unlink()
            logger.info("Cleared saved state")

def load_queries(input_file: str) -> List[str]:
    """Load queries from a file"""
    queries = []
    
    with open(input_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                queries.append(line)
    
    return queries

def show_welcome():
    """Display welcome screen with ASCII art"""
    console.clear()
    
    # ASCII art title
    ascii_banner = pyfiglet.figlet_format("Contact Finder", font="slant")
    console.print(f"[bold cyan]{ascii_banner}[/bold cyan]")
    console.print("[bold green]Business & Government Contact Discovery Tool[/bold green]")
    console.print("[dim]Powered by Perplexity AI with verification layers[/dim]\n")
    
    # Animated loading
    with console.status("[bold green]Initializing...", spinner="dots"):
        time.sleep(1.5)

def setup_api_keys_interactive():
    """Interactive API key setup wizard"""
    console.print("\n[bold yellow]🔐 API Key Setup Wizard[/bold yellow]")
    console.print("[dim]We'll help you set up your API keys. You can paste them directly when prompted.[/dim]\n")
    
    api_keys = {}
    
    # Check for existing config
    if os.path.exists('config.json'):
        if Confirm.ask("Found existing configuration. Do you want to update it?"):
            with open('config.json', 'r') as f:
                config = json.load(f)
                api_keys = config.get('api_keys', {})
    
    # Perplexity API (required)
    console.print("\n[bold]1. Perplexity API Key[/bold] [red](REQUIRED)[/red]")
    console.print("   Get your key at: [link]https://www.perplexity.ai/settings/api[/link]")
    
    perplexity_key = os.environ.get('PERPLEXITY_API_KEY', api_keys.get('perplexity', ''))
    if perplexity_key:
        console.print(f"   Current key: [dim]{perplexity_key[:10]}...{perplexity_key[-4:]}[/dim]")
        if Confirm.ask("   Keep existing key?", default=True):
            api_keys['perplexity'] = perplexity_key
        else:
            api_keys['perplexity'] = Prompt.ask("   Enter your Perplexity API key", password=True)
    else:
        api_keys['perplexity'] = Prompt.ask("   Enter your Perplexity API key", password=True)
    
    # Optional verification services
    if Confirm.ask("\n[bold]Do you want to set up email/phone verification?[/bold] (improves accuracy)", default=False):
        
        # Email verification
        console.print("\n[bold]2. Email Verification Services[/bold] [dim](optional)[/dim]")
        
        if Confirm.ask("   Set up Hunter.io?", default=False):
            console.print("   Get your key at: [link]https://hunter.io/api[/link]")
            api_keys['hunter'] = Prompt.ask("   Enter your Hunter.io API key", password=True)
        
        if Confirm.ask("   Set up ZeroBounce?", default=False):
            console.print("   Get your key at: [link]https://www.zerobounce.net[/link]")
            api_keys['zerobounce'] = Prompt.ask("   Enter your ZeroBounce API key", password=True)
        
        # Phone verification
        console.print("\n[bold]3. Phone Verification Services[/bold] [dim](optional)[/dim]")
        
        if Confirm.ask("   Set up Numverify?", default=False):
            console.print("   Get your key at: [link]https://numverify.com[/link]")
            api_keys['numverify'] = Prompt.ask("   Enter your Numverify API key", password=True)
        
        if Confirm.ask("   Set up Twilio?", default=False):
            console.print("   Get your keys at: [link]https://www.twilio.com[/link]")
            api_keys['twilio_account_sid'] = Prompt.ask("   Enter your Twilio Account SID")
            api_keys['twilio_auth_token'] = Prompt.ask("   Enter your Twilio Auth Token", password=True)
    
    # Save configuration
    config = {
        "api_keys": api_keys,
        "settings": {
            "batch_size": 10,
            "rate_limit_delay": 1.0,
            "verify_emails": bool(api_keys.get('hunter') or api_keys.get('zerobounce')),
            "verify_phones": bool(api_keys.get('numverify') or api_keys.get('twilio_account_sid'))
        }
    }
    
    with open('config.json', 'w') as f:
        json.dump(config, f, indent=2)
    
    console.print("\n[bold green]✅ Configuration saved![/bold green]")
    time.sleep(1)

def select_search_template() -> tuple[Dict, str]:
    """Interactive template selection"""
    console.print("\n[bold]📋 Select Search Template[/bold]")
    
    # Create choices for questionary
    choices = []
    for key, template in SEARCH_TEMPLATES.items():
        choices.append(
            questionary.Choice(
                title=f"{template['name']} - {template['description']}",
                value=key
            )
        )
    
    template_key = questionary.select(
        "Choose a search template:",
        choices=choices
    ).ask()
    
    return SEARCH_TEMPLATES[template_key], template_key

def build_search_query(template: Dict, template_key: str) -> List[str]:
    """Build search queries based on template"""
    console.print(f"\n[bold]🔍 Building Search Query[/bold]")
    
    if template_key == "custom_search":
        # Batch custom search
        queries = []
        console.print("Enter your search queries (one per line, empty line to finish):")
        console.print("[dim]Tip: Each query will find multiple contacts. Examples:[/dim]")
        console.print("[dim]  - California state senators contact list[/dim]")
        console.print("[dim]  - Microsoft executive team emails[/dim]")
        console.print("[dim]  - Austin city council members[/dim]\n")
        
        while True:
            query = Prompt.ask("Query", default="")
            if not query:
                break
            queries.append(query)
        return queries
    
    # Template-based search
    console.print(f"Template: [cyan]{template['name']}[/cyan]")
    console.print("[dim]This will search for multiple contacts based on roles/positions[/dim]\n")
    
    # Show examples first
    console.print("[bold]Example searches this template can generate:[/bold]")
    for example in template['examples'][:3]:
        console.print(f"  • {example}")
    console.print()
    
    console.print("Fill in the fields below (leave blank to skip):")
    
    field_values = {}
    for field in template['fields']:
        # Provide helpful prompts based on field
        if field == "state":
            value = Prompt.ask(f"  {field.title()} (e.g., California, Texas, New York)", default="")
        elif field == "city":
            value = Prompt.ask(f"  {field.title()} (e.g., Austin, Chicago, Seattle)", default="")
        elif field == "county":
            value = Prompt.ask(f"  {field.title()} (e.g., Davidson County, Cook County)", default="")
        elif field == "company":
            value = Prompt.ask(f"  {field.title()} (e.g., Microsoft, Apple, Tesla)", default="")
        elif field == "industry":
            value = Prompt.ask(f"  {field.title()} (e.g., technology, healthcare, finance)", default="")
        elif field == "service_type":
            value = Prompt.ask(f"  Service Type (e.g., roofing, plumbing, HVAC, landscaping)", default="")
        elif field == "trade":
            value = Prompt.ask(f"  Trade/Profession (e.g., electrician, carpenter, painter)", default="")
        elif field == "business_type":
            value = Prompt.ask(f"  Business Type (e.g., restaurant, retail store, coffee shop)", default="")
        elif field == "profession":
            value = Prompt.ask(f"  Profession (e.g., lawyer, accountant, consultant)", default="")
        elif field == "specialty":
            value = Prompt.ask(f"  Specialty (e.g., criminal law, tax accounting, IT consulting)", default="")
        elif field == "property_type":
            value = Prompt.ask(f"  Property Type (e.g., residential, commercial, industrial)", default="")
        elif field == "care_type":
            value = Prompt.ask(f"  Care Type (e.g., urgent care, nursing home, rehab center)", default="")
        elif field == "cuisine_type":
            value = Prompt.ask(f"  Cuisine Type (e.g., Italian, Mexican, Chinese)", default="")
        elif field == "shopping_area":
            value = Prompt.ask(f"  Shopping Area/Mall (e.g., Downtown, Main Street, Westfield Mall)", default="")
        elif field == "organization_type":
            value = Prompt.ask(f"  Organization Type (e.g., charity, foundation, association)", default="")
        elif field == "location":
            value = Prompt.ask(f"  Location (city, state, or region)", default="")
        elif field == "level":
            value = Prompt.ask(f"  Government Level (e.g., federal, state, local, city, county)", default="")
        elif field == "title":
            value = Prompt.ask(f"  Title/Position (e.g., mayor, director, commissioner)", default="")
        elif field == "office":
            value = Prompt.ask(f"  Office/Department (e.g., planning, parks, public works)", default="")
        elif field == "position":
            value = Prompt.ask(f"  Position (e.g., council member, board member, director)", default="")
        elif field == "department":
            value = Prompt.ask(f"  {field.title()} (e.g., Engineering, Marketing, Finance)", default="")
        elif field == "agency":
            value = Prompt.ask(f"  {field.title()} (e.g., EPA, FDA, Department of Defense)", default="")
        elif field == "cause":
            value = Prompt.ask(f"  {field.title()} (e.g., education, healthcare, environment)", default="")
        elif field == "region":
            value = Prompt.ask(f"  Region (e.g., Northeast, Midwest, Bay Area)", default="")
        else:
            value = Prompt.ask(f"  {field.title()}", default="")
        
        if value:
            field_values[field] = value
    
    # Clean up field values to avoid duplication
    if 'city' in field_values and 'state' in field_values:
        # Remove state from city if it's already included
        city_parts = field_values['city'].split(',')
        if len(city_parts) > 1:
            field_values['city'] = city_parts[0].strip()
    
    # Handle multiple service types/trades/etc separated by commas
    multi_value_fields = ['service_type', 'trade', 'business_type', 'profession']
    expanded_queries = []
    
    for field in multi_value_fields:
        if field in field_values and ',' in field_values[field]:
            # Split the field into multiple values
            values = [v.strip() for v in field_values[field].split(',')]
            # Generate queries for each value separately
            for value in values:
                temp_values = field_values.copy()
                temp_values[field] = value
                
                # Generate queries for this specific value
                for example in template['examples']:
                    try:
                        query = example.format(**temp_values)
                        if '{' not in query:
                            expanded_queries.append(query)
                    except KeyError:
                        pass
    
    # If we generated expanded queries, use those instead
    if expanded_queries:
        return expanded_queries
    
    # Generate queries from examples
    queries = []
    for example in template['examples']:
        try:
            # Only use examples where we have all required fields
            query = example.format(**field_values)
            # Skip if the query still has unfilled placeholders
            if '{' not in query:
                queries.append(query)
        except KeyError:
            # Skip if not all fields are filled
            pass
    
    # If no queries generated, create some based on filled fields
    if not queries and field_values:
        if template_key == "local_businesses" and "service_type" in field_values:
            service = field_values.get('service_type')
            location = field_values.get('city', field_values.get('state', 'area'))
            queries.append(f"{service} companies {location} owner contact information")
        elif template_key == "smb_by_industry" and "industry" in field_values:
            industry = field_values.get('industry')
            location = field_values.get('city', field_values.get('state', 'area'))
            queries.append(f"{industry} small business owners {location} contact list")
        elif template_key == "contractors_trades" and "trade" in field_values:
            trade = field_values.get('trade')
            location = field_values.get('city', field_values.get('state', 'area'))
            queries.append(f"{trade} contractors {location} business contacts")
        elif template_key == "retail_restaurants" and "business_type" in field_values:
            business = field_values.get('business_type')
            location = field_values.get('city', field_values.get('state', 'area'))
            queries.append(f"{business} owners {location} contact list")
        elif template_key == "professional_services" and "profession" in field_values:
            profession = field_values.get('profession')
            location = field_values.get('city', field_values.get('state', 'area'))
            queries.append(f"{profession} firms {location} contact information")
        elif template_key == "real_estate" and ("city" in field_values or "state" in field_values):
            location = field_values.get('city', field_values.get('state', 'area'))
            queries.append(f"real estate professionals {location} contact list")
        elif template_key == "healthcare_providers" and ("specialty" in field_values or "care_type" in field_values):
            type_val = field_values.get('specialty', field_values.get('care_type', 'medical'))
            location = field_values.get('city', field_values.get('state', 'area'))
            queries.append(f"{type_val} providers {location} contact information")
        elif template_key == "business_associations" and "city" in field_values:
            city = field_values.get('city')
            queries.append(f"{city} chamber of commerce member contact list")
        elif template_key == "government" and "location" in field_values:
            location = field_values.get('location')
            level = field_values.get('level', '')
            queries.append(f"{level} government officials {location} contact information")
        elif template_key == "nonprofit" and ("cause" in field_values or "location" in field_values):
            cause = field_values.get('cause', 'nonprofit')
            location = field_values.get('location', field_values.get('city', field_values.get('state', '')))
            queries.append(f"{cause} organizations {location} director contacts")
    
    # Show generated queries
    if queries:
        console.print("\n[bold]Generated searches:[/bold]")
        console.print("[dim]Each search will look for multiple contacts[/dim]")
        for i, query in enumerate(queries, 1):
            console.print(f"  {i}. {query}")
        
        # Allow selecting which queries to use
        if len(queries) > 1:
            if Confirm.ask("\nUse all these searches?", default=True):
                pass
            else:
                # Let user select which queries to keep
                selected_queries = []
                for query in queries:
                    if Confirm.ask(f"Include: {query}?", default=True):
                        selected_queries.append(query)
                queries = selected_queries
        
        # Allow editing
        if Confirm.ask("\nWould you like to edit any searches?", default=False):
            edited_queries = []
            for query in queries:
                edited = Prompt.ask("Edit search", default=query)
                if edited:
                    edited_queries.append(edited)
            queries = edited_queries
    
    # Add custom queries
    if Confirm.ask("\nAdd additional searches?", default=False):
        console.print("[dim]Remember: Each search should find multiple contacts[/dim]")
        while True:
            query = Prompt.ask("Additional search", default="")
            if not query:
                break
            queries.append(query)
    
    return queries

def run_search_with_animation(finder: ContactFinder, queries: List[str]):
    """Run the search with progress animations"""
    console.print(f"\n[bold green]🚀 Starting search for {len(queries)} contacts[/bold green]")
    
    results = []
    
    # Progress bar
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
    ) as progress:
        
        task = progress.add_task("[cyan]Searching contacts...", total=len(queries))
        
        for i, query in enumerate(queries):
            progress.update(task, description=f"[cyan]Searching: {query[:50]}...")
            
            try:
                # Search for contacts (returns multiple)
                contacts = finder.perplexity.search_contact(query)
                
                if contacts:
                    console.print(f"[green]✓[/green] Found {len(contacts)} contacts for: {query}")
                    for contact in contacts:
                        # Verify if enabled
                        if finder.config.get_setting('verify_emails'):
                            finder.email_verifier.verify_all_emails(contact)
                        if finder.config.get_setting('verify_phones'):
                            finder.phone_verifier.verify_all_phones(contact)
                        
                        results.append(contact)
                        console.print(f"   • {contact.name} at {contact.company}")
                else:
                    console.print(f"[red]✗[/red] Not found: {query}")
            except Exception as e:
                console.print(f"[red]✗[/red] Error with {query}: {str(e)}")
            
            progress.update(task, advance=1)
            
            # Rate limiting
            if i < len(queries) - 1:
                time.sleep(finder.config.get_setting('rate_limit_delay'))
    
    return results

def display_results_summary(results: List, csv_file: str = None, json_file: str = None, txt_file: str = None, excel_file: str = None):
    """Display a summary of the results with sources in table format"""
    console.print("\n[bold green]✅ Search Complete![/bold green]")
    
    if not results:
        console.print("[red]No contacts found.[/red]")
        return
    
    console.print(f"\n[bold]Found {len(results)} contacts:[/bold]\n")
    
    # Create main results table
    table = Table(title="Contact Search Results", show_lines=True)
    table.add_column("#", style="dim", width=3)
    table.add_column("Name", style="bold cyan", width=20)
    table.add_column("Company/Org", style="blue", width=20)
    table.add_column("Email", style="green", width=30)
    table.add_column("Phone", style="yellow", width=15)
    table.add_column("Sources", style="magenta", width=40)
    table.add_column("Confidence", justify="center", width=10)
    
    # Add rows for all contacts (or first 20 if too many)
    display_limit = min(len(results), 20)
    for i, result in enumerate(results[:display_limit], 1):
        # Format sources
        sources_text = ""
        if result.sources:
            # Show first source title and indicate if there are more
            first_source = result.sources[0].get('title', 'Source')
            if len(result.sources) > 1:
                sources_text = f"{first_source}\n[dim](+{len(result.sources)-1} more sources)[/dim]"
            else:
                sources_text = first_source
        else:
            sources_text = "[dim]No sources[/dim]"
        
        # Format confidence with color
        confidence = f"{result.confidence_score:.0%}"
        if result.confidence_score >= 0.8:
            confidence = f"[green]{confidence}[/green]"
        elif result.confidence_score >= 0.6:
            confidence = f"[yellow]{confidence}[/yellow]"
        else:
            confidence = f"[red]{confidence}[/red]"
        
        table.add_row(
            str(i),
            result.name or "N/A",
            result.company or "-",
            result.primary_email or "[dim]No email[/dim]",
            result.primary_phone or "[dim]No phone[/dim]",
            sources_text,
            confidence
        )
    
    console.print(table)
    
    if len(results) > display_limit:
        console.print(f"\n[dim]Showing first {display_limit} of {len(results)} contacts. See exported files for complete list.[/dim]")
    
    # Create sources detail table for first few contacts
    console.print("\n[bold]Detailed Sources (First 5 Contacts):[/bold]")
    sources_table = Table(show_lines=True)
    sources_table.add_column("Contact", style="cyan", width=25)
    sources_table.add_column("Source Title", style="white", width=30)
    sources_table.add_column("Source URL", style="dim blue", width=50)
    
    for result in results[:5]:
        if result.sources:
            for j, source in enumerate(result.sources):
                # Only show contact name in first row for that contact
                contact_name = result.name if j == 0 else ""
                sources_table.add_row(
                    contact_name,
                    source.get('title', 'Unknown Source'),
                    source.get('url', 'No URL available')
                )
        else:
            sources_table.add_row(
                result.name,
                "[dim]No sources available[/dim]",
                "-"
            )
    
    console.print(sources_table)
    
    # Summary statistics in a compact table
    console.print("\n[bold]Summary Statistics:[/bold]")
    stats_table = Table(show_header=False, box=None)
    stats_table.add_column("Metric", style="dim")
    stats_table.add_column("Value", style="bold")
    
    stats_table.add_row("Total contacts found:", f"[green]{len(results)}[/green]")
    stats_table.add_row("With email address:", f"[green]{sum(1 for r in results if r.primary_email)}[/green]")
    stats_table.add_row("With phone number:", f"[green]{sum(1 for r in results if r.primary_phone)}[/green]")
    stats_table.add_row("Average confidence:", f"[yellow]{sum(r.confidence_score for r in results) / len(results):.0%}[/yellow]")
    
    console.print(stats_table)
    
    # Output files
    if csv_file or json_file or txt_file or excel_file:
        console.print(f"\n[bold]📁 Exported Files:[/bold]")
        files_table = Table(show_header=False, box=None)
        files_table.add_column("Format", style="dim")
        files_table.add_column("Path", style="cyan")
        
        if csv_file:
            files_table.add_row("CSV:", csv_file)
        if excel_file:
            files_table.add_row("Excel:", excel_file)
        if txt_file:
            files_table.add_row("Text:", txt_file)
        if json_file:
            files_table.add_row("JSON:", json_file)
        
        console.print(files_table)
        console.print(f"\n[yellow]⚠️  Always verify contact information using the provided sources before use![/yellow]")

def run_enrichment_mode(finder: ContactFinder):
    """Run contact enrichment mode"""
    console.print("\n[bold cyan]📈 Contact Enrichment Mode[/bold cyan]")
    console.print("[dim]Upload a list of contacts to find missing emails and phone numbers[/dim]\n")
    
    # Get file path
    file_path = Prompt.ask("Enter path to contact file (CSV, Excel, or JSON)")
    
    if not Path(file_path).exists():
        console.print(f"[red]File not found: {file_path}[/red]")
        return
    
    try:
        # Parse contacts
        console.print(f"\n[cyan]Parsing contacts from {file_path}...[/cyan]")
        contacts = ContactParser.parse_file(file_path)
        
        if not contacts:
            console.print("[yellow]No contacts found in file[/yellow]")
            return
        
        console.print(f"[green]✓ Found {len(contacts)} contacts[/green]")
        
        # Show preview
        table = Table(title="Contact Preview (First 5)")
        table.add_column("Name", style="cyan")
        table.add_column("Company", style="magenta")
        table.add_column("Has Email", style="green")
        table.add_column("Has Phone", style="yellow")
        
        for contact in contacts[:5]:
            table.add_row(
                contact.name or "-",
                contact.company or "-",
                "✓" if contact.email else "✗",
                "✓" if contact.phone else "✗"
            )
        
        console.print(table)
        
        # Count missing info
        missing_email = sum(1 for c in contacts if not c.email)
        missing_phone = sum(1 for c in contacts if not c.phone)
        missing_both = sum(1 for c in contacts if not c.email and not c.phone)
        
        console.print(f"\n[bold]Enrichment Opportunities:[/bold]")
        console.print(f"  • Missing emails: {missing_email}")
        console.print(f"  • Missing phones: {missing_phone}")
        console.print(f"  • Missing both: {missing_both}")
        
        if missing_email == 0 and missing_phone == 0:
            console.print("\n[green]All contacts already have email and phone![/green]")
            return
        
        # Ask to proceed
        if not Confirm.ask(f"\nEnrich {missing_email + missing_phone} missing fields?"):
            return
        
        # Check for resume
        resume = False
        if Path("enrichment_state.json").exists():
            resume = Confirm.ask("Found previous enrichment session. Resume?")
        
        # Initialize enricher
        enricher = ContactEnricher(
            perplexity_client=finder.perplexity,
            rate_limit_delay=finder.config.rate_limit_delay
        )
        
        # Run enrichment
        console.print("\n[bold green]Starting enrichment...[/bold green]")
        results = enricher.enrich_contacts(contacts, resume=resume)
        
        # Export results
        if results:
            console.print("\n[bold]Export Options:[/bold]")
            format_choice = questionary.select(
                "Choose export format:",
                choices=["CSV", "Excel", "JSON", "All formats"]
            ).ask()
            
            exporter = EnrichmentExporter()
            
            if format_choice == "All formats":
                csv_file = exporter.export_results(results, "csv")
                excel_file = exporter.export_results(results, "excel")
                json_file = exporter.export_results(results, "json")
                
                console.print("\n[bold green]✓ Exported enriched contacts:[/bold green]")
                console.print(f"  • CSV: {csv_file}")
                console.print(f"  • Excel: {excel_file}")
                console.print(f"  • JSON: {json_file}")
            else:
                export_format = format_choice.lower()
                export_file = exporter.export_results(results, export_format)
                console.print(f"\n[bold green]✓ Exported to: {export_file}[/bold green]")
            
            # Clean up state file
            if Path("enrichment_state.json").exists() and Confirm.ask("\nDelete enrichment state file?"):
                Path("enrichment_state.json").unlink()
    
    except Exception as e:
        console.print(f"[red]Error during enrichment: {str(e)}[/red]")
        logger.error(f"Enrichment error: {str(e)}", exc_info=True)

def show_interactive_help():
    """Show interactive help for common issues"""
    console.clear()
    console.print("[bold cyan]🆘 Contact Finder Help Center[/bold cyan]\n")
    
    help_topics = {
        "Getting Started": {
            "No API key": "You need a Perplexity API key. Get one at https://www.perplexity.ai/settings/api\nThen either:\n1. Run with --interactive for setup wizard\n2. Set environment variable: export PERPLEXITY_API_KEY='your-key'\n3. Create config.json with your key",
            "First time setup": "Run: python3 perplexity_contact_finder.py --interactive\nThis will guide you through setup",
            "Virtual environment": "Create a virtual environment:\n1. python3 -m venv venv\n2. source venv/bin/activate (Mac/Linux) or venv\\Scripts\\activate (Windows)\n3. pip install -r requirements.txt"
        },
        "Search Tips": {
            "Government contacts": "Use templates! Run with --interactive and select 'Federal/State/Local Government Officials'",
            "Better results": "Be specific: Include full name, title, and organization\nExample: 'John Smith CEO Microsoft' not just 'John Smith'",
            "No results found": "Try variations:\n- Different name formats (John vs Jonathan)\n- Include middle names or initials\n- Add location (city/state)\n- Check spelling"
        },
        "Common Errors": {
            "Module not found": "Install dependencies: pip install -r requirements.txt",
            "API key invalid": "Check your API key is correct and has credits remaining",
            "Rate limit": "The tool automatically handles rate limits. If you hit limits, wait a few minutes",
            "No config file": "Run: python3 perplexity_contact_finder.py --setup"
        },
        "Advanced Usage": {
            "Batch searches": "Create a file with one search per line, then:\npython3 perplexity_contact_finder.py -f queries.txt",
            "Resume interrupted": "If search was interrupted:\npython3 perplexity_contact_finder.py -f queries.txt --resume",
            "Skip verification": "For faster results without verification:\npython3 perplexity_contact_finder.py 'query' --perplexity-only",
            "Output formats": "Choose output: --output csv, --output json, or --output both (default)"
        }
    }
    
    while True:
        # Show topics
        console.print("[bold]Select a help topic:[/bold]")
        topic_choices = list(help_topics.keys()) + ["Exit Help"]
        
        topic = questionary.select(
            "What do you need help with?",
            choices=topic_choices
        ).ask()
        
        if topic == "Exit Help":
            break
        
        # Show subtopics
        console.print(f"\n[bold cyan]{topic}[/bold cyan]")
        subtopics = help_topics[topic]
        
        subtopic = questionary.select(
            "Select specific issue:",
            choices=list(subtopics.keys()) + ["Back"]
        ).ask()
        
        if subtopic != "Back":
            console.print(f"\n[bold]{subtopic}:[/bold]")
            console.print(Panel(subtopics[subtopic], expand=False))
            Prompt.ask("\nPress Enter to continue")
        
        console.clear()
        console.print("[bold cyan]🆘 Contact Finder Help Center[/bold cyan]\n")

def run_interactive_mode():
    """Run the tool in interactive mode"""
    show_welcome()
    
    # Check for API keys
    if not os.path.exists('config.json') and not os.environ.get('PERPLEXITY_API_KEY'):
        console.print("[yellow]⚠️  No configuration found. Let's set up your API keys.[/yellow]")
        setup_api_keys_interactive()
    elif not os.path.exists('config.json'):
        # Create config from environment variable
        if Confirm.ask("Would you like to save your API key configuration?"):
            setup_api_keys_interactive()
    
    # Initialize finder
    try:
        finder = ContactFinder('config.json')
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        if Confirm.ask("Would you like to set up API keys now?"):
            setup_api_keys_interactive()
            finder = ContactFinder('config.json')
        else:
            return
    
    while True:
        # Main menu
        console.print("\n[bold]Main Menu[/bold]")
        action = questionary.select(
            "What would you like to do?",
            choices=[
                "🔍 Search for contacts",
                "📋 Use search templates",
                "📈 Enrich existing contacts",
                "🔐 Update API keys",
                "📚 View examples",
                "🆘 Get help",
                "❌ Exit"
            ]
        ).ask()
        
        if "Search for contacts" in action or "Use search templates" in action:
            # Ask if user wants enhanced search
            use_enhanced = False
            if "Search for contacts" in action:
                console.print("\n[bold]🔍 Search Mode Selection[/bold]")
                search_mode = questionary.select(
                    "Choose search mode:",
                    choices=[
                        questionary.Choice("🚀 Enhanced Search (Finds MANY more contacts)", value="enhanced"),
                        questionary.Choice("⚡ Standard Search (Faster, fewer results)", value="standard")
                    ]
                ).ask()
                use_enhanced = (search_mode == "enhanced")
            
            template, template_key = select_search_template()
            queries = build_search_query(template, template_key)
            
            if queries:
                if use_enhanced and len(queries) > 0:
                    console.print("\n[bold green]🚀 Enhanced Search Mode Activated![/bold green]")
                    console.print("[dim]This will perform multiple rounds of searching to find comprehensive results.[/dim]")
                    console.print("[dim]This may take several minutes but will find many more contacts.[/dim]\n")
                    
                    # Use enhanced search strategy
                    enhanced_searcher = EnhancedSearchStrategy(finder.perplexity)
                    results = enhanced_searcher.iterative_deep_search(queries[0])
                else:
                    # Standard search
                    results = run_search_with_animation(finder, queries)
                
                if results:
                    # Use output selector for user-friendly export
                    exporter = DataExporter()
                    output_selector = OutputSelector()
                    
                    # Let user choose formats and export
                    exported_files = output_selector.export_with_options(results, exporter)
                    
                    # Show file access guide
                    output_selector.show_file_access_guide(exported_files)
            else:
                console.print("[yellow]No queries entered.[/yellow]")
        
        elif "Enrich existing contacts" in action:
            run_enrichment_mode(finder)
        
        elif "Update API keys" in action:
            setup_api_keys_interactive()
            # Reinitialize finder with new config
            try:
                finder = ContactFinder('config.json')
            except Exception as e:
                console.print(f"[red]Error reinitializing: {e}[/red]")
        
        elif "View examples" in action:
            show_examples()
        
        elif "Get help" in action:
            show_interactive_help()
        
        elif "Exit" in action:
            console.print("\n[bold green]Thanks for using Contact Finder! 👋[/bold green]")
            break

def show_examples():
    """Display search examples"""
    console.print("\n[bold]📚 Search Examples[/bold]\n")
    console.print("[dim]These searches find multiple contacts automatically:[/dim]\n")
    
    examples = {
        "Government - Find Multiple Officials": [
            "all California state senators contact list",
            "Texas state government cabinet members",
            "New York City council members contact information",
            "EPA regional directors contact list",
            "House judiciary committee members emails"
        ],
        "Business - Find Teams & Leaders": [
            "Apple executive team contact information",
            "Microsoft C-suite executives emails",
            "Fortune 500 technology CEOs contact list",
            "Tesla board of directors contacts",
            "Amazon regional managers contact information"
        ],
        "Local Government - City/County": [
            "Austin city council members",
            "Chicago mayor and deputy mayors contacts",
            "Los Angeles county commissioners",
            "Seattle planning commission members",
            "Miami city department heads contact list"
        ],
        "Industry Leaders": [
            "healthcare industry CEOs contact list",
            "renewable energy companies executives",
            "top 20 banks chief technology officers",
            "biotech startup founders Bay Area",
            "automotive industry board members"
        ],
        "Nonprofit & Education": [
            "education nonprofit executive directors California",
            "environmental foundation board members",
            "Texas university presidents contact list",
            "healthcare advocacy organizations leadership",
            "Chicago area community foundation directors"
        ]
    }
    
    for category, example_list in examples.items():
        console.print(f"[bold cyan]{category}:[/bold cyan]")
        for example in example_list:
            console.print(f"  • {example}")
        console.print()
    
    Prompt.ask("\nPress Enter to continue")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Find and verify contact information using Perplexity AI')
    
    parser.add_argument('queries', nargs='*', help='Contact queries (names, companies, etc.)')
    parser.add_argument('-f', '--file', help='File containing queries (one per line)')
    parser.add_argument('-c', '--config', default='config.json', help='Configuration file')
    parser.add_argument('-o', '--output', choices=['csv', 'json', 'both'], default='both', 
                       help='Output format (default: both)')
    parser.add_argument('--resume', action='store_true', help='Resume from previous run')
    parser.add_argument('--clear', action='store_true', help='Clear saved state and start fresh')
    parser.add_argument('--setup', action='store_true', help='Create sample configuration file')
    parser.add_argument('--no-verify', action='store_true', help='Skip email/phone verification')
    parser.add_argument('--perplexity-only', action='store_true', help='Use only Perplexity API (no verification services)')
    parser.add_argument('--interactive', '-i', action='store_true', help='Run in interactive mode with templates and wizard')
    parser.add_argument('--help-me', action='store_true', help='Get interactive help for common issues')
    parser.add_argument('--enrich', help='Enrich contacts from a CSV/Excel/JSON file')
    parser.add_argument('--enrich-format', choices=['csv', 'excel', 'json', 'all'], default='csv',
                       help='Export format for enriched contacts (default: csv)')
    
    args = parser.parse_args()
    
    # Help mode
    if args.help_me:
        show_interactive_help()
        return
    
    # Interactive mode
    if args.interactive or (not args.queries and not args.file and not args.setup and not args.clear and not args.enrich):
        run_interactive_mode()
        return
    
    # Enrichment mode
    if args.enrich:
        try:
            finder = ContactFinder(args.config)
            
            # Parse contacts from file
            console.print(f"[cyan]Loading contacts from {args.enrich}...[/cyan]")
            contacts = ContactParser.parse_file(args.enrich)
            
            if not contacts:
                console.print("[red]No contacts found in file[/red]")
                return
            
            console.print(f"[green]Found {len(contacts)} contacts[/green]")
            
            # Check for resume
            resume = args.resume or (Path("enrichment_state.json").exists() and 
                                    Confirm.ask("Found previous enrichment. Resume?"))
            
            # Initialize enricher
            enricher = ContactEnricher(
                perplexity_client=finder.perplexity,
                rate_limit_delay=finder.config.rate_limit_delay
            )
            
            # Run enrichment
            results = enricher.enrich_contacts(contacts, resume=resume)
            
            # Export results
            if results:
                exporter = EnrichmentExporter()
                
                if args.enrich_format == "all":
                    csv_file = exporter.export_results(results, "csv")
                    excel_file = exporter.export_results(results, "excel")
                    json_file = exporter.export_results(results, "json")
                    console.print("\n[bold green]✓ Exported enriched contacts:[/bold green]")
                    console.print(f"  • CSV: {csv_file}")
                    console.print(f"  • Excel: {excel_file}")
                    console.print(f"  • JSON: {json_file}")
                else:
                    export_file = exporter.export_results(results, args.enrich_format)
                    console.print(f"\n[bold green]✓ Exported to: {export_file}[/bold green]")
        
        except Exception as e:
            console.print(f"[red]Error: {str(e)}[/red]")
            logger.error(f"Enrichment error: {str(e)}", exc_info=True)
        return
    
    # Setup mode
    if args.setup:
        config = Config()
        config.create_sample_config()
        print("\nSample configuration created. Copy config.sample.json to config.json and add your API keys.")
        return
    
    # Initialize finder
    try:
        finder = ContactFinder(args.config)
    except ValueError as e:
        print(f"Error: {e}")
        print("\nRun with --setup to create a sample configuration file.")
        return 1
    
    # Clear state if requested
    if args.clear:
        finder.clear_state()
        if not args.queries and not args.file:
            return
    
    # Disable verification if requested
    if args.no_verify or args.perplexity_only:
        finder.config.set_setting('verify_emails', False)
        finder.config.set_setting('verify_phones', False)
        
    # Show Perplexity-only mode message
    if args.perplexity_only:
        print("Running in Perplexity-only mode (no verification services)")
    
    # Get queries
    queries = []
    
    if args.file:
        queries.extend(load_queries(args.file))
    
    if args.queries:
        queries.extend(args.queries)
    
    if not queries:
        print("Error: No queries provided. Use positional arguments or -f/--file option.")
        parser.print_help()
        return 1
    
    # Display configuration
    print("\n" + "="*60)
    print("PERPLEXITY CONTACT FINDER")
    print("="*60)
    finder.config.display_config()
    print(f"\nQueries to process: {len(queries)}")
    print("="*60 + "\n")
    
    # Find contacts
    try:
        contacts = finder.find_contacts(queries, resume=args.resume)
        
        if contacts:
            # Export results
            exported_files = finder.export_results(args.output)
            
            print("\nExported files:")
            for file in exported_files:
                print(f"  - {file}")
        else:
            print("\nNo contacts found.")
            
    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Progress has been saved.")
        print("Run with --resume to continue from where you left off.")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())