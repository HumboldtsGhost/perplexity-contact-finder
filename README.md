# Perplexity Contact Finder

[![GitHub](https://img.shields.io/github/license/HumboldtsGhost/perplexity-contact-finder)](https://github.com/HumboldtsGhost/perplexity-contact-finder/blob/main/LICENSE)
[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

A powerful Python tool that uses Perplexity AI to find contact information and enriches it through verification layers. The tool preserves source citations and captures alternate contact information.

## 🚀 Super Quick Start (For Everyone!)

### Mac/Linux Users:
```bash
# 1. Open Terminal and navigate to this folder
# 2. Run setup (only needed once):
./setup.sh

# 3. Run the tool:
./run.sh
```

### Windows Users:
```
1. Double-click setup.bat (only needed once)
2. Double-click run.bat
```

That's it! The tool will guide you through everything else. 🎉

---

> **Note**: This tool was inspired by a use case where Perplexity API outperformed traditional enrichment services like Apollo in finding accurate contact information with proper source citations.

## Features

- 🎯 **Interactive Mode**: User-friendly interface with templates and wizards
- 🏛️ **Bulk Government Search**: Find entire teams - senators, city councils, agency directors
- 💼 **Company-Wide Search**: Get all executives, board members, or department heads at once
- 🏭 **Industry-Wide Search**: Find leaders across entire industries or regions
- 🔍 **Contact Discovery**: Uses Perplexity AI to find contact information
- ✅ **Email Verification**: Supports Hunter.io and ZeroBounce APIs
- 📞 **Phone Verification**: Supports Numverify and Twilio APIs
- 📚 **Source Citations**: Preserves all sources where information was found
- 🔄 **Alternate Contacts**: Captures all email and phone variations
- 💾 **Multiple Export Formats**: CSV, Apollo-compatible CSV, and JSON
- ⏸️ **Resume Capability**: Can pause and resume long-running searches
- 🔧 **Flexible Configuration**: Use default API keys or provide your own
- 🆘 **Built-in Help**: Interactive help system for troubleshooting
- 🎨 **Progress Animations**: Visual feedback during searches

## Installation

1. Clone or download this repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Quick Start

The simplest way to use this tool is to run it in interactive mode:

```bash
# First time setup (creates virtual environment and installs dependencies)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run in interactive mode (recommended for first-time users)
python3 perplexity_contact_finder.py --interactive
```

This will:
- Guide you through API key setup with a friendly wizard
- Show search templates for government and business contacts
- Display progress with animations
- Provide helpful examples and tips

### Quick command-line usage:
```bash
# Set your API key
export PERPLEXITY_API_KEY='your-key-here'

# Run a single search
python3 perplexity_contact_finder.py "John Doe CEO Company" --perplexity-only
```

### Need help?
```bash
# Get interactive help for common issues
python3 perplexity_contact_finder.py --help-me
```

## Configuration

### API Keys Required

You'll need at least a Perplexity API key to use this tool. Additional API keys for email/phone verification are optional but recommended.

- **Perplexity API** (REQUIRED): Get your key at [https://www.perplexity.ai/settings/api](https://www.perplexity.ai/settings/api)
- **Hunter.io** (optional): For email verification - [https://hunter.io/api](https://hunter.io/api)
- **ZeroBounce** (optional): For email verification - [https://www.zerobounce.net](https://www.zerobounce.net)
- **Numverify** (optional): For phone verification - [https://numverify.com](https://numverify.com)
- **Twilio** (optional): For phone verification - [https://www.twilio.com](https://www.twilio.com)

### Setting Up Your API Keys

1. Create a configuration file:
```bash
python perplexity_contact_finder.py --setup
```

2. Copy the sample configuration:
```bash
cp config.sample.json config.json
```

3. Edit `config.json` and add your API keys:
```json
{
  "api_keys": {
    "perplexity": "your-perplexity-api-key",
    "hunter": "your-hunter-api-key",
    "zerobounce": "your-zerobounce-api-key",
    "numverify": "your-numverify-api-key",
    "twilio_account_sid": "your-twilio-sid",
    "twilio_auth_token": "your-twilio-token"
  },
  "settings": {
    "batch_size": 10,
    "rate_limit_delay": 1.0,
    "verify_emails": true,
    "verify_phones": true
  }
}
```

### Environment Variables
You can also set API keys using environment variables:
- `PERPLEXITY_API_KEY`
- `HUNTER_API_KEY`
- `ZEROBOUNCE_API_KEY`
- `NUMVERIFY_API_KEY`
- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`

## Usage

### Basic Usage
Search for a single contact:
```bash
python perplexity_contact_finder.py "John Smith CEO at Microsoft"
```

Search for multiple contacts:
```bash
python perplexity_contact_finder.py "Jane Doe CTO Google" "Bob Wilson CFO Apple" "Alice Brown CMO Meta"
```

### Using a File
Create a file `queries.txt` with one query per line:
```
John Smith CEO Microsoft
Jane Doe CTO Google
Bob Wilson CFO Apple
```

Run the search:
```bash
python perplexity_contact_finder.py -f queries.txt
```

### Resume a Previous Run
If the script was interrupted:
```bash
python perplexity_contact_finder.py -f queries.txt --resume
```

### Skip Verification / Perplexity Only Mode
To use only Perplexity without verification services:
```bash
# Option 1: Use --perplexity-only flag
python perplexity_contact_finder.py -f queries.txt --perplexity-only

# Option 2: Use --no-verify flag  
python perplexity_contact_finder.py -f queries.txt --no-verify
```

### Output Formats
Choose output format:
```bash
# CSV only
python perplexity_contact_finder.py -f queries.txt -o csv

# JSON only  
python perplexity_contact_finder.py -f queries.txt -o json

# Both (default)
python perplexity_contact_finder.py -f queries.txt -o both
```

## Output Files

The tool creates an `output` directory with:

1. **Standard CSV** (`contacts_TIMESTAMP.csv`):
   - All contact information with sources
   - Alternate emails and phones included
   - Verification status

2. **Apollo CSV** (`apollo_contacts_TIMESTAMP.csv`):
   - Format compatible with Apollo.io import
   - Separate rows for alternate emails

3. **JSON** (`contacts_TIMESTAMP.json`):
   - Complete data including raw responses
   - Full source citations
   - All metadata

## API Services

### Email Verification
- **Hunter.io**: Professional email verification with detailed checks
- **ZeroBounce**: AI-powered email scoring and validation

### Phone Verification
- **Numverify**: Global phone number validation
- **Twilio**: Carrier and caller ID lookup
- **Local**: Fallback using phonenumbers library

## Tips for Best Results

1. **Bulk Searches**: Design queries to find multiple contacts at once
   - Good: "California state senators contact list"
   - Better: "all California state senators email addresses and phone numbers"
   - Best: "current California state senators contact information including emails"

2. **Role-Based Searches**: Focus on positions rather than names
   - "Microsoft executive team contacts"
   - "Austin city council members emails"
   - "Fortune 500 healthcare CEOs contact list"

3. **Industry Searches**: Cast a wide net across industries
   - "renewable energy companies board members"
   - "Bay Area startup founders contact information"
   - "top pharmaceutical companies executives"

4. **Government Searches**: Be specific about jurisdiction
   - "Texas state government cabinet members"
   - "New York City department commissioners"
   - "EPA regional directors contact list"

5. **Rate Limits**: The tool respects API rate limits automatically

6. **Verification**: Email/phone verification improves data quality but takes longer

7. **Sources**: Always check the sources to verify information accuracy

## Troubleshooting

### No results found
- Try more specific queries
- Include company name and title
- Check if Perplexity can access the information

### Verification failing
- Check API keys are valid
- Ensure you have credits/quota remaining
- Some emails/phones may be unverifiable

### Script interrupted
- Use `--resume` to continue from where you left off
- Progress is automatically saved after each query

## Example Bulk Search Results

When searching for "California state senators contact list", the tool might return:

```
Found 40 contacts:

1. Name: Senator Jane Smith
   District: 1
   Email: senator.smith@senate.ca.gov
   Phone: +1-916-555-0001
   Sources: California Senate Website, Official Directory

2. Name: Senator Robert Johnson
   District: 2
   Email: senator.johnson@senate.ca.gov
   Phone: +1-916-555-0002
   Sources: Senate.ca.gov, District Office Page

... (and 38 more contacts)
```

The tool automatically:
- Finds all relevant contacts matching your search
- Extracts emails, phones, and other details
- Provides source citations for verification
- Exports to CSV/JSON for easy use

## Performance

- **Processing Time**: ~100-200 contacts in 30 minutes (with verification)
- **Without Verification**: 3-4x faster using `--no-verify` flag
- **Rate Limiting**: Automatically handled to respect API limits
- **Resume Capability**: Can handle interruptions and resume processing

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

This tool is for legitimate business purposes only. Users are responsible for complying with all applicable laws and regulations regarding data collection and privacy.