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

@app.post("/api/upload")
async def upload_queries(file: UploadFile = File(...)):
    """Upload a file with queries"""
    try:
        content = await file.read()
        text = content.decode('utf-8')
        queries = [q.strip() for q in text.split('\n') if q.strip()]
        
        return {
            "success": True,
            "queries": queries,
            "count": len(queries)
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