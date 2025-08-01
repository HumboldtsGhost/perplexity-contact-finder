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
        
    def extract_entities_from_results(self, results: List[ContactInfo]) -> Dict[str, Set[str]]:
        """Extract entities (schools, districts, cities) from initial results for follow-up searches"""
        entities = {
            'schools': set(),
            'districts': set(),
            'cities': set(),
            'titles': set(),
            'departments': set()
        }
        
        for contact in results:
            # Extract from company/organization field
            if contact.company:
                if 'school' in contact.company.lower():
                    entities['schools'].add(contact.company)
                elif 'district' in contact.company.lower():
                    entities['districts'].add(contact.company)
                    
            # Extract from notes and sources
            if contact.notes:
                # Look for patterns like "XYZ School District"
                words = contact.notes.split()
                for i in range(len(words) - 1):
                    if words[i+1].lower() == 'district':
                        entities['districts'].add(f"{words[i]} District")
                    elif words[i+1].lower() in ['elementary', 'middle', 'high']:
                        entities['schools'].add(f"{words[i]} {words[i+1]}")
                        
        return entities
    
    def generate_expanded_queries(self, base_query: str, location: str = "") -> List[str]:
        """Generate multiple query variations for comprehensive coverage"""
        queries = []
        
        # Different title variations for IT directors
        it_titles = [
            "IT Director",
            "Technology Director", 
            "Chief Technology Officer",
            "CTO",
            "Director of Technology",
            "Technology Coordinator",
            "IT Manager",
            "Technology Manager",
            "Director of Information Technology",
            "Chief Information Officer",
            "CIO",
            "Technology Specialist",
            "Network Administrator",
            "Systems Administrator"
        ]
        
        # Query patterns
        patterns = [
            "{title} {location} public schools contact list",
            "all {title}s in {location} school districts",
            "{location} school district {title} directory",
            "list of {title}s {location} K-12 schools",
            "{location} public schools technology department contacts",
            "{title} email addresses {location} schools",
            "complete list {title} {location} education",
            "{location} school technology leaders contact information",
            "who is the {title} for {location} schools",
            "{location} district technology staff directory"
        ]
        
        # Generate queries for each title and pattern combination
        for title in it_titles:
            for pattern in patterns:
                query = pattern.format(title=title, location=location)
                if query not in self.processed_queries:
                    queries.append(query)
                    
        # Add specific district searches
        if location.lower() == "north carolina":
            # Major NC school districts
            major_districts = [
                "Wake County", "Charlotte-Mecklenburg", "Guilford County",
                "Forsyth County", "Cumberland County", "Durham", 
                "Buncombe County", "Union County", "Cabarrus County",
                "Johnston County", "Pitt County", "Onslow County",
                "New Hanover County", "Alamance-Burlington", "Chapel Hill-Carrboro"
            ]
            
            for district in major_districts:
                for title in it_titles[:5]:  # Use top 5 titles
                    query = f"{title} {district} Schools North Carolina contact"
                    if query not in self.processed_queries:
                        queries.append(query)
                        
        return queries
    
    def search_by_regions(self, state: str) -> List[str]:
        """Break down state into regions for more targeted searches"""
        regional_queries = []
        
        if state.lower() == "north carolina":
            regions = [
                "Western North Carolina", "Piedmont North Carolina",
                "Eastern North Carolina", "Charlotte metro area",
                "Raleigh-Durham area", "Triad area North Carolina",
                "Coastal North Carolina", "Mountain region North Carolina"
            ]
            
            for region in regions:
                regional_queries.extend([
                    f"IT directors {region} schools",
                    f"technology coordinators {region} school districts",
                    f"K-12 technology staff {region}"
                ])
                
        return regional_queries
    
    def iterative_deep_search(self, initial_query: str, max_iterations: int = 5) -> List[ContactInfo]:
        """Perform deep iterative searching with refinement"""
        all_results = []
        iteration = 1
        
        # Extract location from query
        location = "North Carolina"  # Default, could be extracted better
        if "north carolina" in initial_query.lower():
            location = "North Carolina"
            
        logger.info(f"Starting enhanced search with max {max_iterations} iterations")
        
        # Stage 1: Broad searches
        print(f"\n🔍 Stage 1: Broad search queries...")
        broad_queries = self.generate_expanded_queries(initial_query, location)[:10]
        
        for query in broad_queries:
            if query not in self.processed_queries:
                print(f"   Searching: {query[:60]}...")
                results = self._search_with_tracking(query)
                all_results.extend(results)
                time.sleep(1)  # Rate limiting
                
        print(f"   ✓ Found {len(self.found_contacts)} unique contacts so far")
        
        # Stage 2: Regional searches
        print(f"\n🔍 Stage 2: Regional searches...")
        regional_queries = self.search_by_regions(location)[:10]
        
        for query in regional_queries:
            if query not in self.processed_queries:
                print(f"   Searching: {query[:60]}...")
                results = self._search_with_tracking(query)
                all_results.extend(results)
                time.sleep(1)
                
        print(f"   ✓ Found {len(self.found_contacts)} unique contacts so far")
        
        # Stage 3: Entity-based searches (search specific districts/schools found)
        if all_results:
            print(f"\n🔍 Stage 3: Targeted searches based on discovered entities...")
            entities = self.extract_entities_from_results(all_results)
            
            # Search specific districts found
            for district in list(entities['districts'])[:20]:  # Top 20 districts
                query = f"IT director technology coordinator {district} contact email"
                if query not in self.processed_queries:
                    print(f"   Searching: {district}...")
                    results = self._search_with_tracking(query)
                    all_results.extend(results)
                    time.sleep(1)
                    
        print(f"\n✅ Enhanced search complete! Found {len(self.found_contacts)} unique contacts")
        
        # Return unique contacts
        return list(self.found_contacts.values())
    
    def _search_with_tracking(self, query: str) -> List[ContactInfo]:
        """Search and track unique results"""
        self.processed_queries.add(query)
        
        try:
            # Use Perplexity to search
            contact = self.client.search_contact(query)
            
            if contact:
                # Check if we already have this contact (by email)
                if contact.primary_email and contact.primary_email not in self.found_contacts:
                    self.found_contacts[contact.primary_email] = contact
                    return [contact]
                elif not contact.primary_email and contact.name:
                    # No email but has name - still worth keeping
                    key = f"{contact.name}_{contact.company}"
                    if key not in self.found_contacts:
                        self.found_contacts[key] = contact
                        return [contact]
                        
        except Exception as e:
            logger.error(f"Error searching {query}: {e}")
            
        return []
    
    def suggest_better_query(self, original_query: str) -> str:
        """Use AI to suggest a better query"""
        prompt = f"""
        The user searched for: "{original_query}"
        
        This query needs to be improved to find MORE contacts (not just one or two).
        Generate a better search query that will find a comprehensive list of contacts.
        
        Make the query:
        1. More specific about wanting multiple results
        2. Include words like "list", "all", "directory", "complete"
        3. Be clear about the geographic scope
        4. Include multiple title variations
        
        Return only the improved query, nothing else.
        """
        
        try:
            # We can use Perplexity itself to improve queries
            improved = self.client.search_contact(prompt)
            if improved and improved.raw_response:
                return improved.raw_response.strip()
        except:
            pass
            
        # Fallback improvement
        if "north carolina" in original_query.lower():
            return f"complete list all IT directors technology coordinators North Carolina public school districts contact information email addresses"
        
        return f"comprehensive list all {original_query} contact directory email addresses"