"""
Enhanced Search Module - Implements multi-stage, iterative searching for comprehensive results
"""
import json
import time
from typing import List, Dict, Set
from perplexity_client import PerplexityClient, ContactInfo
import logging

logger = logging.getLogger(__name__)

class EnhancedSearchStrategy:
    """Implements aggressive multi-stage search strategies for comprehensive contact discovery"""
    
    def __init__(self, perplexity_client: PerplexityClient):
        self.client = perplexity_client
        self.found_contacts = {}  # Track unique contacts by email
        self.processed_queries = set()  # Avoid duplicate searches
        
    def generate_expanded_queries(self, base_query: str) -> List[str]:
        """Generate multiple query variations for comprehensive coverage"""
        queries = []
        query_lower = base_query.lower()
        
        # Start with the original query
        queries.append(base_query)
        
        # Add variations based on the type of query
        if any(word in query_lower for word in ['contractor', 'company', 'business', 'service', 
                                                  'roofer', 'plumber', 'electrician', 'carpenter',
                                                  'painter', 'landscaper', 'hvac', 'builder']):
            # Business/contractor queries
            queries.extend([
                f"list of {base_query}",
                f"all {base_query} with contact information",
                f"{base_query} owner names and emails",
                f"{base_query} business owner directory",
                f"complete list {base_query}",
                f"{base_query} decision maker contacts",
                f"top {base_query} with phone numbers",
                f"{base_query} email directory",
                f"find all {base_query}",
                f"{base_query} contact database"
            ])
        elif any(word in query_lower for word in ['restaurant', 'retail', 'store', 'shop', 'cafe']):
            # Retail/restaurant queries
            queries.extend([
                f"{base_query} owner contacts",
                f"{base_query} manager directory",
                f"all {base_query} with emails",
                f"{base_query} business directory",
                f"list of {base_query} owners"
            ])
        elif any(word in query_lower for word in ['director', 'manager', 'executive', 'ceo', 'cto', 'cfo']):
            # Executive/leadership queries
            queries.extend([
                f"{base_query} contact list",
                f"all {base_query} email addresses",
                f"{base_query} directory with phone",
                f"complete list of {base_query}",
                f"{base_query} contact information"
            ])
        else:
            # Generic queries
            queries.extend([
                f"list of {base_query}",
                f"all {base_query}",
                f"{base_query} contact information",
                f"{base_query} directory",
                f"find {base_query}",
                f"{base_query} with email and phone"
            ])
        
        # Remove duplicates while preserving order
        seen = set()
        unique_queries = []
        for q in queries:
            if q not in seen and q not in self.processed_queries:
                seen.add(q)
                unique_queries.append(q)
        
        return unique_queries[:15]  # Return top 15 variations
    
    def _search_with_tracking(self, query: str) -> List[ContactInfo]:
        """Execute search and track unique results"""
        try:
            results = self.client.search_contact(query)
            self.processed_queries.add(query)
            
            # Track unique contacts
            unique_results = []
            for contact in results:
                # Use email as unique identifier
                if contact.primary_email and contact.primary_email not in self.found_contacts:
                    self.found_contacts[contact.primary_email] = contact
                    unique_results.append(contact)
                elif not contact.primary_email:
                    # If no email, still include but can't deduplicate
                    unique_results.append(contact)
                    
            return unique_results
            
        except Exception as e:
            logger.error(f"Error searching {query}: {e}")
            return []
    
    def iterative_deep_search(self, initial_query: str, max_iterations: int = 3) -> List[ContactInfo]:
        """Perform deep iterative searching with refinement"""
        all_results = []
        
        logger.info(f"Starting enhanced search for: {initial_query}")
        
        # Stage 1: Variations of the original query
        print(f"\n🔍 Enhanced search: Generating query variations...")
        queries = self.generate_expanded_queries(initial_query)
        
        for i, query in enumerate(queries, 1):
            if len(self.found_contacts) >= 50:  # Stop if we have enough results
                break
                
            print(f"   [{i}/{len(queries)}] Searching: {query[:60]}...")
            results = self._search_with_tracking(query)
            if results:
                all_results.extend(results)
                print(f"      ✓ Found {len(results)} new contacts")
            time.sleep(1.5)  # Rate limiting
        
        print(f"\n✅ Enhanced search complete: Found {len(self.found_contacts)} unique contacts")
        
        # Return all unique contacts found
        return list(self.found_contacts.values()) + [c for c in all_results if not c.primary_email]