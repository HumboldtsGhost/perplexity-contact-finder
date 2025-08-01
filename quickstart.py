#!/usr/bin/env python3
"""
Quick start example - Perplexity only (no verification services needed)
"""
import os
from perplexity_client import PerplexityClient
from data_exporter import DataExporter

def main():
    # Get API key from environment or use a test key
    api_key = os.getenv('PERPLEXITY_API_KEY')
    
    if not api_key:
        print("Please set your Perplexity API key:")
        print("export PERPLEXITY_API_KEY='your-key-here'")
        print("\nGet your key at: https://www.perplexity.ai/settings/api")
        return
    
    # Initialize Perplexity client
    client = PerplexityClient(api_key=api_key)
    
    # Search for contacts
    queries = [
        "Tim Cook CEO Apple",
        "Satya Nadella CEO Microsoft",
        "Sundar Pichai CEO Google"
    ]
    
    print("Searching for contacts using Perplexity AI...\n")
    
    contacts = []
    for query in queries:
        print(f"Searching: {query}")
        contact = client.search_contact(query)
        
        if contact:
            contacts.append(contact)
            print(f"✓ Found: {contact.name}")
            if contact.primary_email:
                print(f"  Email: {contact.primary_email}")
            if contact.alternate_emails:
                print(f"  Alt emails: {', '.join(contact.alternate_emails)}")
            if contact.sources:
                print(f"  Sources: {len(contact.sources)} found")
            print()
    
    # Export results
    if contacts:
        exporter = DataExporter()
        csv_file = exporter.export_to_csv(contacts, "quickstart_results.csv")
        print(f"\nResults saved to: {csv_file}")
        exporter.print_summary(contacts)

if __name__ == "__main__":
    main()