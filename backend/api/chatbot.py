"""
Enhanced chatbot service with comprehensive OpenAI tools API for ALA Biocache integration
Implements fallback logic: vernacular name → scientific name (and vice versa)
ENHANCED: Now includes geocoding support for suburb-level queries
FIXED: Generic animal terms now dynamically resolve to taxonomic searches via ALA BIE
FIXED: Search order - taxonomy resolution happens FIRST for generic terms
FIXED: ALA BIE query format - removed problematic kingdom filter
"""
import base64
from typing import Dict, List, Optional, Tuple
import json
import re
import sys
from openai import OpenAI
from config import Config
from api.biocache import BiocacheService
from api.response_cleaner import ResponseCleaner
from api.geocoding import GeocodingService


class ChatbotService:
    def __init__(self):
        """Initialize the chatbot with OpenAI client and comprehensive tool definitions"""
        self.client = OpenAI(api_key=Config.OPENAI_API_KEY)
        self.biocache_service = BiocacheService()
        self.response_cleaner = ResponseCleaner()
        self.geocoding_service = GeocodingService()
        
        self.model = "gpt-5-nano"
        self.conversations = {}
        self.max_history_length = 20
        
        # System prompt
        self.system_prompt = """You are an AI assistant for the Australian Museum Collection Explorer (OZCAM dataset via ALA Biocache API).

## Your Job

1. Understand what the user wants to know about museum specimens.
2. Call the appropriate function to get the data.
3. Provide a clear, natural language answer.
4. When users ask casually about an animal (e.g., "frogs", "christmas beetles"), provide general facts about the animal or connect to 1-2 relevant species in the museum collection, based on the user's intent.
5. When users ask questions unrelated to life science or the museum collection, answer briefly (1-2 sentences) and politely indicate you're specialised in life-science specimen collections from the Australian Museum.

## Available Functions

- **search_specimens**: Search for specimen records with various filters (taxonomy, location, dates, collectors, etc.). Supports partial matching for common names and can handle generic animal categories (e.g., "bird", "fish", "insect").
- **get_specimen_statistics**: Get counts and distributions across different categories.
- **get_specimen_by_id**: Look up a specific specimen record by catalog number.

## CRITICAL RULE: Taxonomic Names

When calling search_specimens or get_specimen_statistics:
- Use EITHER scientific_name OR common_name - NEVER BOTH in the same function call.
- If the user provides a common name (like "rainbow lorikeet"), use only common_name parameter.
- If the user provides a scientific name (like "Macropus rufus"), use only scientific_name parameter.
- The backend will automatically handle fallback if no results are found.

## Response Guidelines

- Be concise and helpful (2-3 sentences for simple queries, 3-5 sentences for detailed results).
- When discussing collection records, provide ACTUAL numbers from API data only and NEVER invent or estimate statistics.
- For casual animal questions, provide general facts first, then connect to collection data IF RELEVANT.
- ALWAYS include the ala_url after retrieving specimen search results, unless the search returned 0 records.
- If no results found, say so clearly and do not include ala_url, then provide some general facts about the species.
- Don't follow up with more questions or offer follow-up options to the user.
- When the user asks for images of a species, show up to five images.
- When discussing specific species or specimen records, show images from the API response when they're present (up to 5 images).
- Use British English spelling (e.g., "specialised", "colour", "catalogue").
- When users ask follow-up questions using pronouns (e.g., "these", "those"), recognise they're referring to the previous query's context and parameters.

## Example

**Example 1:**
User: "Show me kangaroo specimens from the 1980s"
You: Call search_specimens with common_name="kangaroo" (matches any species with "kangaroo" in the name), then respond naturally like:
"I found [X] kangaroo specimens in the collection from the 1980s, including [species names from results]. Most are from [states/locations from results]. [View results on Atlas of Living Australia](ala_url)"
(Note: All numbers, species names, and locations must come from the actual API response)

**Example 2:**
User: "What frogs do you have?"
You: Call search_specimens with common_name="frog" (matches any species with "frog" in the name), then:
- Identify 1-2 representative species from the results.
- For each species, provide: common name, scientific name, specimen count, and key locations.
- Check the returned results for image URLs (imageUrl, largeImageUrl, thumbnailUrl) and display them when present (up to 5 images total).
- Include the ala_url at the end.
- Remove any internal processing from your response.

"""

        # Comprehensive tool definitions
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "search_specimens",
                    "description": "Search the OZCAM specimen dataset via ALA Biocache API with comprehensive filtering options",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "scientific_name": {
                                "type": "string",
                                "description": "Scientific name at any taxonomic level (species, genus, family, order, class, phylum, kingdom)"
                            },
                            "common_name": {
                                "type": "string",
                                "description": "Common/vernacular name of the organism"
                            },
                            "state_province": {
                                "type": "string",
                                "description": "Australian state or territory (full names: 'New South Wales', 'Queensland', 'Victoria', 'Tasmania', 'South Australia', 'Western Australia', 'Northern Territory', 'Australian Capital Territory')"
                            },
                            "locality": {
                                "type": "string",
                                "description": "Specific location description"
                            },
                            "bounds": {
                                "type": "object",
                                "properties": {
                                    "north": {"type": "number"},
                                    "south": {"type": "number"},
                                    "east": {"type": "number"},
                                    "west": {"type": "number"}
                                },
                                "description": "Geographic bounding box"
                            },
                            "point_radius": {
                                "type": "object",
                                "properties": {
                                    "latitude": {"type": "number"},
                                    "longitude": {"type": "number"},
                                    "radius_km": {"type": "number"}
                                },
                                "description": "Search within radius of a point"
                            },
                            "year": {
                                "type": "integer",
                                "description": "Specific year"
                            },
                            "year_range": {
                                "type": "object",
                                "properties": {
                                    "start_year": {"type": "integer"},
                                    "end_year": {"type": "integer"}
                                },
                                "description": "Year range (inclusive)"
                            },
                            "month": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 12,
                                "description": "Month (1-12)"
                            },
                            "catalog_number": {
                                "type": "string",
                                "description": "Specimen catalog number"
                            },
                            "recorded_by": {
                                "type": "string",
                                "description": "Collector name"
                            },
                            "identified_by": {
                                "type": "string",
                                "description": "Identifier name"
                            },
                            "collection_name": {
                                "type": "string",
                                "description": "Museum collection name"
                            },
                            "institution": {
                                "type": "string",
                                "description": "Institution name"
                            },
                            "has_image": {
                                "type": "boolean",
                                "description": "Filter by image availability"
                            },
                            "image_quality": {
                                "type": "string",
                                "enum": ["thumbnail", "medium", "large", "all"],
                                "description": "Image quality for results (default: thumbnail)"
                            },
                            "free_text": {
                                "type": "string",
                                "description": "Free text search across all fields"
                            },
                            "sort_by": {
                                "type": "string",
                                "enum": ["relevance", "year_asc", "year_desc"],
                                "description": "Sort order (default: relevance)"
                            },
                            "limit": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 100,
                                "description": "Maximum results (default: 10, max: 100)"
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_specimen_statistics",
                    "description": "Get statistical summary and distributions for specimens matching search criteria",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "scientific_name": {"type": "string"},
                            "common_name": {"type": "string"},
                            "state_province": {"type": "string"},
                            "year_range": {
                                "type": "object",
                                "properties": {
                                    "start_year": {"type": "integer"},
                                    "end_year": {"type": "integer"}
                                }
                            },
                            "collection_name": {"type": "string"},
                            "include_facets": {
                                "type": "array",
                                "items": {
                                    "type": "string",
                                    "enum": ["year", "state_province", "collection_name", "family", "order", "class", "genus", "institution"]
                                },
                                "description": "Faceted distributions to include"
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_specimen_by_id",
                    "description": "Retrieve detailed information for a specific specimen by catalog number or UUID",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "specimen_id": {"type": "string"}
                        },
                        "required": ["specimen_id"]
                    }
                }
            }
        ]

    def get_or_create_session(self, session_id: str) -> List[Dict]:
        """Get existing session or create new one"""
        if session_id not in self.conversations:
            self.conversations[session_id] = [
                {"role": "system", "content": self.system_prompt}
            ]
        return self.conversations[session_id]

    def _trim_conversation_history(self, conversation: List[Dict]) -> List[Dict]:
        """Trim conversation history while preserving tool_calls/tool/assistant sequences"""
        if len(conversation) <= self.max_history_length:
            return conversation
        
        trimmed = [conversation[0]]
        messages = conversation[1:]
        keep_from_index = len(messages) - (self.max_history_length - 1)
        
        for i in range(keep_from_index, -1, -1):
            msg = messages[i]
            if msg.get('role') == 'assistant' and not msg.get('tool_calls'):
                trimmed.extend(messages[i+1:])
                print(f"[ChatbotService] Trimmed conversation from index {i+1}, keeping {len(trimmed)} messages")
                return trimmed
            if msg.get('role') == 'user' and i > 0:
                prev = messages[i-1]
                if prev.get('role') == 'assistant' and not prev.get('tool_calls'):
                    trimmed.extend(messages[i:])
                    print(f"[ChatbotService] Trimmed conversation from index {i}, keeping {len(trimmed)} messages")
                    return trimmed
        
        print(f"[ChatbotService] WARNING: Could not find safe trim point, keeping all messages")
        return conversation

    def execute_function(self, function_name: str, arguments: Dict) -> Dict:
        """Execute function with fallback logic for name conversion"""
        print(f"[ChatbotService] execute_function called: {function_name}")
        print(f"[ChatbotService] Raw arguments from OpenAI: {arguments}")
        sys.stdout.flush()
        
        if function_name == "search_specimens":
            return self._search_specimens_with_fallback(**arguments)
        elif function_name == "get_specimen_statistics":
            return self._get_specimen_statistics_with_fallback(**arguments)
        elif function_name == "get_specimen_by_id":
            return self._get_specimen_by_id(**arguments)
        else:
            raise ValueError(f"Unknown function: {function_name}")

    def _is_generic_animal_term(self, term: str) -> bool:
        """
        Check if a term is a generic animal category that won't appear in most species names.
        These terms need taxonomy resolution FIRST, not wildcard search.
        """
        # Generic terms that describe animal groups but don't appear in species common names
        generic_terms = {
            # Birds - "bird" doesn't appear in most bird names (kookaburra, magpie, etc.)
            'bird', 'birds',
            # Fish - "fish" doesn't appear in most fish names (barramundi, snapper, etc.)  
            'fish', 'fishes',
            # Insects - most insects aren't called "_____ insect"
            'insect', 'insects',
            # Mammals - "mammal" rarely in common names
            'mammal', 'mammals',
            # Reptiles - "reptile" rarely in common names
            'reptile', 'reptiles',
            # Amphibians
            'amphibian', 'amphibians',
            # Invertebrates
            'invertebrate', 'invertebrates',
        }
        
        term_lower = term.lower().strip()
        return term_lower in generic_terms

    def _search_specimens_with_fallback(self, **kwargs) -> Dict:
        """
        Search with intelligent fallback:
        1. For GENERIC terms (bird, fish, insect): resolve taxonomy FIRST
        2. For SPECIFIC terms (lyrebird, barramundi): try wildcard search first
        3. If no results, try alternative approaches
        """
        print(f"[ChatbotService] _search_specimens_with_fallback called with kwargs: {kwargs}")
        sys.stdout.flush()
        
        if kwargs.get('scientific_name') and kwargs.get('common_name'):
            print(f"[ChatbotService] WARNING: Both names provided! Removing common_name.")
            kwargs = kwargs.copy()
            del kwargs['common_name']
        
        common_name = kwargs.get('common_name')
        
        # For GENERIC animal terms, try taxonomy resolution FIRST
        if common_name and self._is_generic_animal_term(common_name):
            print(f"[ChatbotService] '{common_name}' is a generic term - trying taxonomy resolution FIRST")
            
            taxonomy_info = self._resolve_common_name_to_taxonomy(common_name)
            
            if taxonomy_info:
                rank, value, display_name = taxonomy_info
                print(f"[ChatbotService] ✓ Resolved '{common_name}' to {rank}: {value}")
                
                # Search using taxonomy instead of common_name
                kwargs_copy = kwargs.copy()
                del kwargs_copy['common_name']
                kwargs_copy[rank] = value
                
                taxonomy_results = self._search_specimens(**kwargs_copy)
                
                if taxonomy_results['total_records'] > 0:
                    print(f"[ChatbotService] ✓ Taxonomy search successful! Found {taxonomy_results['total_records']} records")
                    taxonomy_results['fallback_note'] = f"Searched using {rank} '{value}' for '{common_name}'"
                    taxonomy_results['resolved_taxonomy'] = {'rank': rank, 'value': value, 'common_term': common_name}
                    return taxonomy_results
                else:
                    print(f"[ChatbotService] Taxonomy search returned 0 results")
            else:
                print(f"[ChatbotService] Could not resolve taxonomy for '{common_name}'")
        
        # For SPECIFIC terms (or if taxonomy resolution failed), try wildcard search
        original_results = self._search_specimens(**kwargs)
        
        if original_results['total_records'] > 0:
            return original_results
        
        print("[ChatbotService] No results with original query, attempting fallback...")
        
        # Fallback: try taxonomy resolution (for specific terms that didn't match wildcard)
        if common_name and not self._is_generic_animal_term(common_name):
            print(f"[ChatbotService] Attempting taxonomic resolution for: {common_name}")
            
            taxonomy_info = self._resolve_common_name_to_taxonomy(common_name)
            
            if taxonomy_info:
                rank, value, display_name = taxonomy_info
                print(f"[ChatbotService] Resolved '{common_name}' to {rank}: {value}")
                
                kwargs_copy = kwargs.copy()
                del kwargs_copy['common_name']
                kwargs_copy[rank] = value
                
                fallback_results = self._search_specimens(**kwargs_copy)
                
                if fallback_results['total_records'] > 0:
                    print(f"[ChatbotService] ✓ Taxonomic fallback successful! Found {fallback_results['total_records']} records")
                    fallback_results['fallback_note'] = f"Searched using {rank} '{value}' for '{common_name}'"
                    fallback_results['resolved_taxonomy'] = {'rank': rank, 'value': value, 'common_term': common_name}
                    return fallback_results
            
            # Try scientific name lookup
            scientific_name = self._get_scientific_name_for_common(common_name)
            
            if scientific_name:
                print(f"[ChatbotService] Found scientific name: {scientific_name}, retrying...")
                kwargs_copy = kwargs.copy()
                del kwargs_copy['common_name']
                kwargs_copy['scientific_name'] = scientific_name
                
                fallback_results = self._search_specimens(**kwargs_copy)
                
                if fallback_results['total_records'] > 0:
                    print(f"[ChatbotService] ✓ Scientific name fallback successful!")
                    fallback_results['fallback_note'] = f"Searched using scientific name '{scientific_name}' for '{common_name}'"
                    return fallback_results
        
        elif kwargs.get('scientific_name'):
            scientific_name = kwargs['scientific_name']
            print(f"[ChatbotService] Attempting to find vernacular name for: {scientific_name}")
            
            vernacular_name = self._get_vernacular_name_for_scientific(scientific_name)
            
            if vernacular_name:
                print(f"[ChatbotService] Found vernacular name: {vernacular_name}, retrying...")
                kwargs_copy = kwargs.copy()
                del kwargs_copy['scientific_name']
                kwargs_copy['common_name'] = vernacular_name
                
                fallback_results = self._search_specimens(**kwargs_copy)
                
                if fallback_results['total_records'] > 0:
                    print(f"[ChatbotService] ✓ Vernacular fallback successful!")
                    fallback_results['fallback_note'] = f"Searched using vernacular name '{vernacular_name}'"
                    return fallback_results
        
        print("[ChatbotService] Fallback also returned no results")
        return original_results

    def _resolve_common_name_to_taxonomy(self, common_name: str) -> Optional[Tuple[str, str, str]]:
        """
        Dynamically resolve a generic common name to its appropriate taxonomic level.
        
        Uses ALA BIE to find multiple matching taxa, then identifies the common
        taxonomic level shared by all results.
        
        FIXED: Removed kingdom filter from API call - filter in code instead
        
        Args:
            common_name: Generic term like "bird", "fish", "insect", "beetle"
            
        Returns:
            Tuple of (rank, value, display_name) e.g., ('class', 'Aves', 'birds')
            or None if no common taxonomy found
        """
        try:
            import requests
            
            url = "https://bie.ala.org.au/ws/search"
            # FIXED: Don't use list for fq, use single string
            # FIXED: Remove kingdom filter - filter results in code instead
            params = {
                'q': common_name,
                'fq': 'idxtype:TAXON',  # Single string, not list
                'pageSize': 20
            }
            
            print(f"[ChatbotService] Querying ALA BIE for taxonomic resolution: '{common_name}'")
            print(f"[ChatbotService] ALA BIE URL params: {params}")
            
            response = requests.get(url, params=params, timeout=10)
            print(f"[ChatbotService] ALA BIE response status: {response.status_code}")
            
            if response.status_code != 200:
                print(f"[ChatbotService] ALA BIE request failed: {response.status_code}")
                print(f"[ChatbotService] Response text: {response.text[:500]}")
                return None
            
            data = response.json()
            all_results = data.get('searchResults', {}).get('results', [])
            
            print(f"[ChatbotService] ALA BIE returned {len(all_results)} total results")
            
            if not all_results:
                print(f"[ChatbotService] No ALA BIE results for '{common_name}'")
                return None
            
            # Filter to ANIMALIA kingdom in code (more reliable than API filter)
            results = [r for r in all_results if (r.get('kingdom') or '').upper() == 'ANIMALIA']
            print(f"[ChatbotService] After ANIMALIA filter: {len(results)} results")
            
            # Log first few results for debugging
            for i, r in enumerate(results[:3]):
                print(f"[ChatbotService]   Result {i+1}: {r.get('name')} - {r.get('rank')} - class={r.get('class')}")
            
            if not results:
                print(f"[ChatbotService] No ANIMALIA results for '{common_name}'")
                # Try without kingdom filter as last resort
                results = all_results
                print(f"[ChatbotService] Using all {len(results)} results without kingdom filter")
            
            # Check if any result IS the taxonomic rank itself
            for result in results:
                result_rank = result.get('rank', '').lower()
                result_name = result.get('scientificName') or result.get('name')
                
                if result_rank in ['class', 'order', 'family', 'subclass', 'superorder', 'infraorder', 'suborder']:
                    print(f"[ChatbotService] Found direct taxonomic match: {result_rank} = {result_name}")
                    # Normalize rank to one we support in biocache
                    normalized_rank = result_rank if result_rank in ['class', 'order', 'family'] else 'order'
                    return (normalized_rank, result_name, common_name)
            
            # Find the common taxonomic level across all results
            taxonomy_ranks = ['class', 'order', 'family', 'genus']
            
            for rank in taxonomy_ranks:
                values = set()
                for result in results:
                    value = result.get(rank)
                    if value:
                        values.add(value)
                
                if len(values) == 1:
                    shared_value = values.pop()
                    print(f"[ChatbotService] ✓ All {len(results)} results share {rank}: {shared_value}")
                    return (rank, shared_value, common_name)
                elif len(values) > 1:
                    print(f"[ChatbotService] Results have {len(values)} different {rank} values: {list(values)[:5]}")
            
            print(f"[ChatbotService] No common taxonomy found across results")
            return None
            
        except Exception as e:
            print(f"[ChatbotService] Error in taxonomic resolution: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _get_scientific_name_for_common(self, common_name: str) -> Optional[str]:
        """Try to find the scientific name for a common name. Prefers ANIMALIA kingdom."""
        try:
            import requests
            
            url = "https://bie.ala.org.au/ws/search"
            # FIXED: Use single string for fq, not list
            params = {
                'q': common_name,
                'fq': 'idxtype:TAXON',
                'pageSize': 20
            }
            
            print(f"[ChatbotService] ALA BIE scientific name lookup for: '{common_name}'")
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                all_results = data.get('searchResults', {}).get('results', [])
                
                # Filter to ANIMALIA in code
                results = [r for r in all_results if (r.get('kingdom') or '').upper() == 'ANIMALIA']
                
                if not results:
                    results = all_results  # Fallback to all results
                
                if results:
                    result = results[0]
                    kingdom = result.get('kingdom', 'Unknown')
                    print(f"[ChatbotService] Selected result kingdom: {kingdom}")
                    
                    scientific_name = result.get('scientificName') or result.get('name')
                    
                    if not scientific_name or ' ' not in scientific_name:
                        scientific_name = result.get('acceptedConceptName') or scientific_name
                    
                    if scientific_name:
                        print(f"[ChatbotService] ALA lookup found scientific name: '{scientific_name}'")
                        return scientific_name
                            
        except Exception as e:
            print(f"[ChatbotService] Error in ALA species lookup: {e}")
            import traceback
            traceback.print_exc()
        
        return None

    def _get_vernacular_name_for_scientific(self, scientific_name: str) -> Optional[str]:
        """Try to find the vernacular/common name for a scientific name."""
        try:
            import requests
            
            url = "https://bie.ala.org.au/ws/search"
            params = {
                'q': scientific_name,
                'fq': 'idxtype:TAXON',
                'pageSize': 1
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                results = data.get('searchResults', {}).get('results', [])
                
                if results:
                    vernacular_name = results[0].get('commonName') or results[0].get('vernacularName')
                    if vernacular_name:
                        print(f"[ChatbotService] ALA lookup found: {vernacular_name}")
                        return vernacular_name
        except Exception as e:
            print(f"[ChatbotService] Error in ALA species lookup: {e}")
        
        return None

    def _search_specimens(self, **kwargs) -> Dict:
        """Execute specimen search - supports taxonomic filters"""
        import os
        log_path = os.path.join(os.getcwd(), 'chatbot_debug.log')
        with open(log_path, 'a') as f:
            f.write(f"\n=== _search_specimens CALLED ===\n")
            f.write(f"kwargs: {kwargs}\n")
            f.flush()
        
        print(f"[ChatbotService] _search_specimens called with: {kwargs}")
        sys.stdout.flush()
        
        filters = {}
        lat = None
        lon = None
        radius = None
        
        # Taxonomic filters
        if kwargs.get('scientific_name'):
            filters['scientific_name'] = kwargs['scientific_name']
        elif kwargs.get('common_name'):
            filters['common_name'] = kwargs['common_name']
        
        # Higher taxonomy filters (from dynamic resolution)
        for tax_rank in ['class', 'order', 'family', 'genus', 'phylum', 'kingdom']:
            if kwargs.get(tax_rank):
                filters[tax_rank] = kwargs[tax_rank]
        
        # Geographic - STATE FILTER
        if kwargs.get('state_province'):
            filters['state_province'] = kwargs['state_province']
        
        # Geographic - LOCALITY (with intelligent geocoding)
        if kwargs.get('locality'):
            locality = kwargs['locality']
            
            geocoded_list = self.geocoding_service.geocode_location(
                locality, bias_to_australia=True, return_all_matches=True
            )
            
            if geocoded_list:
                if not isinstance(geocoded_list, list):
                    geocoded_list = [geocoded_list]
                
                if kwargs.get('state_province'):
                    user_state = kwargs['state_province']
                    geocoded_list = [loc for loc in geocoded_list if loc.get('state') == user_state]
                
                if len(geocoded_list) == 1:
                    geocoded = geocoded_list[0]
                    
                    if self.geocoding_service.should_use_state_filter(geocoded['place_type']):
                        state = geocoded.get('state')
                        if state and not kwargs.get('state_province'):
                            filters['state_province'] = state
                    else:
                        lat = geocoded['latitude']
                        lon = geocoded['longitude']
                        radius = self.geocoding_service.get_search_radius_km(geocoded['place_type'])
                        
                        if 'state_province' in filters:
                            print(f"[ChatbotService] Removing state filter to use spatial search only")
                            del filters['state_province']
                
                elif len(geocoded_list) > 1:
                    print(f"[ChatbotService] Found {len(geocoded_list)} locations, searching all")
                    
                    limit = min(kwargs.get('limit', 10), 100)
                    all_occurrences = []
                    total_sum = 0
                    
                    for location in geocoded_list:
                        loc_filters = filters.copy()
                        loc_filters['state_province'] = location.get('state')
                        
                        loc_results = self.biocache_service.search_occurrences(
                            filters=loc_filters, page=0, page_size=limit,
                            lat=location['latitude'], lon=location['longitude'],
                            radius=self.geocoding_service.get_search_radius_km(location['place_type'])
                        )
                        
                        all_occurrences.extend(loc_results.get('occurrences', []))
                        total_sum += loc_results.get('totalRecords', 0)
                    
                    seen = set()
                    unique = []
                    for occ in all_occurrences:
                        uuid = occ.get('id')
                        if uuid and uuid not in seen:
                            seen.add(uuid)
                            unique.append(occ)
                    
                    results = {'totalRecords': total_sum, 'occurrences': unique[:limit], 'ala_url': None}
                    kwargs['_skip_normal_search'] = True
            else:
                filters['locality'] = locality
        
        # Temporal
        if kwargs.get('year'):
            filters['year'] = kwargs['year']
        if kwargs.get('year_range'):
            yr = kwargs['year_range']
            filters['year_range'] = f"[{yr['start_year']} TO {yr['end_year']}]"
        if kwargs.get('month'):
            filters['month'] = kwargs['month']
        
        # Specimen details
        if kwargs.get('catalog_number'):
            filters['catalog_number'] = kwargs['catalog_number']
        if kwargs.get('recorded_by'):
            filters['recorded_by'] = kwargs['recorded_by']
        if kwargs.get('identified_by'):
            filters['identified_by'] = kwargs['identified_by']
        
        # Collection
        if kwargs.get('collection_name'):
            filters['collection_name'] = kwargs['collection_name']
        if kwargs.get('institution'):
            filters['institution'] = kwargs['institution']
        
        # Images
        if kwargs.get('has_image') is not None:
            filters['has_image'] = kwargs['has_image']
        
        # Free text
        if kwargs.get('free_text'):
            filters['free_text_search'] = kwargs['free_text']
        
        # Spatial parameters - explicit point_radius
        if kwargs.get('point_radius'):
            pr = kwargs['point_radius']
            lat = pr['latitude']
            lon = pr['longitude']
            radius = pr['radius_km']
        
        bounds = kwargs.get('bounds')
        limit = min(kwargs.get('limit', 10), 100)
        
        print(f"[ChatbotService] About to call search_occurrences with:")
        print(f"[ChatbotService]   lat={lat}, lon={lon}, radius={radius}")
        print(f"[ChatbotService]   filters={filters}")
        
        if not kwargs.get('_skip_normal_search'):
            results = self.biocache_service.search_occurrences(
                filters=filters if filters else None,
                page=0, page_size=limit, bounds=bounds,
                lat=lat, lon=lon, radius=radius,
                show_only_with_images=False
            )
        
        print(f"[ChatbotService] search_occurrences returned {results.get('totalRecords')} records")
        print(f"[ChatbotService] ala_url from backend: {results.get('ala_url')}")
        
        image_quality = kwargs.get('image_quality', 'thumbnail')
        
        formatted_results = {
            "total_records": results['totalRecords'],
            "returned_records": len(results['occurrences']),
            "specimens": [],
            "ala_url": results.get('ala_url')
        }
        
        for occ in results['occurrences'][:limit]:
            image_url = None
            if image_quality == 'thumbnail':
                image_url = occ.get('thumbnailUrl')
            elif image_quality == 'medium':
                image_url = occ.get('imageUrl')
            elif image_quality == 'large':
                image_url = occ.get('largeImageUrl')
            elif image_quality == 'all':
                image_url = {
                    'thumbnail': occ.get('thumbnailUrl'),
                    'medium': occ.get('imageUrl'),
                    'large': occ.get('largeImageUrl'),
                    'all_images': occ.get('images', [])
                }
            
            specimen = {
                "scientific_name": occ.get('scientificName'),
                "common_name": occ.get('commonName'),
                "catalog_number": occ.get('catalogNumber'),
                "uuid": occ.get('id'),
                "collection_name": occ.get('collectionName'),
                "institution": occ.get('institutionName'),
                "location": {
                    "state": occ.get('stateProvince'),
                    "locality": occ.get('locality'),
                    "coordinates": {"latitude": occ.get('latitude'), "longitude": occ.get('longitude')},
                    "coordinate_uncertainty_meters": occ.get('coordinateUncertaintyInMeters')
                },
                "date": {
                    "event_date": occ.get('eventDate'),
                    "year": occ.get('year'),
                    "month": occ.get('month'),
                    "day": occ.get('day')
                },
                "people": {
                    "recorded_by": occ.get('recordedBy'),
                    "identified_by": occ.get('identifiedBy')
                },
                "taxonomy": {
                    "kingdom": occ.get('kingdom'),
                    "phylum": occ.get('phylum'),
                    "class": occ.get('class'),
                    "order": occ.get('order'),
                    "family": occ.get('family'),
                    "genus": occ.get('genus'),
                    "species": occ.get('species')
                },
                "images": image_url
            }
            formatted_results["specimens"].append(specimen)
        
        if results.get('facets'):
            formatted_results['facets'] = results['facets']
        
        print(f"[ChatbotService] Returning ala_url: {formatted_results.get('ala_url')}")
        sys.stdout.flush()
        
        return formatted_results

    def _get_specimen_statistics_with_fallback(self, **kwargs) -> Dict:
        """Get statistics with fallback logic"""
        common_name = kwargs.get('common_name')
        
        # For generic terms, try taxonomy first
        if common_name and self._is_generic_animal_term(common_name):
            taxonomy_info = self._resolve_common_name_to_taxonomy(common_name)
            
            if taxonomy_info:
                rank, value, _ = taxonomy_info
                kwargs_copy = kwargs.copy()
                del kwargs_copy['common_name']
                kwargs_copy[rank] = value
                
                results = self._get_specimen_statistics(**kwargs_copy)
                if results['total_records'] > 0:
                    return results
        
        original_results = self._get_specimen_statistics(**kwargs)
        
        if original_results['total_records'] > 0:
            return original_results
        
        print("[ChatbotService] No statistics with original query, attempting fallback...")
        
        if common_name:
            taxonomy_info = self._resolve_common_name_to_taxonomy(common_name)
            
            if taxonomy_info:
                rank, value, _ = taxonomy_info
                kwargs_copy = kwargs.copy()
                del kwargs_copy['common_name']
                kwargs_copy[rank] = value
                
                fallback_results = self._get_specimen_statistics(**kwargs_copy)
                if fallback_results['total_records'] > 0:
                    print(f"[ChatbotService] ✓ Statistics taxonomic fallback successful!")
                    return fallback_results
            
            scientific_name = self._get_scientific_name_for_common(common_name)
            
            if scientific_name:
                kwargs_copy = kwargs.copy()
                del kwargs_copy['common_name']
                kwargs_copy['scientific_name'] = scientific_name
                
                fallback_results = self._get_specimen_statistics(**kwargs_copy)
                if fallback_results['total_records'] > 0:
                    print(f"[ChatbotService] ✓ Statistics fallback successful!")
                    return fallback_results
        
        elif kwargs.get('scientific_name'):
            scientific_name = kwargs['scientific_name']
            vernacular_name = self._get_vernacular_name_for_scientific(scientific_name)
            
            if vernacular_name:
                kwargs_copy = kwargs.copy()
                del kwargs_copy['scientific_name']
                kwargs_copy['common_name'] = vernacular_name
                
                fallback_results = self._get_specimen_statistics(**kwargs_copy)
                if fallback_results['total_records'] > 0:
                    print(f"[ChatbotService] ✓ Statistics fallback successful!")
                    return fallback_results
        
        return original_results

    def _get_specimen_statistics(self, **kwargs) -> Dict:
        """Get statistics - no fallbacks"""
        filters = {}
        
        if kwargs.get('scientific_name'):
            filters['scientific_name'] = kwargs['scientific_name']
        elif kwargs.get('common_name'):
            filters['common_name'] = kwargs['common_name']
        
        for tax_rank in ['class', 'order', 'family', 'genus']:
            if kwargs.get(tax_rank):
                filters[tax_rank] = kwargs[tax_rank]
        
        if kwargs.get('state_province'):
            filters['state_province'] = kwargs['state_province']
        if kwargs.get('collection_name'):
            filters['collection_name'] = kwargs['collection_name']
        if kwargs.get('year_range'):
            yr = kwargs['year_range']
            filters['year_range'] = f"[{yr['start_year']} TO {yr['end_year']}]"
        
        results = self.biocache_service.search_occurrences(
            filters=filters if filters else None, page=0, page_size=0
        )
        
        statistics = {"total_records": results['totalRecords'], "faceted_counts": {}}
        
        requested_facets = kwargs.get('include_facets', [])
        all_facets = results.get('facets', {})
        
        if requested_facets:
            facet_mapping = {
                'year': 'year', 'state_province': 'state_province',
                'collection_name': 'collection_name', 'family': 'family',
                'order': 'order', 'class': 'class', 'genus': 'genus', 'institution': 'institution'
            }
            for facet_name in requested_facets:
                mapped_name = facet_mapping.get(facet_name)
                if mapped_name and mapped_name in all_facets:
                    statistics['faceted_counts'][facet_name] = all_facets[mapped_name]
        else:
            statistics['faceted_counts'] = all_facets
        
        return statistics

    def _get_specimen_by_id(self, specimen_id: str) -> Dict:
        """Get specimen by ID"""
        results = self.biocache_service.search_occurrences(
            filters={'catalog_number': specimen_id}, page=0, page_size=1
        )
        
        if results['totalRecords'] == 0:
            raise ValueError(f"No specimen found with ID: {specimen_id}")
        
        occ = results['occurrences'][0]
        
        specimen = {
            "scientific_name": occ.get('scientificName'),
            "common_name": occ.get('commonName'),
            "catalog_number": occ.get('catalogNumber'),
            "uuid": occ.get('id'),
            "collection": {
                "name": occ.get('collectionName'),
                "institution": occ.get('institutionName'),
                "basis_of_record": occ.get('basisOfRecord')
            },
            "location": {
                "state": occ.get('stateProvince'),
                "locality": occ.get('locality'),
                "latitude": occ.get('latitude'),
                "longitude": occ.get('longitude'),
                "coordinate_uncertainty_meters": occ.get('coordinateUncertaintyInMeters')
            },
            "temporal": {
                "event_date": occ.get('eventDate'),
                "year": occ.get('year'),
                "month": occ.get('month'),
                "day": occ.get('day')
            },
            "people": {
                "recorded_by": occ.get('recordedBy'),
                "identified_by": occ.get('identifiedBy')
            },
            "taxonomy": {
                "kingdom": occ.get('kingdom'),
                "phylum": occ.get('phylum'),
                "class": occ.get('class'),
                "order": occ.get('order'),
                "family": occ.get('family'),
                "genus": occ.get('genus'),
                "species": occ.get('species')
            },
            "images": {
                "thumbnail": occ.get('thumbnailUrl'),
                "medium": occ.get('imageUrl'),
                "large": occ.get('largeImageUrl'),
                "all": occ.get('images', [])
            }
        }
        
        return {"specimen": specimen, "found": True}

    def process_message(self, message: str, session_id: str = "default", image_data: Optional[str] = None) -> Dict:
        """Process message - logs errors and provides helpful responses"""
        try:
            conversation = self.get_or_create_session(session_id)
            
            user_message = {"role": "user", "content": []}
            
            if message:
                user_message["content"].append({"type": "text", "text": message})
            
            if image_data:
                if image_data.startswith('data:image'):
                    image_data = image_data.split(',')[1]
                
                user_message["content"].append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{image_data}", "detail": "high"}
                })
                
                if not message:
                    user_message["content"].insert(0, {
                        "type": "text",
                        "text": "Identify the animal species in this image. Provide scientific name, common name, taxonomic classification, and key identifying features."
                    })
            
            conversation.append(user_message)
            conversation = self._trim_conversation_history(conversation)
            self.conversations[session_id] = conversation
            
            response = self.client.chat.completions.create(
                model=self.model, messages=conversation, tools=self.tools, tool_choice="auto"
            )
            
            message_response = response.choices[0].message
            
            if message_response.tool_calls:
                tool_results = []
                
                for tool_call in message_response.tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    
                    print(f"Executing: {function_name}({function_args})")
                    
                    function_result = self.execute_function(function_name, function_args)
                    
                    tool_results.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": json.dumps(function_result)
                    })
                
                conversation.append({
                    "role": "assistant",
                    "content": message_response.content,
                    "tool_calls": [
                        {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                        for tc in message_response.tool_calls
                    ]
                })
                
                for tool_result in tool_results:
                    conversation.append(tool_result)
                
                final_response = self.client.chat.completions.create(model=self.model, messages=conversation)
                
                assistant_message = final_response.choices[0].message.content
                response_type = "data_response" if not image_data else "image_and_data_response"
                
                assistant_message = self.response_cleaner.clean_response(assistant_message, tool_results)
                
            else:
                assistant_message = message_response.content
                response_type = "image_analysis" if image_data else "text_response"
        
            conversation.append({"role": "assistant", "content": assistant_message})
            
            return {
                "success": True,
                "response": assistant_message,
                "session_id": session_id,
                "type": response_type,
                "suggestions": self.get_contextual_suggestions(image_data is not None)
            }
            
        except Exception as e:
            print(f"ERROR in process_message: {str(e)}")
            import traceback
            traceback.print_exc()
            
            error_msg = "I encountered an error searching the collection. "
            
            if "common_name" in str(e).lower() or "vernacular" in str(e).lower():
                error_msg += "The common name search may not have matched any records. Try using the scientific name instead."
            elif "no specimen found" in str(e).lower():
                error_msg += "No specimens matched your search criteria."
            elif "api" in str(e).lower() or "connection" in str(e).lower():
                error_msg += "There was a problem connecting to the ALA database. Please try again."
            else:
                error_msg += "Please try rephrasing your question or contact support if this persists."
            
            return {
                "success": False,
                "response": error_msg,
                "session_id": session_id,
                "error": str(e),
                "suggestions": self.get_default_suggestions()
            }

    def get_contextual_suggestions(self, had_image: bool) -> List[str]:
        if had_image:
            return ["Search for this species in our collection", "Where has this species been found?", "Show me more specimens with images"]
        return ["Show me specimens from a specific collector", "What's the distribution by state?", "Find specimens from a specific year range"]

    def get_default_suggestions(self) -> List[str]:
        return ["Show me kangaroo specimens from NSW", "How many fish specimens are in the collection?", "What species were collected in the 1980s?"]

    def clear_session(self, session_id: str = "default") -> Dict:
        if session_id in self.conversations:
            del self.conversations[session_id]
        return {"success": True, "message": "Conversation history cleared", "session_id": session_id}

    def get_session_history(self, session_id: str = "default") -> Dict:
        conversation = self.get_or_create_session(session_id)
        display_history = [msg for msg in conversation[1:] if msg.get("role") in ["user", "assistant"] and msg.get("content")]
        return {"success": True, "history": display_history, "session_id": session_id, "message_count": len(display_history)}