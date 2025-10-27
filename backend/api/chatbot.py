"""
Enhanced chatbot service with comprehensive OpenAI tools API for ALA Biocache integration
Implements fallback logic: vernacular name → scientific name (and vice versa)
"""
import base64
from typing import Dict, List, Optional
import json
import re
import sys
from openai import OpenAI
from config import Config
from api.biocache import BiocacheService
from api.response_cleaner import ResponseCleaner


class ChatbotService:
    def __init__(self):
        """Initialize the chatbot with OpenAI client and comprehensive tool definitions"""
        self.client = OpenAI(api_key=Config.OPENAI_API_KEY)
        self.biocache_service = BiocacheService()
        self.response_cleaner = ResponseCleaner()
        
        self.model = "gpt-5-mini"
        self.conversations = {}
        self.max_history_length = 20
        
        # Simplified system prompt - focus on natural language only
        self.system_prompt = """You are an AI assistant for the Australian Museum Collection Explorer (OZCAM dataset via ALA Biocache API).

## Your Job

1. Understand what the user wants to know about museum specimens
2. Call the appropriate function to get the data
3. Provide a clear, natural language answer

## Available Functions

- **search_specimens**: Search for specimens with various filters (taxonomy, location, dates, collectors, etc.)
- **get_specimen_statistics**: Get counts and distributions across different categories
- **get_specimen_by_id**: Look up a specific specimen by catalog number

## CRITICAL RULE: Taxonomic Names

When calling search_specimens or get_specimen_statistics:
- Use EITHER scientific_name OR common_name - NEVER BOTH in the same function call
- If the user provides a common name (like "kangaroo"), use only common_name parameter
- If the user provides a scientific name (like "Macropus rufus"), use only scientific_name parameter
- The backend will automatically handle fallback if no results are found

## Response Guidelines

- Be concise and helpful (2-3 sentences for simple queries, more for detailed results)
- Provide actual numbers and facts from the API data
- When you retrieve specimen search results, the API provides a link - always include it at the end of your response
- NEVER show JSON, function calls, or internal processing to the user
- If no results found, say so clearly
- Don't follow up with more questions, or offer follow-up options to the user
- When the user asks for images of a species, show up to five images.

## Example

User: "Show me kangaroo specimens from the 1980s"
You: Call search_specimens with common_name="kangaroo" (NOT scientific_name), then respond naturally like:
"I found 127 kangaroo specimens in the collection from the 1980s. Most are from New South Wales and Queensland. [View results on Atals of Living Australia](link)"

Be natural and helpful."""

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
                            "basis_of_record": {
                                "type": "string",
                                "enum": ["PRESERVED_SPECIMEN", "HUMAN_OBSERVATION", "LIVING_SPECIMEN", "MACHINE_OBSERVATION"],
                                "description": "Record type"
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
                                    "enum": ["year", "state_province", "collection_name", "family", "order", "class", "genus", "basis_of_record", "institution"]
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

    def execute_function(self, function_name: str, arguments: Dict) -> Dict:
        """Execute function with fallback logic for name conversion (RULE 3)"""
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

    def _search_specimens_with_fallback(self, **kwargs) -> Dict:
        """
        RULE 3 IMPLEMENTATION: Search with fallback
        - If vernacular name returns 0 results, try scientific name
        - If scientific name returns 0 results, try vernacular name
        """
        print(f"[ChatbotService] _search_specimens_with_fallback called with kwargs: {kwargs}")
        sys.stdout.flush()
        
        # DEFENSIVE: If both scientific_name and common_name are provided, remove common_name
        # This enforces Rule 4 even if the LLM sends both
        if kwargs.get('scientific_name') and kwargs.get('common_name'):
            print(f"[ChatbotService] WARNING: Both scientific_name and common_name provided! Removing common_name to enforce Rule 4.")
            print(f"[ChatbotService]   scientific_name: {kwargs['scientific_name']}")
            print(f"[ChatbotService]   common_name (will be ignored): {kwargs['common_name']}")
            kwargs = kwargs.copy()
            del kwargs['common_name']
        
        # First attempt with original query
        original_results = self._search_specimens(**kwargs)
        
        # If we got results, return them
        if original_results['total_records'] > 0:
            return original_results
        
        # RULE 3: No results found, try fallback
        print("[ChatbotService] No results with original query, attempting fallback...")
        
        # Case 1: User searched with vernacular name → try scientific name
        if kwargs.get('common_name'):
            common_name = kwargs['common_name']
            print(f"[ChatbotService] Attempting to find scientific name for: {common_name}")
            
            # Try to get scientific name from first result's taxonomy
            scientific_name = self._get_scientific_name_for_common(common_name)
            
            if scientific_name:
                print(f"[ChatbotService] Found scientific name: {scientific_name}, retrying search...")
                # Retry with scientific name
                kwargs_copy = kwargs.copy()
                del kwargs_copy['common_name']
                kwargs_copy['scientific_name'] = scientific_name
                
                fallback_results = self._search_specimens(**kwargs_copy)
                
                if fallback_results['total_records'] > 0:
                    print(f"[ChatbotService] ✓ Fallback successful! Found {fallback_results['total_records']} records")
                    # Add note about the conversion
                    fallback_results['fallback_note'] = f"Searched using scientific name '{scientific_name}' for common name '{common_name}'"
                    return fallback_results
        
        # Case 2: User searched with scientific name → try vernacular name
        elif kwargs.get('scientific_name'):
            scientific_name = kwargs['scientific_name']
            print(f"[ChatbotService] Attempting to find vernacular name for: {scientific_name}")
            
            # Try to get vernacular name
            vernacular_name = self._get_vernacular_name_for_scientific(scientific_name)
            
            if vernacular_name:
                print(f"[ChatbotService] Found vernacular name: {vernacular_name}, retrying search...")
                # Retry with vernacular name
                kwargs_copy = kwargs.copy()
                del kwargs_copy['scientific_name']
                kwargs_copy['common_name'] = vernacular_name
                
                fallback_results = self._search_specimens(**kwargs_copy)
                
                if fallback_results['total_records'] > 0:
                    print(f"[ChatbotService] ✓ Fallback successful! Found {fallback_results['total_records']} records")
                    # Add note about the conversion
                    fallback_results['fallback_note'] = f"Searched using vernacular name '{vernacular_name}' for scientific name '{scientific_name}'"
                    return fallback_results
        
        # If fallback also failed, return the original empty results
        print("[ChatbotService] Fallback also returned no results")
        return original_results

    def _get_scientific_name_for_common(self, common_name: str) -> Optional[str]:
        """
        Try to find the scientific name for a common name
        Uses ALA's name matching API or searches broader context
        """
        try:
            # Try searching ALA species lookup
            import requests
            
            # ALA species lookup endpoint
            url = "https://bie.ala.org.au/ws/search"
            params = {
                'q': common_name,
                'fq': 'idxtype:TAXON',
                'pageSize': 1
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                results = data.get('searchResults', {}).get('results', [])
                
                if results:
                    result = results[0]
                    print(f"[ChatbotService] ALA BIE API result: {result}")
                    
                    # Prefer scientificName over name (name might be just genus)
                    scientific_name = result.get('scientificName') or result.get('name')
                    
                    # Also check for acceptedConceptName which is often more complete
                    if not scientific_name or ' ' not in scientific_name:
                        scientific_name = result.get('acceptedConceptName') or scientific_name
                    
                    if scientific_name:
                        print(f"[ChatbotService] ALA lookup found scientific name: '{scientific_name}'")
                        return scientific_name
                    else:
                        print(f"[ChatbotService] No scientific name found in result")
        except Exception as e:
            print(f"[ChatbotService] Error in ALA species lookup: {e}")
            import traceback
            traceback.print_exc()
        
        return None

    def _get_vernacular_name_for_scientific(self, scientific_name: str) -> Optional[str]:
        """
        Try to find the vernacular/common name for a scientific name
        Uses ALA's species lookup
        """
        try:
            import requests
            
            # ALA species lookup endpoint
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
                    # Get the vernacular name from first result
                    vernacular_name = results[0].get('commonName') or results[0].get('vernacularName')
                    if vernacular_name:
                        print(f"[ChatbotService] ALA lookup found: {vernacular_name}")
                        return vernacular_name
        except Exception as e:
            print(f"[ChatbotService] Error in ALA species lookup: {e}")
        
        return None

    def _search_specimens(self, **kwargs) -> Dict:
        """Execute specimen search - no fallbacks here, just direct search"""
        # CRITICAL: Confirm this function is being called
        import os
        log_path = os.path.join(os.getcwd(), 'chatbot_debug.log')
        with open(log_path, 'a') as f:
            f.write(f"\n=== _search_specimens CALLED ===\n")
            f.write(f"kwargs: {kwargs}\n")
            f.flush()
        
        print(f"[ChatbotService] _search_specimens called with: {kwargs}")
        sys.stdout.flush()
        
        filters = {}
        
        # Taxonomic - CRITICAL: Use if/elif to prevent both names (RULE 4)
        if kwargs.get('scientific_name'):
            filters['scientific_name'] = kwargs['scientific_name']
        elif kwargs.get('common_name'):
            filters['common_name'] = kwargs['common_name']
        
        # Geographic
        if kwargs.get('state_province'):
            filters['state_province'] = kwargs['state_province']
        if kwargs.get('locality'):
            filters['locality'] = kwargs['locality']
        
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
        if kwargs.get('basis_of_record'):
            filters['basis_of_record'] = kwargs['basis_of_record']
        
        # Images
        if kwargs.get('has_image') is not None:
            filters['has_image'] = kwargs['has_image']
        
        # Free text
        if kwargs.get('free_text'):
            filters['free_text_search'] = kwargs['free_text']
        
        # Spatial parameters
        lat = None
        lon = None
        radius = None
        if kwargs.get('point_radius'):
            pr = kwargs['point_radius']
            lat = pr['latitude']
            lon = pr['longitude']
            radius = pr['radius_km']
        
        bounds = kwargs.get('bounds')
        limit = min(kwargs.get('limit', 10), 100)
        
        # Call API
        results = self.biocache_service.search_occurrences(
            filters=filters if filters else None,
            page=0,
            page_size=limit,
            bounds=bounds,
            lat=lat,
            lon=lon,
            radius=radius
        )
        
        # DEBUG: Check what we got back
        print(f"[ChatbotService] search_occurrences returned {results.get('totalRecords')} records")
        print(f"[ChatbotService] ala_url from backend: {results.get('ala_url')}")
        
        # Determine image quality
        image_quality = kwargs.get('image_quality', 'thumbnail')
        
        # Format results
        formatted_results = {
            "total_records": results['totalRecords'],
            "returned_records": len(results['occurrences']),
            "specimens": [],
            "ala_url": results.get('ala_url')  # Include URL built by backend
        }
        
        for occ in results['occurrences'][:limit]:
            # Select image URL based on quality
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
                "basis_of_record": occ.get('basisOfRecord'),
                "location": {
                    "state": occ.get('stateProvince'),
                    "locality": occ.get('locality'),
                    "coordinates": {
                        "latitude": occ.get('latitude'),
                        "longitude": occ.get('longitude')
                    },
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
        
        # CRITICAL DEBUG: Log what we're returning
        import os
        log_path = os.path.join(os.getcwd(), 'chatbot_debug.log')
        with open(log_path, 'a') as f:
            f.write(f"\n=== _search_specimens returning ===\n")
            f.write(f"total_records: {formatted_results['total_records']}\n")
            f.write(f"ala_url: {formatted_results.get('ala_url')}\n")
            f.flush()
        
        print(f"[ChatbotService] Returning ala_url: {formatted_results.get('ala_url')}")
        sys.stdout.flush()
        
        return formatted_results

    def _get_specimen_statistics_with_fallback(self, **kwargs) -> Dict:
        """Get statistics with fallback logic"""
        # First attempt
        original_results = self._get_specimen_statistics(**kwargs)
        
        # If we got results, return them
        if original_results['total_records'] > 0:
            return original_results
        
        # RULE 3: Try fallback
        print("[ChatbotService] No statistics with original query, attempting fallback...")
        
        # Case 1: Vernacular → Scientific
        if kwargs.get('common_name'):
            common_name = kwargs['common_name']
            scientific_name = self._get_scientific_name_for_common(common_name)
            
            if scientific_name:
                kwargs_copy = kwargs.copy()
                del kwargs_copy['common_name']
                kwargs_copy['scientific_name'] = scientific_name
                
                fallback_results = self._get_specimen_statistics(**kwargs_copy)
                if fallback_results['total_records'] > 0:
                    print(f"[ChatbotService] ✓ Statistics fallback successful!")
                    return fallback_results
        
        # Case 2: Scientific → Vernacular
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
        
        # CRITICAL: Use if/elif to prevent both names (RULE 4)
        if kwargs.get('scientific_name'):
            filters['scientific_name'] = kwargs['scientific_name']
        elif kwargs.get('common_name'):
            filters['common_name'] = kwargs['common_name']
        if kwargs.get('state_province'):
            filters['state_province'] = kwargs['state_province']
        if kwargs.get('collection_name'):
            filters['collection_name'] = kwargs['collection_name']
        if kwargs.get('year_range'):
            yr = kwargs['year_range']
            filters['year_range'] = f"[{yr['start_year']} TO {yr['end_year']}]"
        
        results = self.biocache_service.search_occurrences(
            filters=filters if filters else None,
            page=0,
            page_size=0
        )
        
        statistics = {
            "total_records": results['totalRecords'],
            "faceted_counts": {}
        }
        
        requested_facets = kwargs.get('include_facets', [])
        all_facets = results.get('facets', {})
        
        if requested_facets:
            facet_mapping = {
                'year': 'year',
                'state_province': 'state_province',
                'collection_name': 'collection_name',
                'family': 'family',
                'order': 'order',
                'class': 'class',
                'genus': 'genus',
                'basis_of_record': 'basis_of_record',
                'institution': 'institution'
            }
            
            for facet_name in requested_facets:
                mapped_name = facet_mapping.get(facet_name)
                if mapped_name and mapped_name in all_facets:
                    statistics['faceted_counts'][facet_name] = all_facets[mapped_name]
        else:
            statistics['faceted_counts'] = all_facets
        
        return statistics

    def _get_specimen_by_id(self, specimen_id: str) -> Dict:
        """Get specimen by ID - no fallbacks"""
        results = self.biocache_service.search_occurrences(
            filters={'catalog_number': specimen_id},
            page=0,
            page_size=1
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

    def process_message(
        self, 
        message: str, 
        session_id: str = "default",
        image_data: Optional[str] = None
    ) -> Dict:
        """Process message - logs errors and provides helpful responses"""
        try:
            conversation = self.get_or_create_session(session_id)
            
            user_message = {"role": "user", "content": []}
            
            if message:
                user_message["content"].append({
                    "type": "text",
                    "text": message
                })
            
            if image_data:
                if image_data.startswith('data:image'):
                    image_data = image_data.split(',')[1]
                
                user_message["content"].append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{image_data}",
                        "detail": "high"
                    }
                })
                
                if not message:
                    user_message["content"].insert(0, {
                        "type": "text",
                        "text": "Identify the animal species in this image. Provide scientific name, common name, taxonomic classification, and key identifying features."
                    })
            
            conversation.append(user_message)
            
            if len(conversation) > self.max_history_length:
                conversation = [conversation[0]] + conversation[-(self.max_history_length-1):]
                self.conversations[session_id] = conversation
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=conversation,
                tools=self.tools,
                tool_choice="auto"
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
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        } for tc in message_response.tool_calls
                    ]
                })
                
                for tool_result in tool_results:
                    conversation.append(tool_result)
                
                final_response = self.client.chat.completions.create(
                    model=self.model,
                    messages=conversation
                )
                
                assistant_message = final_response.choices[0].message.content
                response_type = "data_response" if not image_data else "image_and_data_response"
                
                # Clean the response to remove JSON, fix URLs, etc.
                assistant_message = self.response_cleaner.clean_response(
                    assistant_message, 
                    tool_results
                )
                
            else:
                assistant_message = message_response.content
                response_type = "image_analysis" if image_data else "text_response"
        
            conversation.append({
                "role": "assistant",
                "content": assistant_message
            })
            
            return {
                "success": True,
                "response": assistant_message,
                "session_id": session_id,
                "type": response_type,
                "suggestions": self.get_contextual_suggestions(image_data is not None)
            }
            
        except Exception as e:
            # Log the full error for debugging
            print(f"ERROR in process_message: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # Provide helpful response to user
            error_msg = "I encountered an error searching the collection. "
            
            # Try to provide context-specific help
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
        """Get contextual suggestions"""
        if had_image:
            return [
                "Search for this species in our collection",
                "Where has this species been found?",
                "Show me more specimens with images"
            ]
        return [
            "Show me specimens from a specific collector",
            "What's the distribution by state?",
            "Find specimens from a specific year range"
        ]

    def get_default_suggestions(self) -> List[str]:
        """Get default suggestions"""
        return [
            "Show me kangaroo specimens from NSW",
            "How many fish specimens are in the collection?",
            "What species were collected in the 1980s?"
        ]

    def clear_session(self, session_id: str = "default") -> Dict:
        """Clear conversation history"""
        if session_id in self.conversations:
            del self.conversations[session_id]
        return {
            "success": True,
            "message": "Conversation history cleared",
            "session_id": session_id
        }

    def get_session_history(self, session_id: str = "default") -> Dict:
        """Get conversation history"""
        conversation = self.get_or_create_session(session_id)
        display_history = [
            msg for msg in conversation[1:]
            if msg.get("role") in ["user", "assistant"] and msg.get("content")
        ]
        
        return {
            "success": True,
            "history": display_history,
            "session_id": session_id,
            "message_count": len(display_history)
        }