"""
Perplexity API client for contact finding
"""
import time
import json
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import re

from openai import OpenAI

@dataclass
class ContactInfo:
    """Represents a contact with all found information"""
    name: str
    company: str = ""
    primary_email: str = ""
    alternate_emails: List[str] = field(default_factory=list)
    primary_phone: str = ""
    alternate_phones: List[str] = field(default_factory=list)
    sources: List[Dict[str, str]] = field(default_factory=list)
    raw_response: str = ""
    confidence_score: float = 0.0
    verification_status: Dict[str, str] = field(default_factory=dict)
    notes: str = ""
    date_found: str = field(default_factory=lambda: datetime.now().isoformat())

class PerplexityClient:
    """Client for interacting with Perplexity API"""
    
    def __init__(self, api_key: str, model: str = "sonar-pro", 
                 rate_limit_delay: float = 1.0, max_retries: int = 3):
        """Initialize Perplexity client"""
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.perplexity.ai"
        )
        self.model = model
        self.rate_limit_delay = rate_limit_delay
        self.max_retries = max_retries
    
    def search_contact(self, query: str, additional_context: str = "") -> List[ContactInfo]:
        """Search for contact information using Perplexity - returns multiple contacts"""
        
        # Construct the prompt for finding contact information
        system_prompt = """You are an expert business contact researcher specializing in finding specific business owner and decision-maker contact information.

When given a query about finding contacts:
1. Search for SPECIFIC BUSINESS NAMES with their owners/decision-makers
2. Focus on finding real companies with actual contact details (not generic industry info)
3. Prioritize owner names, CEO names, or key decision-makers
4. Include company websites, email addresses, and phone numbers
5. For contractors/services: find actual business names like "Smith Roofing LLC" or "Johnson Plumbing Services"
6. Always cite your sources with full URLs

IMPORTANT: Return multiple distinct businesses when searching for a category (e.g., if searching for "roofers in Greenville", return 5-10 different roofing companies with their specific contact info).

Format your response as a JSON array of contacts:
[
    {
        "name": "John Smith (Owner)",
        "company": "Smith Roofing LLC",
        "emails": ["john@smithroofing.com", "info@smithroofing.com"],
        "phones": ["+1-864-555-1234", "+1-864-555-5678"],
        "sources": [
            {"url": "https://smithroofing.com/contact", "title": "Smith Roofing Contact Page", "relevance": "Official company contact page"},
            {"url": "https://bbb.org/profile/smith-roofing", "title": "BBB Profile", "relevance": "Verified business listing"}
        ],
        "confidence": 0.95,
        "notes": "Family-owned business since 1995, specializes in residential roofing"
    },
    {
        "name": "Maria Garcia (President)",
        "company": "Garcia Plumbing & HVAC Inc",
        "emails": ["maria@garciaplumbing.com"],
        "phones": ["+1-864-555-9876"],
        "sources": [{"url": "https://garciaplumbing.com", "title": "Company Website", "relevance": "Main website"}],
        "confidence": 0.9,
        "notes": "Commercial and residential services"
    }
]"""

        user_prompt = f"""Find specific business contacts for: {query}
{additional_context}

IMPORTANT REQUIREMENTS:
1. Find ACTUAL BUSINESS NAMES (not generic descriptions)
2. Include the OWNER or KEY DECISION-MAKER name whenever possible
3. Search for AT LEAST 5-10 different businesses that match the criteria
4. For each business include:
   - Owner/manager/decision-maker name with their title
   - Specific company name
   - Direct email addresses (not just generic info@)
   - Phone numbers
   - Company website
   - Where you found this information

For service businesses (contractors, restaurants, etc.), focus on:
- Local business directories
- BBB listings
- Chamber of Commerce members
- Google Business profiles
- Industry association members
- Company websites with "About Us" or "Our Team" pages

Respond with a JSON array containing multiple businesses as specified above."""

        retries = 0
        while retries < self.max_retries:
            try:
                # Rate limiting
                time.sleep(self.rate_limit_delay)
                
                # Make API call
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.1,  # Lower temperature for more consistent results
                )
                
                # Extract response
                raw_response = response.choices[0].message.content
                
                # Parse JSON response to get multiple contacts
                contacts = self._parse_response_multiple(raw_response, query)
                
                return contacts
                
            except Exception as e:
                retries += 1
                if retries >= self.max_retries:
                    print(f"Error searching for {query}: {str(e)}")
                    return []
                time.sleep(2 ** retries)  # Exponential backoff
        
        return []
    
    def _parse_response_multiple(self, response: str, original_query: str) -> List[ContactInfo]:
        """Parse the JSON response from Perplexity to extract multiple contacts"""
        contacts = []
        try:
            # Extract JSON array from response
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                contacts_data = json.loads(json_match.group())
            else:
                # Try single object format for backward compatibility
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    contacts_data = [json.loads(json_match.group())]
                else:
                    contacts_data = json.loads(response)
            
            # If we got a single dict instead of array, wrap it
            if isinstance(contacts_data, dict):
                contacts_data = [contacts_data]
            
            # Process each contact
            for data in contacts_data:
                # Skip if no actual company name
                if not data.get('company') or data.get('company').lower() in ['company', 'business', 'organization']:
                    continue
                    
                # Extract emails
                emails = data.get('emails', [])
                primary_email = emails[0] if emails else ""
                alternate_emails = emails[1:] if len(emails) > 1 else []
                
                # Extract phones
                phones = data.get('phones', [])
                primary_phone = phones[0] if phones else ""
                alternate_phones = phones[1:] if len(phones) > 1 else []
                
                # Create ContactInfo object
                contact = ContactInfo(
                    name=data.get('name', ''),
                    company=data.get('company', ''),
                    primary_email=primary_email,
                    alternate_emails=alternate_emails,
                    primary_phone=primary_phone,
                    alternate_phones=alternate_phones,
                    sources=data.get('sources', []),
                    confidence_score=data.get('confidence', 0.5),
                    notes=data.get('notes', ''),
                    raw_response=response
                )
                contacts.append(contact)
            
            # If no valid contacts found, try text parsing
            if not contacts:
                contact = self._parse_text_response(response, original_query)
                if contact:
                    contacts.append(contact)
                    
            return contacts
            
        except (json.JSONDecodeError, TypeError) as e:
            # Fallback: try to extract information from raw text
            contact = self._parse_text_response(response, original_query)
            return [contact] if contact else []
    
    def _parse_response(self, response: str, original_query: str) -> ContactInfo:
        """Parse the JSON response from Perplexity"""
        try:
            # Extract JSON array from response
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                contacts_data = json.loads(json_match.group())
            else:
                # Try single object format for backward compatibility
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    contacts_data = [json.loads(json_match.group())]
                else:
                    contacts_data = json.loads(response)
            
            # If we got a single dict instead of array, wrap it
            if isinstance(contacts_data, dict):
                contacts_data = [contacts_data]
            
            # Return the first contact with the highest confidence
            best_contact = None
            best_confidence = 0
            
            for data in contacts_data:
                # Skip if no actual company name
                if not data.get('company') or data.get('company') == original_query:
                    continue
                    
                confidence = data.get('confidence', 0.5)
                if confidence > best_confidence:
                    # Extract emails
                    emails = data.get('emails', [])
                    primary_email = emails[0] if emails else ""
                    alternate_emails = emails[1:] if len(emails) > 1 else []
                    
                    # Extract phones
                    phones = data.get('phones', [])
                    primary_phone = phones[0] if phones else ""
                    alternate_phones = phones[1:] if len(phones) > 1 else []
                    
                    # Create ContactInfo object
                    best_contact = ContactInfo(
                        name=data.get('name', ''),
                        company=data.get('company', ''),
                        primary_email=primary_email,
                        alternate_emails=alternate_emails,
                        primary_phone=primary_phone,
                        alternate_phones=alternate_phones,
                        sources=data.get('sources', []),
                        confidence_score=confidence,
                        notes=data.get('notes', '')
                    )
                    best_confidence = confidence
            
            return best_contact if best_contact else self._parse_text_response(response, original_query)
            
        except (json.JSONDecodeError, TypeError) as e:
            # Fallback: try to extract information from raw text
            return self._parse_text_response(response, original_query)
    
    def _parse_text_response(self, response: str, original_query: str) -> Optional[ContactInfo]:
        """Fallback parser for non-JSON responses"""
        # Extract emails using regex
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = list(set(re.findall(email_pattern, response)))
        
        # Extract phone numbers using regex
        phone_pattern = r'[\+]?[(]?[0-9]{1,3}[)]?[-\s\.]?[(]?[0-9]{1,4}[)]?[-\s\.]?[0-9]{1,4}[-\s\.]?[0-9]{1,9}'
        phones = list(set(re.findall(phone_pattern, response)))
        
        # Extract URLs
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls = re.findall(url_pattern, response)
        sources = [{"url": url, "title": "Source", "relevance": "Found in response"} for url in urls]
        
        return ContactInfo(
            name=original_query,
            primary_email=emails[0] if emails else "",
            alternate_emails=emails[1:] if len(emails) > 1 else [],
            primary_phone=phones[0] if phones else "",
            alternate_phones=phones[1:] if len(phones) > 1 else [],
            sources=sources,
            confidence_score=0.5,  # Lower confidence for parsed responses
            notes=f"Parsed from text response"
        )
    
    def batch_search(self, queries: List[str], batch_size: int = 10) -> List[ContactInfo]:
        """Search for multiple contacts in batches"""
        results = []
        
        for i in range(0, len(queries), batch_size):
            batch = queries[i:i + batch_size]
            print(f"Processing batch {i//batch_size + 1} of {len(queries)//batch_size + 1}")
            
            for query in batch:
                contacts = self.search_contact(query)
                if contacts:
                    results.extend(contacts)
                    print(f"Found {len(contacts)} contacts for: {query}")
                    for contact in contacts:
                        print(f"  - {contact.name} at {contact.company}")
                else:
                    print(f"No results for: {query}")
        
        return results