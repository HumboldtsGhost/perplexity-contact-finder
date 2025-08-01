"""
Phone number verification module supporting multiple providers
"""
import requests
import phonenumbers
from phonenumbers import carrier, geocoder
from typing import Dict, Optional
from abc import ABC, abstractmethod

class PhoneVerifier(ABC):
    """Abstract base class for phone verifiers"""
    
    @abstractmethod
    def verify_phone(self, phone: str, country_code: str = None) -> Dict[str, any]:
        """Verify a single phone number"""
        pass

class NumverifyVerifier(PhoneVerifier):
    """Numverify phone verification"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "http://apilayer.net/api/validate"
    
    def verify_phone(self, phone: str, country_code: str = None) -> Dict[str, any]:
        """Verify a phone number using Numverify"""
        try:
            params = {
                'access_key': self.api_key,
                'number': phone
            }
            
            if country_code:
                params['country_code'] = country_code
            
            response = requests.get(self.base_url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('valid'):
                    return {
                        'phone': phone,
                        'valid': True,
                        'formatted': data.get('international_format', phone),
                        'local_format': data.get('local_format', ''),
                        'country_code': data.get('country_code', ''),
                        'country_name': data.get('country_name', ''),
                        'location': data.get('location', ''),
                        'carrier': data.get('carrier', ''),
                        'line_type': data.get('line_type', ''),
                        'provider': 'numverify'
                    }
                else:
                    return {
                        'phone': phone,
                        'valid': False,
                        'provider': 'numverify',
                        'error': 'Invalid phone number'
                    }
            else:
                return {
                    'phone': phone,
                    'valid': False,
                    'provider': 'numverify',
                    'error': 'API request failed'
                }
                
        except Exception as e:
            return {
                'phone': phone,
                'valid': False,
                'provider': 'numverify',
                'error': str(e)
            }

class TwilioVerifier(PhoneVerifier):
    """Twilio phone verification using Lookup API"""
    
    def __init__(self, account_sid: str, auth_token: str):
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.base_url = f"https://lookups.twilio.com/v2/PhoneNumbers"
    
    def verify_phone(self, phone: str, country_code: str = None) -> Dict[str, any]:
        """Verify a phone number using Twilio Lookup"""
        try:
            # Format phone number for Twilio (should include country code)
            if not phone.startswith('+'):
                if country_code:
                    phone = f"+{country_code}{phone}"
                else:
                    # Try to parse and format
                    try:
                        parsed = phonenumbers.parse(phone, None)
                        phone = f"+{parsed.country_code}{parsed.national_number}"
                    except:
                        phone = f"+1{phone}"  # Default to US
            
            url = f"{self.base_url}/{phone}"
            
            response = requests.get(
                url,
                auth=(self.account_sid, self.auth_token),
                params={'Fields': 'line_type_intelligence,caller_name'}
            )
            
            if response.status_code == 200:
                data = response.json()
                
                return {
                    'phone': phone,
                    'valid': True,
                    'formatted': data.get('phone_number', phone),
                    'country_code': data.get('country_code', ''),
                    'carrier': data.get('carrier', {}).get('name', ''),
                    'line_type': data.get('line_type_intelligence', {}).get('type', ''),
                    'caller_name': data.get('caller_name', {}).get('caller_name', ''),
                    'provider': 'twilio'
                }
            else:
                return {
                    'phone': phone,
                    'valid': False,
                    'provider': 'twilio',
                    'error': f'API request failed: {response.status_code}'
                }
                
        except Exception as e:
            return {
                'phone': phone,
                'valid': False,
                'provider': 'twilio',
                'error': str(e)
            }

class LocalPhoneVerifier(PhoneVerifier):
    """Local phone verification using phonenumbers library"""
    
    def verify_phone(self, phone: str, country_code: str = None) -> Dict[str, any]:
        """Verify phone number using local phonenumbers library"""
        try:
            # Parse the phone number
            if country_code:
                parsed = phonenumbers.parse(phone, country_code)
            else:
                parsed = phonenumbers.parse(phone, None)
            
            # Check if valid
            is_valid = phonenumbers.is_valid_number(parsed)
            
            if is_valid:
                # Get additional information
                carrier_name = carrier.name_for_number(parsed, "en")
                location = geocoder.description_for_number(parsed, "en")
                
                return {
                    'phone': phone,
                    'valid': True,
                    'formatted': phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL),
                    'local_format': phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.NATIONAL),
                    'country_code': f"+{parsed.country_code}",
                    'location': location,
                    'carrier': carrier_name,
                    'provider': 'local'
                }
            else:
                return {
                    'phone': phone,
                    'valid': False,
                    'provider': 'local',
                    'error': 'Invalid phone number format'
                }
                
        except phonenumbers.NumberParseException as e:
            return {
                'phone': phone,
                'valid': False,
                'provider': 'local',
                'error': f'Parse error: {str(e)}'
            }
        except Exception as e:
            return {
                'phone': phone,
                'valid': False,
                'provider': 'local',
                'error': str(e)
            }

class PhoneVerificationService:
    """Main service for phone verification with fallback support"""
    
    def __init__(self, config):
        self.config = config
        self.verifiers = []
        
        # Always include local verifier as fallback
        self.verifiers.append(LocalPhoneVerifier())
        
        # Add API-based verifiers if configured
        if config.get_api_key('numverify'):
            self.verifiers.append(NumverifyVerifier(config.get_api_key('numverify')))
        
        if config.get_api_key('twilio_account_sid') and config.get_api_key('twilio_auth_token'):
            self.verifiers.append(TwilioVerifier(
                config.get_api_key('twilio_account_sid'),
                config.get_api_key('twilio_auth_token')
            ))
    
    def verify_phone(self, phone: str, country_code: str = None) -> Dict[str, any]:
        """Verify a phone number using available verifiers"""
        # Try each verifier
        for verifier in self.verifiers:
            result = verifier.verify_phone(phone, country_code)
            if result.get('valid') or verifier == self.verifiers[-1]:
                return result
        
        # Should not reach here, but just in case
        return {
            'phone': phone,
            'valid': False,
            'error': 'No verification service available'
        }
    
    def verify_all_phones(self, contact) -> None:
        """Verify all phone numbers for a contact"""
        if not self.config.get_setting('verify_phones'):
            return
        
        # Verify primary phone
        if contact.primary_phone:
            result = self.verify_phone(contact.primary_phone)
            contact.verification_status['primary_phone'] = 'valid' if result.get('valid') else 'invalid'
            
            # Update with formatted version if available
            if result.get('valid') and result.get('formatted'):
                contact.primary_phone = result['formatted']
        
        # Verify alternate phones
        verified_alternates = []
        for phone in contact.alternate_phones:
            result = self.verify_phone(phone)
            if result.get('valid'):
                # Use formatted version if available
                verified_alternates.append(result.get('formatted', phone))
        
        contact.alternate_phones = verified_alternates