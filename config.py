"""
Configuration management for Perplexity Contact Finder
Handles API keys with defaults and user overrides
"""
import os
import json
from pathlib import Path
from typing import Dict, Optional

class Config:
    """Manages API keys and configuration settings"""
    
    # Default API keys (can be overridden)
    DEFAULT_KEYS = {
        'perplexity': None,
        'hunter': None,
        'zerobounce': None,
        'numverify': None,
        'twilio_account_sid': None,
        'twilio_auth_token': None,
    }
    
    # Default settings
    DEFAULT_SETTINGS = {
        'batch_size': 10,
        'rate_limit_delay': 1.0,  # seconds between API calls
        'max_retries': 3,
        'timeout': 30,
        'verify_emails': True,
        'verify_phones': True,
        'output_format': 'both',  # 'csv', 'json', or 'both'
        'include_alternates': True,
        'include_sources': True,
    }
    
    def __init__(self, config_file: str = 'config.json'):
        """Initialize configuration with optional config file"""
        self.config_file = Path(config_file)
        self.api_keys = self.DEFAULT_KEYS.copy()
        self.settings = self.DEFAULT_SETTINGS.copy()
        
        # Load from environment variables
        self._load_from_env()
        
        # Load from config file if exists
        if self.config_file.exists():
            self._load_from_file()
    
    def _load_from_env(self):
        """Load API keys from environment variables"""
        env_mapping = {
            'PERPLEXITY_API_KEY': 'perplexity',
            'HUNTER_API_KEY': 'hunter',
            'ZEROBOUNCE_API_KEY': 'zerobounce',
            'NUMVERIFY_API_KEY': 'numverify',
            'TWILIO_ACCOUNT_SID': 'twilio_account_sid',
            'TWILIO_AUTH_TOKEN': 'twilio_auth_token',
        }
        
        for env_var, key_name in env_mapping.items():
            value = os.getenv(env_var)
            if value:
                self.api_keys[key_name] = value
    
    def _load_from_file(self):
        """Load configuration from JSON file"""
        try:
            with open(self.config_file, 'r') as f:
                data = json.load(f)
                
            # Update API keys
            if 'api_keys' in data:
                for key, value in data['api_keys'].items():
                    if value:  # Only update if value is provided
                        self.api_keys[key] = value
            
            # Update settings
            if 'settings' in data:
                self.settings.update(data['settings'])
                
        except Exception as e:
            print(f"Warning: Could not load config file: {e}")
    
    def save_to_file(self):
        """Save current configuration to file"""
        data = {
            'api_keys': self.api_keys,
            'settings': self.settings
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def create_sample_config(self):
        """Create a sample configuration file"""
        sample_data = {
            'api_keys': {
                'perplexity': 'your-perplexity-api-key-here',
                'hunter': 'your-hunter-api-key-here',
                'zerobounce': 'your-zerobounce-api-key-here',
                'numverify': 'your-numverify-api-key-here',
                'twilio_account_sid': 'your-twilio-account-sid-here',
                'twilio_auth_token': 'your-twilio-auth-token-here'
            },
            'settings': self.DEFAULT_SETTINGS
        }
        
        with open('config.sample.json', 'w') as f:
            json.dump(sample_data, f, indent=2)
            
        print("Created config.sample.json - Copy to config.json and add your API keys")
    
    def get_api_key(self, service: str) -> Optional[str]:
        """Get API key for a specific service"""
        return self.api_keys.get(service)
    
    def set_api_key(self, service: str, key: str):
        """Set API key for a specific service"""
        self.api_keys[service] = key
    
    def get_setting(self, setting: str):
        """Get a specific setting value"""
        return self.settings.get(setting)
    
    def set_setting(self, setting: str, value):
        """Set a specific setting value"""
        self.settings[setting] = value
    
    def validate_keys(self) -> Dict[str, bool]:
        """Check which API keys are configured"""
        return {
            service: bool(key) for service, key in self.api_keys.items()
        }
    
    def display_config(self):
        """Display current configuration (hiding sensitive keys)"""
        print("Current Configuration:")
        print("\nAPI Keys:")
        for service, key in self.api_keys.items():
            if key:
                masked_key = key[:4] + '...' + key[-4:] if len(key) > 8 else '****'
                print(f"  {service}: {masked_key}")
            else:
                print(f"  {service}: Not configured")
        
        print("\nSettings:")
        for setting, value in self.settings.items():
            print(f"  {setting}: {value}")


if __name__ == "__main__":
    # Example usage
    config = Config()
    
    # Create sample config file
    config.create_sample_config()
    
    # Display current configuration
    config.display_config()