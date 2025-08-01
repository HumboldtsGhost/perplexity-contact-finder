"""
Email verification module supporting multiple providers
"""
import requests
import time
from typing import List, Dict, Optional
from abc import ABC, abstractmethod

class EmailVerifier(ABC):
    """Abstract base class for email verifiers"""
    
    @abstractmethod
    def verify_email(self, email: str) -> Dict[str, any]:
        """Verify a single email address"""
        pass
    
    @abstractmethod
    def verify_batch(self, emails: List[str]) -> List[Dict[str, any]]:
        """Verify multiple email addresses"""
        pass

class HunterVerifier(EmailVerifier):
    """Hunter.io email verification"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.hunter.io/v2"
    
    def verify_email(self, email: str) -> Dict[str, any]:
        """Verify a single email using Hunter.io"""
        try:
            url = f"{self.base_url}/email-verifier"
            params = {
                'email': email,
                'api_key': self.api_key
            }
            
            response = requests.get(url, params=params)
            if response.status_code == 200:
                data = response.json()['data']
                return {
                    'email': email,
                    'status': data.get('status', 'unknown'),
                    'score': data.get('score', 0),
                    'result': data.get('result', 'unverifiable'),
                    'provider': 'hunter',
                    'details': {
                        'accept_all': data.get('accept_all', False),
                        'disposable': data.get('disposable', False),
                        'webmail': data.get('webmail', False),
                        'mx_records': data.get('mx_records', False),
                        'smtp_server': data.get('smtp_server', False),
                        'smtp_check': data.get('smtp_check', False),
                        'blocked': data.get('blocked', False)
                    }
                }
            else:
                return {
                    'email': email,
                    'status': 'error',
                    'provider': 'hunter',
                    'error': response.json().get('errors', [{'details': 'Unknown error'}])[0]['details']
                }
                
        except Exception as e:
            return {
                'email': email,
                'status': 'error',
                'provider': 'hunter',
                'error': str(e)
            }
    
    def verify_batch(self, emails: List[str]) -> List[Dict[str, any]]:
        """Verify multiple emails (Hunter doesn't support batch, so we iterate)"""
        results = []
        for email in emails:
            results.append(self.verify_email(email))
            time.sleep(0.5)  # Rate limiting
        return results

class ZeroBounceVerifier(EmailVerifier):
    """ZeroBounce email verification"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.zerobounce.net/v2"
    
    def verify_email(self, email: str) -> Dict[str, any]:
        """Verify a single email using ZeroBounce"""
        try:
            url = f"{self.base_url}/validate"
            params = {
                'email': email,
                'api_key': self.api_key
            }
            
            response = requests.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                return {
                    'email': email,
                    'status': data.get('status', 'unknown'),
                    'sub_status': data.get('sub_status', ''),
                    'score': self._map_status_to_score(data.get('status', 'unknown')),
                    'provider': 'zerobounce',
                    'details': {
                        'firstname': data.get('firstname', ''),
                        'lastname': data.get('lastname', ''),
                        'gender': data.get('gender', ''),
                        'country': data.get('country', ''),
                        'region': data.get('region', ''),
                        'city': data.get('city', ''),
                        'processed_at': data.get('processed_at', '')
                    }
                }
            else:
                return {
                    'email': email,
                    'status': 'error',
                    'provider': 'zerobounce',
                    'error': 'API request failed'
                }
                
        except Exception as e:
            return {
                'email': email,
                'status': 'error',
                'provider': 'zerobounce',
                'error': str(e)
            }
    
    def verify_batch(self, emails: List[str]) -> List[Dict[str, any]]:
        """Verify multiple emails using ZeroBounce batch API"""
        try:
            url = f"{self.base_url}/validatebatch"
            
            # Prepare batch data
            email_batch = [{"email_address": email} for email in emails]
            
            response = requests.post(
                url,
                json={
                    "api_key": self.api_key,
                    "email_batch": email_batch
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                results = []
                
                for item in data.get('email_batch', []):
                    results.append({
                        'email': item.get('address', ''),
                        'status': item.get('status', 'unknown'),
                        'sub_status': item.get('sub_status', ''),
                        'score': self._map_status_to_score(item.get('status', 'unknown')),
                        'provider': 'zerobounce'
                    })
                
                return results
            else:
                # Fallback to individual verification
                return [self.verify_email(email) for email in emails]
                
        except Exception as e:
            # Fallback to individual verification
            return [self.verify_email(email) for email in emails]
    
    def _map_status_to_score(self, status: str) -> float:
        """Map ZeroBounce status to a confidence score"""
        status_scores = {
            'valid': 1.0,
            'catch-all': 0.8,
            'unknown': 0.5,
            'spamtrap': 0.0,
            'abuse': 0.0,
            'do_not_mail': 0.0,
            'invalid': 0.0
        }
        return status_scores.get(status.lower(), 0.5)

class EmailVerificationService:
    """Main service for email verification with fallback support"""
    
    def __init__(self, config):
        self.config = config
        self.verifiers = []
        
        # Initialize available verifiers
        if config.get_api_key('hunter'):
            self.verifiers.append(HunterVerifier(config.get_api_key('hunter')))
        
        if config.get_api_key('zerobounce'):
            self.verifiers.append(ZeroBounceVerifier(config.get_api_key('zerobounce')))
    
    def verify_email(self, email: str) -> Dict[str, any]:
        """Verify an email using available verifiers"""
        if not self.verifiers:
            return {
                'email': email,
                'status': 'unverified',
                'note': 'No email verification service configured'
            }
        
        # Try each verifier until one succeeds
        for verifier in self.verifiers:
            result = verifier.verify_email(email)
            if result.get('status') != 'error':
                return result
        
        # All verifiers failed
        return {
            'email': email,
            'status': 'error',
            'note': 'All verification services failed'
        }
    
    def verify_all_emails(self, contact) -> None:
        """Verify all emails for a contact (primary and alternates)"""
        if not self.config.get_setting('verify_emails'):
            return
        
        # Verify primary email
        if contact.primary_email:
            result = self.verify_email(contact.primary_email)
            contact.verification_status['primary_email'] = result.get('status', 'unverified')
            
            # Update confidence based on verification
            if result.get('score'):
                contact.confidence_score *= result['score']
        
        # Verify alternate emails
        verified_alternates = []
        for email in contact.alternate_emails:
            result = self.verify_email(email)
            if result.get('status') in ['valid', 'catch-all']:
                verified_alternates.append(email)
        
        contact.alternate_emails = verified_alternates