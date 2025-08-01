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
    
    def search_contact(self, query: str, additional_context: str = "") -> Optional[ContactInfo]:
        """Search for contact information using Perplexity"""
        
        # Construct the prompt for finding contact information
        system_prompt = """You are a professional contact researcher. When given a query about finding contact information:
1. Search for all available contact information including emails and phone numbers
2. Always cite your sources with full URLs
3. Include ALL email addresses and phone numbers you find, even if they seem like alternates
4. Format your response as JSON with the following structure:
{
    "name": "Full Name",
    "company": "Company Name",
    "emails": ["primary@email.com", "alternate1@email.com", "alternate2@email.com"],
    "phones": ["+1-555-123-4567", "+1-555-987-6543"],
    "sources": [
        {"url": "https://example.com/page", "title": "Page Title", "relevance": "Contains direct contact info"},
        {"url": "https://linkedin.com/in/profile", "title": "LinkedIn Profile", "relevance": "Professional profile"}
    ],
    "confidence": 0.95,
    "notes": "Any additional relevant information"
}"""

        user_prompt = f"""Find contact information for: {query}
{additional_context}

Please search thoroughly and include:
- All email addresses found (primary and any alternates)
- All phone numbers found (office, mobile, etc.)
- Source URLs where each piece of information was found
- Your confidence level in the accuracy

Respond ONLY with the JSON structure specified."""

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
                
                # Parse JSON response
                contact_data = self._parse_response(raw_response, query)
                contact_data.raw_response = raw_response
                
                return contact_data
                
            except Exception as e:
                retries += 1
                if retries >= self.max_retries:
                    print(f"Error searching for {query}: {str(e)}")
                    return None
                time.sleep(2 ** retries)  # Exponential backoff
        
        return None
    
    def _parse_response(self, response: str, original_query: str) -> ContactInfo:
        """Parse the JSON response from Perplexity"""
        try:
            # Extract JSON from response (in case there's extra text)
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                data = json.loads(response)
            
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
                confidence_score=data.get('confidence', 0.0),
                notes=data.get('notes', '')
            )
            
            return contact
            
        except json.JSONDecodeError:
            # Fallback: try to extract information from raw text
            return self._parse_text_response(response, original_query)
    
    def _parse_text_response(self, response: str, original_query: str) -> ContactInfo:
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
                contact = self.search_contact(query)
                if contact:
                    results.append(contact)
                    print(f"Found: {contact.name} - {contact.primary_email}")
                else:
                    print(f"No results for: {query}")
        
        return results