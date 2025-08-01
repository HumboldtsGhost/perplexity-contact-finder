# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Perplexity Contact Finder is a Python CLI tool that discovers contact information using Perplexity AI and enriches it through verification layers. It features an interactive mode with templates for government, business, nonprofit, and education sectors.

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

# Install new dependency for Excel export if needed
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

2. **Service Abstraction**: Both email and phone verifiers use abstract base classes with multiple provider implementations. New providers can be added by inheriting from the base class.

3. **Configuration Cascade**: Config values are resolved in order: environment variables → config.json → defaults. This is handled by `config.py`.

4. **Template System**: Search templates in `perplexity_contact_finder.py` use a dictionary structure with fields, examples, and multi_result flags. Templates generate multiple search queries from user input.

### Module Interactions

- **perplexity_contact_finder.py**: Orchestrates all operations, manages state persistence, and provides both CLI and interactive interfaces. The `ContactFinder` class coordinates between services.

- **perplexity_client.py**: Formats prompts to get structured JSON responses from Perplexity AI. Falls back to regex parsing if JSON fails. Returns `ContactInfo` objects.

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

### Source Citations
Sources are preserved throughout the pipeline as a list of dictionaries with 'url', 'title', and optional 'relevance' fields. This is critical for users to verify information.

### Bulk Search Focus
Templates are designed to find multiple contacts per query (e.g., "all California senators" rather than individual names). The `multi_result: True` flag in templates indicates this capability.

## Testing and Debugging

While there's no formal test suite, use these approaches:
- Run `quickstart.py` for minimal Perplexity-only testing
- Use `--perplexity-only` flag to skip verification during development
- Check `contact_finder.log` for detailed execution logs
- Use interactive mode's help system (`--help-me`) for troubleshooting

## Git Workflow

The repository uses SSH for secure access:
- Remote: HumboldtsGhost/perplexity-contact-finder
- Push with: `git push origin main`