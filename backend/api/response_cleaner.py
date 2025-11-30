"""
Response post-processor to ensure clean, user-friendly outputs
"""
import re
import json


class ResponseCleaner:
    """Clean and enhance chatbot responses before sending to users"""
    
    def __init__(self):
        self.ala_base = "https://biocache.ala.org.au/occurrences/search?q=*:*"
    
    def clean_response(self, message: str, function_results: list = None) -> str:
        """
        Clean a chatbot response by:
        1. Removing raw JSON
        2. Removing function call leakage
        3. Fixing malformed URLs
        4. Converting markdown images to "See image:" format
        5. Ensuring natural language
        """
        original = message
        
        # Step 1: Remove raw JSON blocks
        message = self._remove_json_blocks(message)
        
        # Step 2: Remove function call leakage
        message = self._remove_function_leakage(message)
        
        # Step 3: Fix URLs using function results - CRITICAL STEP
        if function_results:
            message = self._fix_urls(message, function_results)
        
        # Step 4: Convert markdown image syntax to "See image:" format
        message = self._convert_image_syntax(message)
        
        # Step 5: Remove empty lines and clean up
        message = self._cleanup_formatting(message)
        
        # If we removed too much, check what the original query might have been about
        if len(message.strip()) < 20:
            # Check if there's any remaining useful content
            if 'couldn\'t find' in original.lower() or 'no records' in original.lower() or '0 records' in original.lower():
                # User query returned no results - preserve that information
                if 'couldn\'t find' in original:
                    match = re.search(r'couldn\'t find[^\.]+\.', original, re.IGNORECASE)
                    if match:
                        return match.group(0)
                return "I couldn't find any matching records in the Australian Museum collection for that query."
            
            return "I encountered an issue processing that query. Could you rephrase your question?"
        
        # Log if we made significant changes
        if len(message) < len(original) * 0.7:
            print(f"[ResponseCleaner] Significantly cleaned response (removed {len(original) - len(message)} chars)")
        
        return message
    
    def _remove_json_blocks(self, text: str) -> str:
        """Remove raw JSON that leaked into responses"""
        # Remove JSON objects (anything that looks like {"key":"value"...})
        text = re.sub(r'\{["\'][a-zA-Z_]+["\']:[^\}]{10,}\}', '', text)
        
        # Remove JSON arrays
        text = re.sub(r'\[\{[^\]]{20,}\}\]', '', text)
        
        # Remove standalone curly braces
        text = re.sub(r'\{[^\}]{5,}\}', '', text)
        
        return text
    
    def _remove_function_leakage(self, text: str) -> str:
        """Remove function call leakage and search process descriptions - AGGRESSIVE"""
        
        # Remove entire sentences that describe the search process
        
        # "I'll [action]..." sentences (all variations)
        text = re.sub(r'I\'ll\s+(search|check|query|look|get|retrieve|find|call|fetch|access|contact|pull|grab)[^\n\.]+[\.\n]?', '', text, flags=re.IGNORECASE)
        
        # "I'm [action]..." sentences (all variations)
        text = re.sub(r'I\'m\s+(searching|checking|querying|looking|getting|retrieving|finding|calling|fetching|accessing|contacting|pulling|grabbing)[^\n\.]+[\.\n]?', '', text, flags=re.IGNORECASE)
        
        # "Let me [action]..." sentences
        text = re.sub(r'Let\s+me\s+(search|check|query|look|get|retrieve|find|call|fetch|access)[^\n\.]+[\.\n]?', '', text, flags=re.IGNORECASE)
        
        # "[Action]ing..." sentences (Searching, Querying, Calling, etc.)
        text = re.sub(r'(Searching|Querying|Checking|Looking|Getting|Retrieving|Finding|Calling|Fetching|Accessing|Contacting|Attempting|Proceeding)[^\n]*[\.\n]', '', text, flags=re.IGNORECASE)
        
        # "Done/Finished..." sentences
        text = re.sub(r'(Done|Finished)[^\n]*[\.\n]', '', text, flags=re.IGNORECASE)
        
        # Conditional process statements: "If I can [action]..."
        text = re.sub(r'If\s+I\s+can\s+(retrieve|get|find|access|fetch|pull)[^\n\.]+[\.\n]?', '', text, flags=re.IGNORECASE)
        
        # Notes in parentheses
        text = re.sub(r'\(Note:.*?\)[\.\n]?', '', text, flags=re.IGNORECASE | re.DOTALL)
        
        # "Calling function..." sentences
        text = re.sub(r'Calling\s+(function|the\s+function|the\s+[A-Z][a-z]+\s+[A-Z][a-z]+)[^\n\.]+[\.\n]?', '', text, flags=re.IGNORECASE)
        
        # Specific pattern: "Calling the Australian Museum collection..."
        text = re.sub(r'Calling\s+the\s+Australian\s+Museum[^\n\.]+[\.\n]?', '', text, flags=re.IGNORECASE)
        
        # Simulation notices
        text = re.sub(r'\(this\s+is\s+simulated\)[\.\n]?', '', text, flags=re.IGNORECASE)
        
        # Function call patterns like: _call_function_
        text = re.sub(r'_call_[a-z_]+_', '', text)
        
        # Pattern: (to=functions.name ...)
        text = re.sub(r'\(to=functions\.[a-z_]+[^\)]*\)', '', text)
        
        # Multi-line search descriptions
        text = re.sub(r'I\'ll[^\.]+\.+\s*Searching[^\n]*\n?', '', text, flags=re.IGNORECASE)
        
        # Remove "in case" conditional statements that describe process
        text = re.sub(r'in\s+case\s+records?\s+(are|is)[^\n\.]+[\.\n]?', '', text, flags=re.IGNORECASE)
        
        # Remove phrases about retrieving/showing links
        text = re.sub(r'(I\'ll\s+share\s+the\s+link|to\s+retrieve\s+the[^\n\.]+link)[^\n\.]*[\.\n]?', '', text, flags=re.IGNORECASE)
        
        return text
    
    def _fix_urls(self, text: str, function_results: list) -> str:
        """Fix malformed ALA URLs by replacing with correct ones from function results"""
        print(f"[ResponseCleaner] _fix_urls called")
        print(f"[ResponseCleaner] Input text length: {len(text)}")
        print(f"[ResponseCleaner] Input text preview: {text[:200]}...")
        
        # Extract the correct URL from the last function result
        correct_url = None
        
        for result in reversed(function_results):
            try:
                if result.get('role') == 'tool' and result.get('content'):
                    data = json.loads(result['content'])
                    if 'ala_url' in data:
                        correct_url = data['ala_url']
                        print(f"[ResponseCleaner] Found correct_url: {correct_url}")
                        print(f"[ResponseCleaner] Bracket count in correct_url: {correct_url.count(']')}")
                        break
            except Exception as e:
                print(f"[ResponseCleaner] Error parsing result: {e}")
                continue
        
        if correct_url:
            # IMPROVED REGEX: Match ALA URLs more precisely
            # Stop at: period+space (end of sentence), newline, or closing paren not in URL
            # Allow: spaces, brackets, and other URL characters
            # This pattern will match until it hits ". " (period-space), "\n", or ")" at sentence end
            ala_pattern = r'https://biocache\.ala\.org\.au/occurrences/search[^\n]*?(?=\s+[a-z]|\.\s|\.?$|\n|$)'
            
            # Find all ALA URLs in the text
            matches = re.findall(ala_pattern, text)
            print(f"[ResponseCleaner] Found {len(matches)} URL(s) to replace")
            
            if matches:
                for i, match in enumerate(matches):
                    print(f"[ResponseCleaner] Match {i+1}: {match}")
                    print(f"[ResponseCleaner] Match {i+1} bracket count: {match.count(']')}")
                    print(f"[ResponseCleaner] Match {i+1} last 30 chars: ...{match[-30:]}")
                
                # Replace ALL ALA URLs with the correct one from backend
                text_before = text
                text = re.sub(ala_pattern, correct_url, text)
                
                print(f"[ResponseCleaner] ✓ Replaced {len(matches)} URL(s)")
                print(f"[ResponseCleaner] Text changed: {text != text_before}")
                
                # Check the result
                matches_after = re.findall(ala_pattern, text)
                if matches_after:
                    print(f"[ResponseCleaner] After replacement, found {len(matches_after)} URL(s)")
                    for i, match in enumerate(matches_after):
                        print(f"[ResponseCleaner] After match {i+1} bracket count: {match.count(']')}")
        else:
            # Debug: Check if there are URLs but no correct URL from backend
            ala_pattern = r'https://biocache\.ala\.org\.au/occurrences/search[^\n]*?(?=\s+[a-z]|\.\s|\.?$|\n|$)'
            matches = re.findall(ala_pattern, text)
            if matches:
                print(f"[ResponseCleaner] ⚠ WARNING: Found {len(matches)} ALA URL(s) but NO correct URL from backend!")
                print(f"[ResponseCleaner]   This means the backend didn't return ala_url in function results")
                print(f"[ResponseCleaner]   URL found: {matches[0][:80]}...")
        
        print(f"[ResponseCleaner] Output text preview: {text[:200]}...")
        return text
    
    def _convert_image_syntax(self, text: str) -> str:
        """Convert markdown image syntax ![alt text](url) to 'See image: url' format"""
        # Pattern matches ![any alt text](url)
        # Captures the URL inside the parentheses
        pattern = r'!\[[^\]]*\]\((https?://[^\)]+)\)'
        replacement = r'See image: \1'
        return re.sub(pattern, replacement, text)
    
    def _cleanup_formatting(self, text: str) -> str:
        """Clean up formatting issues"""
        # Remove orphaned JSON characters
        text = re.sub(r'^\s*[\{\}]\s*$', '', text, flags=re.MULTILINE)
        text = re.sub(r'^\s*\}\s*\n', '', text, flags=re.MULTILINE)
        
        # Remove multiple newlines
        text = re.sub(r'\n\n+', '\n\n', text)
        
        # Remove leading/trailing whitespace from each line
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(lines)
        
        # Remove empty lines at start and end
        text = text.strip()
        
        return text