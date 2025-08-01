#!/usr/bin/env python3
"""
Example usage of the Perplexity Contact Finder
"""

from config import Config
from perplexity_client import PerplexityClient
from email_verifier import EmailVerificationService
from phone_verifier import PhoneVerificationService
from data_exporter import DataExporter

def main():
    # Initialize configuration
    config = Config()
    
    # Check if Perplexity API key is set
    if not config.get_api_key('perplexity'):
        print("Error: Perplexity API key not found!")
        print("Please set your API key in config.json or as PERPLEXITY_API_KEY environment variable")
        return
    
    # Initialize services
    perplexity = PerplexityClient(
        api_key=config.get_api_key('perplexity'),
        rate_limit_delay=1.0
    )
    
    email_verifier = EmailVerificationService(config)
    phone_verifier = PhoneVerificationService(config)
    exporter = DataExporter()
    
    # Example: Search for a single contact
    print("Searching for Tim Cook at Apple...")
    contact = perplexity.search_contact("Tim Cook CEO Apple Cupertino")
    
    if contact:
        print(f"\nFound: {contact.name}")
        print(f"Company: {contact.company}")
        print(f"Primary Email: {contact.primary_email}")
        print(f"Alternate Emails: {', '.join(contact.alternate_emails)}")
        print(f"Primary Phone: {contact.primary_phone}")
        print(f"Alternate Phones: {', '.join(contact.alternate_phones)}")
        print(f"Confidence: {contact.confidence_score:.2f}")
        
        # Verify email if verification services are configured
        if config.get_setting('verify_emails'):
            print("\nVerifying emails...")
            email_verifier.verify_all_emails(contact)
            print(f"Email Status: {contact.verification_status.get('primary_email', 'unverified')}")
        
        # Verify phone if verification services are configured
        if config.get_setting('verify_phones'):
            print("\nVerifying phones...")
            phone_verifier.verify_all_phones(contact)
            print(f"Phone Status: {contact.verification_status.get('primary_phone', 'unverified')}")
        
        # Export results
        print("\nExporting results...")
        csv_file = exporter.export_to_csv([contact], "example_output.csv")
        print(f"Results exported to: {csv_file}")
    else:
        print("No contact information found.")

if __name__ == "__main__":
    main()