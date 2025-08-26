#!/usr/bin/env python3
"""
Fixes for web_app.py:
1. Add Title column to tables
2. Save all results to database automatically
3. Remove "View Results So Far" button and show results immediately
4. Implement query bundling (5-10 queries at once to Perplexity)
"""

# This file contains the fixes that need to be applied to web_app.py

FIXES = """
1. Database schema fix - Add title column:
-------------------------------------------
Change the CREATE TABLE for contacts to include title:
    title TEXT,

2. Save results automatically:
-------------------------------
After each successful Perplexity search, save to database:
    # Save to database
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO contacts 
                 (id, name, title, company, email, phone, confidence, imported_at)
                 VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))''',
              (contact_id, name, title, company, email, phone, confidence))
    conn.commit()
    conn.close()

3. Remove "View Results So Far" button:
----------------------------------------
Remove the button HTML and showLiveResults function.
Instead, automatically display results as they come in.

4. Add Title column to results display:
----------------------------------------
In the HTML table headers, add:
    <th>Title</th>
    
In the results display, add:
    <td>${contact.title || 'N/A'}</td>

5. Bundle queries for Perplexity:
----------------------------------
Instead of sending one query at a time, bundle 5-10:

def execute_bundled_search(queries_batch):
    # Combine multiple queries into one Perplexity call
    combined_prompt = "Find contact information for the following:\\n"
    for q in queries_batch[:10]:  # Max 10 queries per call
        combined_prompt += f"- {q['query']}\\n"
    
    # Single Perplexity call for multiple queries
    response = perplexity_client.search_contact(combined_prompt)
    
    # Parse and return multiple results
    return parse_multiple_results(response)
"""

print("Fixes documented. These need to be applied to web_app.py")