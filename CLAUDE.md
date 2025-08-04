# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Perplexity Contact Finder is a Python CLI tool that discovers specific business owner and decision-maker contact information using Perplexity AI. The tool returns multiple contacts per search query, preserves source citations, and enriches data through optional verification layers. It features an interactive mode with templates for various business types, government offices, and nonprofit organizations.

## Common Development Commands

### Running the Application

```bash
# Interactive mode (recommended for development)
python perplexity_contact_finder.py --interactive

# Command line mode
python perplexity_contact_finder.py "query" --perplexity-only

# Batch processing
python perplexity_contact_finder.py -f queries.txt

# Resume interrupted search
python perplexity_contact_finder.py -f queries.txt --resume

# Help mode
python perplexity_contact_finder.py --help-me
```

### Development Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Excel export dependency (included in requirements.txt)
pip install openpyxl
```

### Configuration

```bash
# Copy sample config
cp config.sample.json config.json

# Set environment variable (takes precedence over config.json)
export PERPLEXITY_API_KEY='your-key-here'
```

## Architecture and Key Relationships

### Core Data Flow
The application follows a pipeline architecture:
```
User Input → perplexity_contact_finder.py → perplexity_client.py → ContactInfo
                                                ↓
                                         verification services
                                    (email_verifier.py, phone_verifier.py)
                                                ↓
                                         data_exporter.py → Multiple formats
```

### Key Architectural Patterns

1. **ContactInfo Dataclass**: Central data structure defined in `perplexity_client.py`. All modules work with this standardized format.

2. **Multiple Contact Returns**: The `search_contact` method now returns `List[ContactInfo]` instead of a single contact. The `_parse_response_multiple` method handles JSON arrays of contacts from Perplexity.

3. **Service Abstraction**: Both email and phone verifiers use abstract base classes with multiple provider implementations. New providers can be added by inheriting from the base class.

4. **Configuration Cascade**: Config values are resolved in order: environment variables → config.json → defaults. This is handled by `config.py`.

5. **Template System**: Search templates in `perplexity_contact_finder.py` use a dictionary structure with fields, examples, and multi_result flags. Templates generate multiple search queries from user input.

6. **Smart Query Splitting**: When users enter comma-separated values for service types (e.g., "roofing, plumbing, HVAC"), the system automatically creates separate search queries for each type.

### Module Interactions

- **perplexity_contact_finder.py**: Orchestrates all operations, manages state persistence, and provides both CLI and interactive interfaces. The `ContactFinder` class coordinates between services.

- **perplexity_client.py**: Formats prompts to get structured JSON responses from Perplexity AI. The prompts specifically request actual business names with owner/decision-maker contacts. Returns a list of `ContactInfo` objects. Falls back to regex parsing if JSON fails.

- **Verification Services**: Optional enrichment layer. Services check if API keys exist before initializing. Each service can verify primary and alternate contact methods.

- **data_exporter.py**: Handles all export formats. The Excel export requires openpyxl. Each format method returns the filepath for display.

### State Management

The application saves state to `contact_finder_state.json` after each successful query. This enables resume functionality for batch operations. State includes processed queries and accumulated results.

### Interactive Mode Features

The interactive mode uses:
- `rich` for tables, progress bars, and styled output
- `questionary` for menu selections
- `pyfiglet` for ASCII art
- Search templates that generate multiple queries from minimal input

## Important Implementation Details

### API Integration
- Perplexity API uses OpenAI-compatible endpoints via the `openai` library
- All verification services handle missing API keys gracefully
- Rate limiting is implemented with configurable delays

### Error Handling
- The Perplexity client retries failed requests with exponential backoff
- Verification failures don't stop the pipeline - unverified data is still returned
- JSON parsing failures fall back to regex extraction

### Enhanced Perplexity Prompts
The system prompt in `perplexity_client.py` specifically instructs Perplexity to:
- Find SPECIFIC BUSINESS NAMES (not generic industry descriptions)
- Include owner or key decision-maker names with titles
- Return multiple distinct businesses (5-10) per search
- Search business directories, BBB listings, and company websites
- Focus on "About Us" or "Our Team" pages for owner information

### Source Citations
Sources are preserved throughout the pipeline as a list of dictionaries with 'url', 'title', and optional 'relevance' fields. This is critical for users to verify information.

### Bulk Search Focus
Templates are designed to find multiple specific businesses per query. For example:
- "roofing companies in Austin Texas owner contact information" returns 5-10 actual roofing businesses
- "restaurant owners downtown Chicago contact list" finds specific restaurant names with owner details
The `multi_result: True` flag in templates indicates this capability.

## Testing and Debugging

While there's no formal test suite, use these approaches:
- Run `quickstart.py` for minimal Perplexity-only testing
- Use `--perplexity-only` flag to skip verification during development
- Check `contact_finder.log` for detailed execution logs
- Use interactive mode's help system (`--help-me`) for troubleshooting

### Export Formats

The `data_exporter.py` module supports multiple export formats:
- **CSV**: Standard format with all contact fields
- **Apollo CSV**: Compatible with Apollo.io import format
- **Excel**: Multi-worksheet format (requires `openpyxl`)
- **JSON**: Complete data with raw responses and metadata
- **Text**: Human-readable format with sources

## Git Workflow

The repository uses SSH for secure access:
- Remote: HumboldtsGhost/perplexity-contact-finder
- Push with: `git push origin main`
- Git config is set to use HumboldtsGhost as author (not personal identity)
- SSH key for HumboldtsGhost is configured separately in `~/.ssh/config`