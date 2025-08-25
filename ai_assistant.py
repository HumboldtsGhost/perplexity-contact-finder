"""
AI Assistant Module - Uses Anthropic Claude for intelligent query generation
"""
import json
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import anthropic
from anthropic import Anthropic

logger = logging.getLogger(__name__)

@dataclass
class QuerySuggestion:
    """Represents a suggested search query"""
    query: str
    role: str
    company: str
    contact_types: List[str]
    confidence: float
    reasoning: str

class AIAssistant:
    """AI-powered assistant for query generation and understanding user needs"""
    
    def __init__(self, api_key: str, model: str = "claude-3-haiku-20240307"):
        """Initialize the AI assistant with Anthropic API"""
        self.client = Anthropic(api_key=api_key)
        self.model = model
        self.conversation_history = []
    
    def understand_requirements(self, user_input: str, companies: List[str] = None) -> Dict:
        """
        Understand what the user is looking for through natural language
        Returns structured requirements
        """
        
        # Build context about companies if provided
        company_context = ""
        if companies:
            sample_companies = companies[:5]  # Show first 5 as examples
            company_context = f"""
The user has uploaded a list of {len(companies)} companies/organizations.
Sample entries: {', '.join(sample_companies)}
"""
        
        prompt = f"""You are an expert at understanding contact search requirements for sales teams.
{company_context}
The user said: "{user_input}"

Analyze their request and extract:
1. What roles/positions they're looking for (e.g., CEO, Principal, Operations Manager)
2. What contact information they need (email, phone, LinkedIn, address)
3. Any specific departments or seniority levels
4. Any industry-specific context

Return a JSON object with this structure:
{{
    "roles": ["role1", "role2"],
    "contact_types": ["email", "phone"],
    "departments": ["department1"],
    "seniority_levels": ["C-level", "Director", "Manager"],
    "industry_context": "description",
    "additional_criteria": "any other requirements"
}}

Be specific and practical. For schools, suggest education-specific roles.
For companies, suggest business roles. If the user is vague, make intelligent assumptions."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                temperature=0.2,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Parse the response
            content = response.content[0].text
            
            # Extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                requirements = json.loads(json_match.group())
            else:
                requirements = json.loads(content)
            
            return requirements
            
        except Exception as e:
            logger.error(f"Error understanding requirements: {str(e)}")
            # Return default structure
            return {
                "roles": ["Contact", "Manager"],
                "contact_types": ["email", "phone"],
                "departments": [],
                "seniority_levels": [],
                "industry_context": "",
                "additional_criteria": ""
            }
    
    def generate_queries(self, companies: List[str], requirements: Dict, 
                        max_queries_per_company: int = 2) -> List[QuerySuggestion]:
        """
        Generate optimized Perplexity queries for each company based on requirements
        """
        queries = []
        
        # Prepare the requirements summary
        roles = requirements.get('roles', ['contact'])
        contact_types = requirements.get('contact_types', ['email', 'phone'])
        
        roles_text = ' and '.join(roles) if len(roles) <= 2 else ', '.join(roles)
        contact_text = ' and '.join(contact_types)
        
        # Generate queries for each company
        for company in companies:
            # Determine if this is likely a school, company, or organization
            company_type = self._detect_company_type(company)
            
            # Generate appropriate queries based on type
            if company_type == "school":
                for role in roles[:max_queries_per_company]:
                    query = f"find the {role} {contact_text} for {company}"
                    queries.append(QuerySuggestion(
                        query=query,
                        role=role,
                        company=company,
                        contact_types=contact_types,
                        confidence=0.9,
                        reasoning=f"Direct search for {role} at educational institution"
                    ))
            else:
                # For companies, might want different query patterns
                for role in roles[:max_queries_per_company]:
                    query = f"find {role} {contact_text} contact information {company}"
                    queries.append(QuerySuggestion(
                        query=query,
                        role=role,
                        company=company,
                        contact_types=contact_types,
                        confidence=0.9,
                        reasoning=f"Standard business contact search for {role}"
                    ))
        
        return queries
    
    def _detect_company_type(self, company_name: str) -> str:
        """Detect if the entity is a school, company, or other organization"""
        company_lower = company_name.lower()
        
        school_keywords = ['school', 'elementary', 'middle', 'high', 'academy', 
                          'university', 'college', 'institute', 'education']
        nonprofit_keywords = ['foundation', 'charity', 'nonprofit', 'association', 'society']
        government_keywords = ['department', 'agency', 'administration', 'bureau', 'commission']
        
        for keyword in school_keywords:
            if keyword in company_lower:
                return "school"
        
        for keyword in nonprofit_keywords:
            if keyword in company_lower:
                return "nonprofit"
        
        for keyword in government_keywords:
            if keyword in company_lower:
                return "government"
        
        return "company"
    
    def improve_query(self, original_query: str, context: Dict = None) -> str:
        """
        Take a user's query and improve it for better Perplexity results
        """
        prompt = f"""Improve this search query for finding specific contact information:

Original query: "{original_query}"

Make it more specific and likely to find actual contact details (email, phone).
Add relevant keywords that help find the exact person and their contact info.
Keep it concise but effective.

Return only the improved query, nothing else."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=200,
                temperature=0.1,
                messages=[{"role": "user", "content": prompt}]
            )
            
            improved = response.content[0].text.strip()
            return improved if improved else original_query
            
        except Exception as e:
            logger.error(f"Error improving query: {str(e)}")
            return original_query
    
    def suggest_roles_for_industry(self, companies: List[str]) -> Dict[str, List[str]]:
        """
        Suggest relevant roles based on the types of companies/organizations
        Returns both recommended and optional roles with explanations
        """
        # Take a sample of companies to understand the industry
        sample = companies[:10] if len(companies) > 10 else companies
        sample_text = ', '.join(sample)
        
        prompt = f"""Based on these organizations, suggest the most relevant decision-maker roles to contact:

Organizations: {sample_text}

Analyze the industry/type and suggest roles in two categories:
1. PRIMARY roles (must contact - key decision makers)
2. SECONDARY roles (good to have - supporting decision makers)

For each role, explain WHY they're important for this industry.

Return JSON format:
{{
    "industry_type": "detected industry",
    "primary_roles": [
        {{"role": "Title", "reason": "Why this role is critical"}},
        ...
    ],
    "secondary_roles": [
        {{"role": "Title", "reason": "Why this role could be valuable"}},
        ...
    ],
    "insights": "Key insight about contacting these organizations"
}}"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=500,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}]
            )
            
            content = response.content[0].text.strip()
            
            # Parse JSON
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                result = json.loads(content)
            
            return result
            
        except Exception as e:
            logger.error(f"Error suggesting roles: {str(e)}")
            # Return generic structure as fallback
            return {
                "industry_type": "General Business",
                "primary_roles": [
                    {"role": "CEO", "reason": "Primary decision maker"},
                    {"role": "President", "reason": "Senior leadership"}
                ],
                "secondary_roles": [
                    {"role": "Manager", "reason": "Department head"},
                    {"role": "Director", "reason": "Strategic decisions"}
                ],
                "insights": "Focus on senior decision makers"
            }
    
    def validate_queries(self, queries: List[str]) -> List[Dict]:
        """
        Validate and score a list of queries for quality
        """
        results = []
        
        for query in queries:
            validation = {
                'query': query,
                'is_specific': len(query.split()) > 3,
                'has_role': any(role in query.lower() for role in 
                              ['ceo', 'president', 'director', 'manager', 'principal', 
                               'owner', 'founder', 'head', 'chief']),
                'has_contact_type': any(ct in query.lower() for ct in 
                                       ['email', 'phone', 'contact', 'linkedin']),
                'quality_score': 0.0
            }
            
            # Calculate quality score
            score = 0.0
            if validation['is_specific']:
                score += 0.3
            if validation['has_role']:
                score += 0.4
            if validation['has_contact_type']:
                score += 0.3
            
            validation['quality_score'] = score
            validation['recommendation'] = self._get_recommendation(validation)
            
            results.append(validation)
        
        return results
    
    def _get_recommendation(self, validation: Dict) -> str:
        """Get recommendation for improving a query based on validation"""
        if validation['quality_score'] >= 0.8:
            return "Good query"
        
        recommendations = []
        if not validation['has_role']:
            recommendations.append("Add specific role (e.g., CEO, Principal)")
        if not validation['has_contact_type']:
            recommendations.append("Specify contact type (email, phone)")
        if not validation['is_specific']:
            recommendations.append("Add more detail")
        
        return "; ".join(recommendations) if recommendations else "Query could be improved"
    
    def batch_optimize_queries(self, queries: List[str]) -> List[str]:
        """
        Optimize multiple queries in batch for efficiency
        """
        # Group similar queries and optimize
        optimized = []
        
        for query in queries:
            # Simple optimization rules
            optimized_query = query
            
            # Ensure query asks for specific contact info
            if 'contact' not in query.lower() and 'email' not in query.lower() and 'phone' not in query.lower():
                optimized_query += " contact information email phone"
            
            # Add context clues for better results
            if 'find' not in query.lower() and 'get' not in query.lower():
                optimized_query = f"find {optimized_query}"
            
            optimized.append(optimized_query)
        
        return optimized