#!/usr/bin/env python3
"""
FastAPI backend for Perplexity Contact Finder
"""
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Optional
import json
import os
from pathlib import Path
from datetime import datetime
import asyncio
import uuid
import tempfile

from config import Config
from perplexity_client import PerplexityClient, ContactInfo
from email_verifier import EmailVerificationService
from phone_verifier import PhoneVerificationService
from data_exporter import DataExporter
from enhanced_search import EnhancedSearchStrategy
from perplexity_contact_finder import ContactFinder, SEARCH_TEMPLATES

app = FastAPI(title="Contact Finder Pro API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
search_jobs = {}
finder_instance = None

# Request/Response models
class SearchRequest(BaseModel):
    query: str
    enhanced: bool = False
    verify_emails: bool = False
    verify_phones: bool = False

class BatchSearchRequest(BaseModel):
    queries: List[str]
    enhanced: bool = False
    verify: bool = False

class TemplateSearchRequest(BaseModel):
    template_key: str
    field_values: Dict[str, str]
    enhanced: bool = False

class ApiKeysRequest(BaseModel):
    perplexity: str
    hunter: Optional[str] = None
    zerobounce: Optional[str] = None
    numverify: Optional[str] = None
    twilio_account_sid: Optional[str] = None
    twilio_auth_token: Optional[str] = None

class ExportRequest(BaseModel):
    contacts: List[dict]
    format: str  # csv, excel, json, apollo

def get_finder():
    """Get or create ContactFinder instance"""
    global finder_instance
    if finder_instance is None:
        config_file = Path('config.json')
        if config_file.exists():
            try:
                finder_instance = ContactFinder('config.json')
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to initialize: {str(e)}")
        else:
            raise HTTPException(status_code=400, detail="Please configure API keys first")
    return finder_instance

@app.get("/")
async def serve_homepage():
    """Serve the main HTML page"""
    return FileResponse('static/index.html')

@app.get("/api/config/status")
async def get_config_status():
    """Check if API keys are configured"""
    config_file = Path('config.json')
    if not config_file.exists():
        return {"configured": False, "services": {}}
    
    try:
        config = Config('config.json')
        services = {
            'perplexity': bool(config.get_api_key('perplexity')),
            'hunter': bool(config.get_api_key('hunter')),
            'zerobounce': bool(config.get_api_key('zerobounce')),
            'numverify': bool(config.get_api_key('numverify')),
            'twilio': bool(config.get_api_key('twilio_account_sid'))
        }
        return {
            "configured": services['perplexity'],
            "services": services
        }
    except:
        return {"configured": False, "services": {}}

@app.post("/api/config/save")
async def save_config(keys: ApiKeysRequest):
    """Save API key configuration"""
    if not keys.perplexity:
        raise HTTPException(status_code=400, detail="Perplexity API key is required")
    
    config = Config('config.json')
    config.set_api_key('perplexity', keys.perplexity)
    
    if keys.hunter:
        config.set_api_key('hunter', keys.hunter)
    if keys.zerobounce:
        config.set_api_key('zerobounce', keys.zerobounce)
    if keys.numverify:
        config.set_api_key('numverify', keys.numverify)
    if keys.twilio_account_sid:
        config.set_api_key('twilio_account_sid', keys.twilio_account_sid)
    if keys.twilio_auth_token:
        config.set_api_key('twilio_auth_token', keys.twilio_auth_token)
    
    config.save_to_file()
    
    # Reset finder instance to use new config
    global finder_instance
    finder_instance = None
    
    return {"success": True, "message": "Configuration saved successfully"}

@app.get("/api/templates")
async def get_templates():
    """Get available search templates"""
    templates_with_info = {}
    for key, template in SEARCH_TEMPLATES.items():
        templates_with_info[key] = {
            "name": template.get("name", key),
            "description": template.get("description", ""),
            "fields": template.get("fields", []),
            "examples": template.get("examples", [])[:2]  # Just first 2 examples
        }
    return templates_with_info

@app.post("/api/search")
async def search_contacts(request: SearchRequest):
    """Perform a single search"""
    finder = get_finder()
    
    try:
        if request.enhanced:
            enhanced_searcher = EnhancedSearchStrategy(finder.perplexity)
            results = enhanced_searcher.iterative_deep_search(request.query)
        else:
            results = finder.perplexity.search_contact(request.query)
        
        if results:
            # Verify if requested
            if request.verify_emails:
                for contact in results:
                    finder.email_verifier.verify_all_emails(contact)
            
            if request.verify_phones:
                for contact in results:
                    finder.phone_verifier.verify_all_phones(contact)
            
            # Convert to dict for JSON response
            results_dict = []
            for contact in results:
                results_dict.append({
                    'name': contact.name,
                    'company': contact.company,
                    'primary_email': contact.primary_email,
                    'alternate_emails': contact.alternate_emails,
                    'primary_phone': contact.primary_phone,
                    'alternate_phones': contact.alternate_phones,
                    'sources': contact.sources,
                    'confidence_score': contact.confidence_score,
                    'verification_status': contact.verification_status,
                    'notes': contact.notes,
                    'date_found': contact.date_found
                })
            
            return {
                "success": True,
                "count": len(results_dict),
                "results": results_dict
            }
        else:
            return {
                "success": True,
                "count": 0,
                "results": []
            }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/search/batch")
async def batch_search(request: BatchSearchRequest, background_tasks: BackgroundTasks):
    """Start a batch search job"""
    job_id = str(uuid.uuid4())
    search_jobs[job_id] = {
        "status": "running",
        "progress": 0,
        "total": len(request.queries),
        "results": [],
        "errors": []
    }
    
    # Run search in background
    background_tasks.add_task(
        run_batch_search,
        job_id,
        request.queries,
        request.enhanced,
        request.verify
    )
    
    return {"job_id": job_id, "total_queries": len(request.queries)}

async def run_batch_search(job_id: str, queries: List[str], enhanced: bool, verify: bool):
    """Execute batch search in background"""
    finder = get_finder()
    
    for i, query in enumerate(queries):
        try:
            if enhanced:
                enhanced_searcher = EnhancedSearchStrategy(finder.perplexity)
                results = enhanced_searcher.iterative_deep_search(query)
            else:
                results = finder.perplexity.search_contact(query)
            
            if results:
                if verify:
                    for contact in results:
                        finder.email_verifier.verify_all_emails(contact)
                        finder.phone_verifier.verify_all_phones(contact)
                
                # Convert to dict
                for contact in results:
                    search_jobs[job_id]["results"].append({
                        'name': contact.name,
                        'company': contact.company,
                        'primary_email': contact.primary_email,
                        'alternate_emails': contact.alternate_emails,
                        'primary_phone': contact.primary_phone,
                        'alternate_phones': contact.alternate_phones,
                        'sources': contact.sources,
                        'confidence_score': contact.confidence_score,
                        'verification_status': contact.verification_status,
                        'date_found': contact.date_found
                    })
            
            search_jobs[job_id]["progress"] = i + 1
            await asyncio.sleep(1)  # Rate limiting
            
        except Exception as e:
            search_jobs[job_id]["errors"].append({
                "query": query,
                "error": str(e)
            })
    
    search_jobs[job_id]["status"] = "completed"

@app.get("/api/search/status/{job_id}")
async def get_search_status(job_id: str):
    """Get status of a batch search job"""
    if job_id not in search_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return search_jobs[job_id]

@app.post("/api/search/template")
async def search_with_template(request: TemplateSearchRequest):
    """Search using a template"""
    template = SEARCH_TEMPLATES.get(request.template_key)
    if not template:
        raise HTTPException(status_code=400, detail="Invalid template")
    
    # Generate query from template
    examples = template.get('examples', [])
    if not examples:
        raise HTTPException(status_code=400, detail="Template has no examples")
    
    query_template = examples[0]
    query = query_template
    
    for field, value in request.field_values.items():
        query = query.replace(f"{{{field}}}", value)
    
    # Perform search
    search_req = SearchRequest(
        query=query,
        enhanced=request.enhanced,
        verify_emails=False,
        verify_phones=False
    )
    
    return await search_contacts(search_req)

@app.post("/api/export")
async def export_contacts(request: ExportRequest):
    """Export contacts to specified format"""
    exporter = DataExporter()
    
    # Convert dicts back to ContactInfo objects
    contacts = []
    for contact_dict in request.contacts:
        contact = ContactInfo(
            name=contact_dict.get('name', ''),
            company=contact_dict.get('company', ''),
            primary_email=contact_dict.get('primary_email', ''),
            alternate_emails=contact_dict.get('alternate_emails', []),
            primary_phone=contact_dict.get('primary_phone', ''),
            alternate_phones=contact_dict.get('alternate_phones', []),
            sources=contact_dict.get('sources', []),
            confidence_score=contact_dict.get('confidence_score', 0),
            verification_status=contact_dict.get('verification_status', {}),
            notes=contact_dict.get('notes', ''),
            date_found=contact_dict.get('date_found', datetime.now().isoformat())
        )
        contacts.append(contact)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    try:
        if request.format == 'csv':
            filepath = exporter.export_to_csv(contacts, f"contacts_{timestamp}.csv")
        elif request.format == 'excel':
            filepath = exporter.export_to_excel(contacts, f"contacts_{timestamp}.xlsx")
        elif request.format == 'json':
            filepath = exporter.export_to_json(contacts, f"contacts_{timestamp}.json")
        elif request.format == 'apollo':
            filepath = exporter.export_to_apollo_csv(contacts, f"apollo_{timestamp}.csv")
        else:
            raise HTTPException(status_code=400, detail="Invalid export format")
        
        return FileResponse(
            filepath,
            media_type='application/octet-stream',
            filename=os.path.basename(filepath)
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/analyze-manual-search")
async def analyze_manual_search(request: dict):
    """Analyze manual search input and suggest roles"""
    description = request.get('description', '')
    companies = request.get('companies', [])
    industry = request.get('industry', '')
    location = request.get('location', '')
    
    # Determine industry type from description
    industry_keywords = {
        'tech': ['software', 'tech', 'IT', 'SaaS', 'app', 'digital', 'web'],
        'healthcare': ['medical', 'health', 'hospital', 'clinic', 'doctor', 'pharma'],
        'retail': ['retail', 'store', 'shop', 'ecommerce', 'sales'],
        'manufacturing': ['manufacturing', 'factory', 'production', 'industrial'],
        'finance': ['finance', 'bank', 'investment', 'insurance', 'accounting'],
        'construction': ['construction', 'building', 'contractor', 'real estate'],
        'hospitality': ['restaurant', 'hotel', 'hospitality', 'food', 'dining'],
        'education': ['school', 'university', 'education', 'training', 'academy'],
        'nonprofit': ['nonprofit', 'charity', 'foundation', 'NGO', 'volunteer'],
        'government': ['government', 'municipal', 'federal', 'state', 'public sector']
    }
    
    detected_industry = industry or 'general'
    for ind, keywords in industry_keywords.items():
        if any(kw.lower() in description.lower() for kw in keywords):
            detected_industry = ind
            break
    
    # Define role suggestions based on industry
    role_suggestions = {
        'tech': {
            'primary_roles': [
                {'role': 'CEO', 'reason': 'Primary decision maker for technology companies'},
                {'role': 'CTO', 'reason': 'Technical decision maker and product leader'},
                {'role': 'VP of Engineering', 'reason': 'Manages engineering teams and technical roadmap'}
            ],
            'secondary_roles': [
                {'role': 'Head of Sales', 'reason': 'Drives revenue and customer acquisition'},
                {'role': 'Product Manager', 'reason': 'Defines product strategy and features'}
            ]
        },
        'healthcare': {
            'primary_roles': [
                {'role': 'Administrator', 'reason': 'Manages healthcare facility operations'},
                {'role': 'Medical Director', 'reason': 'Oversees clinical operations'},
                {'role': 'Practice Manager', 'reason': 'Handles day-to-day operations'}
            ],
            'secondary_roles': [
                {'role': 'Chief Medical Officer', 'reason': 'Senior medical executive'},
                {'role': 'Operations Manager', 'reason': 'Manages operational efficiency'}
            ]
        },
        'general': {
            'primary_roles': [
                {'role': 'Owner', 'reason': 'Primary decision maker and business owner'},
                {'role': 'President', 'reason': 'Senior executive responsible for operations'},
                {'role': 'CEO', 'reason': 'Chief Executive Officer and primary leader'}
            ],
            'secondary_roles': [
                {'role': 'General Manager', 'reason': 'Manages overall business operations'},
                {'role': 'Operations Manager', 'reason': 'Handles day-to-day operations'}
            ]
        }
    }
    
    # Get appropriate roles for the detected industry
    roles = role_suggestions.get(detected_industry, role_suggestions['general'])
    
    return {
        'industry_type': detected_industry.title(),
        'insights': f'Based on your search for {detected_industry} companies, here are recommended roles to target',
        'primary_roles': roles['primary_roles'],
        'secondary_roles': roles['secondary_roles']
    }

@app.post("/api/generate-queries")
async def generate_queries(request: dict):
    """Generate search queries from companies and roles"""
    companies = request.get('companies', [])
    roles = request.get('roles', [])
    
    if not roles:
        raise HTTPException(status_code=400, detail="No roles selected")
    
    # Generate queries combining each company with each role
    queries_list = []
    for company in companies if companies else ['']:
        for role in roles:
            if company:
                # Specific company query
                query = f"{role} at {company} contact email phone"
            else:
                # General search query (for manual search without specific companies)
                query = f"{role} contact information email phone"
            
            queries_list.append({
                'company': company or 'General Search',
                'role': role,
                'query': query
            })
    
    return {
        "queries": queries_list,
        "total": len(queries_list)
    }

@app.post("/api/upload")
async def upload_queries(file: UploadFile = File(...)):
    """Upload a file with queries or companies"""
    try:
        content = await file.read()
        text = content.decode('utf-8')
        
        # Check if it's a CSV file
        if file.filename.endswith('.csv'):
            import csv
            import io
            
            # Parse CSV
            csv_reader = csv.reader(io.StringIO(text))
            companies = []
            
            # Try to detect if there's a header
            first_row = next(csv_reader, None)
            if first_row:
                # If first row looks like a header (contains common header words), skip it
                header_words = ['company', 'name', 'business', 'organization']
                is_header = any(word.lower() in first_row[0].lower() for word in header_words)
                
                if not is_header:
                    companies.append(first_row[0])
                
                # Read all remaining rows (no limit)
                for row in csv_reader:
                    if row and row[0].strip():
                        companies.append(row[0].strip())
            
            return {
                "success": True,
                "companies": companies,
                "count": len(companies)
            }
        else:
            # Plain text file - treat each line as a company
            companies = [q.strip() for q in text.split('\n') if q.strip()]
            
            return {
                "success": True,
                "companies": companies,
                "count": len(companies)
            }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing file: {str(e)}")

# Mount static files
static_dir = Path("static")
if static_dir.exists():
    app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)