"""
Geocoding service for converting location names to coordinates
Uses Google Geocoding API to handle Australian suburbs, cities, and regions
"""
import requests
from typing import Optional, Dict
from config import Config


class GeocodingService:
    """
    Geocode location strings (suburbs, cities, etc.) to coordinates
    for spatial queries in the ALA Biocache API
    """
    
    def __init__(self):
        self.api_key = Config.GOOGLE_GEOCODING_API_KEY
        self.base_url = "https://maps.googleapis.com/maps/api/geocode/json"
        self.cache = {}  # Simple in-memory cache to reduce API calls
    
    def geocode_location(self, location: str, bias_to_australia: bool = True, return_all_matches: bool = False) -> Optional[Dict]:
        """
        Geocode a location string to coordinates with Australian bias.
        
        Args:
            location: Location name (e.g., "Castle Hill", "Sydney", "Melbourne")
            bias_to_australia: Whether to bias results to Australian locations
            return_all_matches: If True, return list of all matching Australian locations
        
        Returns:
            If return_all_matches=False (default):
                Dictionary with geocoding results for the primary match
            If return_all_matches=True:
                List of dictionaries, one for each matching location in Australia
            
            Dictionary format:
            {
                'latitude': float,
                'longitude': float,
                'formatted_address': str,
                'place_type': str,  # e.g., 'locality', 'administrative_area_level_2'
                'bounds': dict,  # Optional bounding box
                'state': str  # e.g., "New South Wales"
            }
            Or None if geocoding fails
        """
        # Check cache first
        cache_key = f"{location}_{bias_to_australia}_{return_all_matches}"
        if cache_key in self.cache:
            print(f"[GeocodingService] Cache hit for '{location}'")
            return self.cache[cache_key]
        
        try:
            # Add "Australia" to bias results toward Australian locations
            search_query = f"{location}, Australia" if bias_to_australia else location
            
            params = {
                'address': search_query,
                'key': self.api_key,
                'region': 'au',  # Bias to Australia
                'components': 'country:AU'  # Restrict to Australia
            }
            
            print(f"[GeocodingService] Geocoding: '{search_query}'")
            response = requests.get(self.base_url, params=params, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            if data['status'] == 'OK' and data['results']:
                
                # Process all results that are in Australia
                all_results = []
                for result in data['results']:
                    location_data = result['geometry']['location']
                    formatted_address = result['formatted_address']
                    
                    # Only include if it's in Australia
                    if 'Australia' in formatted_address:
                        geocoded_result = {
                            'latitude': location_data['lat'],
                            'longitude': location_data['lng'],
                            'formatted_address': formatted_address,
                            'place_type': result['types'][0] if result.get('types') else 'unknown',
                            'bounds': result['geometry'].get('bounds'),
                            'viewport': result['geometry'].get('viewport'),
                            'state': self.extract_state_from_address(formatted_address)
                        }
                        all_results.append(geocoded_result)
                
                if not all_results:
                    print(f"[GeocodingService] No Australian results for '{location}'")
                    return None
                
                # Log what we found
                if len(all_results) > 1:
                    print(f"[GeocodingService] Found {len(all_results)} locations named '{location}' in Australia:")
                    for idx, res in enumerate(all_results, 1):
                        print(f"[GeocodingService]   {idx}. {res['formatted_address']} ({res['state']})")
                else:
                    print(f"[GeocodingService] ✓ Geocoded '{location}' to: {all_results[0]['latitude']}, {all_results[0]['longitude']}")
                    print(f"[GeocodingService]   Formatted: {all_results[0]['formatted_address']}")
                    print(f"[GeocodingService]   Type: {all_results[0]['place_type']}")
                
                # Cache and return
                if return_all_matches:
                    self.cache[cache_key] = all_results
                    return all_results
                else:
                    # Return primary (first) result
                    self.cache[cache_key] = all_results[0]
                    return all_results[0]
            
            elif data['status'] == 'ZERO_RESULTS':
                print(f"[GeocodingService] No results for '{location}'")
                return None
            
            else:
                print(f"[GeocodingService] Geocoding API error: {data['status']}")
                return None
            
        except Exception as e:
            print(f"[GeocodingService] Error geocoding '{location}': {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_search_radius_km(self, place_type: str) -> float:
        """
        Determine appropriate search radius based on place type.
        Different place types need different search radii:
        - Suburbs are smaller → smaller radius
        - Cities are larger → larger radius
        - States are huge → use state filter instead of radius
        
        Args:
            place_type: Google place type (e.g., 'locality', 'administrative_area_level_2')
        
        Returns:
            Radius in kilometers
        """
        radius_map = {
            'locality': 5,  # Suburb/town: 5km radius
            'sublocality': 3,  # Sub-suburb/neighborhood: 3km radius
            'sublocality_level_1': 3,
            'postal_code': 5,  # Postcode area: 5km radius
            'administrative_area_level_2': 20,  # City/LGA: 20km radius
            'administrative_area_level_1': 50,  # State: 50km (though state filter preferred)
            'colloquial_area': 10,  # Named area (e.g., "Inner West"): 10km radius
            'neighborhood': 3,  # Neighborhood: 3km radius
            'route': 2,  # Street: 2km radius
        }
        
        radius = radius_map.get(place_type, 10)  # Default 10km if unknown
        print(f"[GeocodingService] Using {radius}km radius for place_type '{place_type}'")
        return radius
    
    def should_use_state_filter(self, place_type: str) -> bool:
        """
        Determine if we should use state filter instead of point-radius.
        For large areas like states, point-radius is inefficient.
        
        Returns:
            True if this is a state-level query (use state filter)
            False if this is a suburb/city-level query (use point-radius)
        """
        state_level_types = [
            'administrative_area_level_1',  # State/territory
            'country'  # Country level
        ]
        return place_type in state_level_types
    
    def extract_state_from_address(self, formatted_address: str) -> Optional[str]:
        """
        Extract state name from formatted address.
        Example: "Castle Hill NSW 2154, Australia" → "New South Wales"
        
        Returns:
            Full state name (e.g., "New South Wales", "Victoria")
            or None if not found
        """
        state_abbreviations = {
            'NSW': 'New South Wales',
            'VIC': 'Victoria',
            'QLD': 'Queensland',
            'SA': 'South Australia',
            'WA': 'Western Australia',
            'TAS': 'Tasmania',
            'NT': 'Northern Territory',
            'ACT': 'Australian Capital Territory'
        }
        
        # Check for state abbreviations
        for abbrev, full_name in state_abbreviations.items():
            if abbrev in formatted_address or full_name in formatted_address:
                return full_name
        
        return None
    
    def get_bounding_box(self, geocoded_result: Dict) -> Optional[Dict]:
        """
        Extract bounding box from geocoded result.
        Useful for more precise area searches.
        
        Returns:
            Dictionary with north, south, east, west coordinates
            or None if no bounds available
        """
        if not geocoded_result:
            return None
        
        bounds = geocoded_result.get('bounds') or geocoded_result.get('viewport')
        if not bounds:
            return None
        
        return {
            'north': bounds['northeast']['lat'],
            'south': bounds['southwest']['lat'],
            'east': bounds['northeast']['lng'],
            'west': bounds['southwest']['lng']
        }