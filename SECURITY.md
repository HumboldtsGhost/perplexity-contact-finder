# Security Notice

## API Key Management

**IMPORTANT**: Never commit API keys or tokens to version control!

### Safe Storage Options:

1. **Environment Variables** (Recommended)
   ```bash
   export PERPLEXITY_API_KEY='your-key-here'
   export HUNTER_API_KEY='your-key-here'
   ```

2. **Local config.json** (Git-ignored)
   - Copy `config.sample.json` to `config.json`
   - Add your keys to `config.json`
   - This file is in `.gitignore` and won't be committed

3. **`.env` file** (Git-ignored)
   - Create a `.env` file in the project root
   - Add keys like:
     ```
     PERPLEXITY_API_KEY=your-key-here
     HUNTER_API_KEY=your-key-here
     ```

### What NOT to do:
- Never hardcode API keys in source files
- Never commit `config.json` with real keys
- Never share API keys in issues or pull requests
- Never commit GitHub Personal Access Tokens

### If you accidentally commit an API key:
1. Immediately revoke the key on the service's website
2. Generate a new key
3. Remove the commit from history (if possible)
4. Force push to update the remote repository

### Files that are Git-ignored:
- `config.json` - Your personal configuration
- `*.token` - Any token files
- `.env*` - Environment files
- `api_keys.txt` - Any plain text key storage
- `credentials.json` - Credential files
- `output/` - Generated contact data

Always verify with `git status` before committing!