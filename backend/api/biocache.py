import requests
from typing import Dict, List, Optional, Union
from config import Config

class BiocacheService:
    def __init__(self):
        self.base_url = Config.BIOCACHE_BASE_URL
        self.dataset_id = Config.DATASET_ID
    
    def search_occurrences(self, 
                          filters: Optional[Dict] = None, 
                          page: int = 0, 
                          page_size: int = 500,
                          bounds: Optional[Dict] = None,
                          lat: Optional[float] = None,
                          lon: Optional[float] = None,
                          radius: Optional[float] = None) -> Dict:
        """
        Enhanced search occurrences with support for function calling parameters
        """
        # Build filter query array
        fq = []
        
        # Add dataset filter
        fq.append(f'dataResourceUid:"{self.dataset_id}"')
        
        # # Add image filter if requested
        # if filters and filters.get('has_image'):
        fq.append('multimedia:Image')
        
        # Add viewport bounds if provided
        if bounds:
            fq.append(f'decimalLatitude:[{bounds["south"]} TO {bounds["north"]}]')
            fq.append(f'decimalLongitude:[{bounds["west"]} TO {bounds["east"]}]')
            print(f"Searching with bounds: lat [{bounds['south']} TO {bounds['north']}], lon [{bounds['west']} TO {bounds['east']}]")
        
        # Add user filters
        if filters:
            # Scientific name - handle different taxonomic levels
            if filters.get('scientific_name'):
                scientific_name = filters['scientific_name']
                # Build a comprehensive query for taxonomic names
                taxonomic_query_parts = []
                
                # Check if it's likely a higher taxon
                if self._is_higher_taxon(scientific_name):
                    # Search in multiple taxonomic fields
                    taxonomic_query_parts.extend([
                        f'family:"{scientific_name}"',
                        f'order:"{scientific_name}"',
                        f'class:"{scientific_name}"',
                        f'phylum:"{scientific_name}"',
                        f'kingdom:"{scientific_name}"'
                    ])
                
                # Always include scientific name and genus
                taxonomic_query_parts.extend([
                    f'scientificName:"{scientific_name}"',
                    f'genus:"{scientific_name}"',
                    f'species:"{scientific_name}"',
                    f'raw_scientificName:"{scientific_name}"'
                ])
                
                # Combine with OR logic
                fq.append(f'({" OR ".join(taxonomic_query_parts)})')
                print(f"Searching for scientific name: {scientific_name}")
            
            # Common name search
            if filters.get('common_name'):
                common_name = filters['common_name']
                fq.append(f'(vernacularName:"{common_name}" OR raw_vernacularName:"{common_name}")')
                print(f"Searching for common name: {common_name}")
            
            # Collection name
            if filters.get('collection_name'):
                fq.append(f'collectionName:"{filters["collection_name"]}"')
            
            # State/Province
            if filters.get('state_province'):
                fq.append(f'stateProvince:"{filters["state_province"]}"')
            
            # Single year
            if filters.get('year'):
                fq.append(f'year:{filters["year"]}')
            
            # Year range
            if filters.get('year_range'):
                # Expected format: "[2020 TO 2023]"
                fq.append(f'year:{filters["year_range"]}')
            
            # Basis of record
            if filters.get('basis_of_record'):
                fq.append(f'basisOfRecord:"{filters["basis_of_record"]}"')
            
            # Institution
            if filters.get('institution'):
                fq.append(f'institutionName:"{filters["institution"]}"')
        
        # Build the main query
        q = '*:*'  # Query everything, use filters for constraints
        
        # If searching by common name or text, also use q parameter
        if filters and filters.get('free_text_search'):
            q = filters['free_text_search']
        
        # Build params with all filters
        params = {
            'q': q,
            'fq': fq,
            'pageSize': page_size,
            'start': page * page_size,
            'facets': 'collectionName,stateProvince,year,family,order,class,basisOfRecord',
            'flimit': 1000,
            'sort': 'score',  # Sort by relevance
            'dir': 'desc'
        }
        
        # Add spatial query parameters if provided
        if lat is not None and lon is not None:
            params['lat'] = lat
            params['lon'] = lon
            if radius is not None:
                params['radius'] = radius
        
        print(f"Query parameters: q={params['q']}, filters={params['fq']}")
        
        try:
            response = requests.get(f"{self.base_url}/occurrences/search", params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            # Process occurrences
            processed_occurrences = []
            for occ in data.get('occurrences', []):
                processed = self._process_occurrence(occ)
                # Apply any additional filtering if needed
                if self._should_include_occurrence(processed, bounds):
                    processed_occurrences.append(processed)
            
            total_records = data.get('totalRecords', 0)
            print(f"Query result: {total_records} total records, returning {len(processed_occurrences)} records")
            
            return {
                'occurrences': processed_occurrences,
                'totalRecords': total_records,
                'facets': self._process_facets(data.get('facetResults', []))
            }
            
        except Exception as e:
            print(f"Error fetching occurrences: {str(e)}")
            return {'occurrences': [], 'totalRecords': 0, 'facets': {}}
    
    def get_statistics(self, filters: Optional[Dict] = None) -> Dict:
        """
        Get statistics about the dataset with optional filters
        """
        # Use search with page_size=0 to just get facets and counts
        results = self.search_occurrences(
            filters=filters,
            page=0,
            page_size=0
        )
        
        return {
            'totalRecords': results.get('totalRecords', 0),
            'facets': results.get('facets', {})
        }
    
    def search_by_taxon(self, taxon_name: str, rank: Optional[str] = None) -> Dict:
        """
        Search by taxonomic name at any rank
        """
        filters = {'scientific_name': taxon_name}
        return self.search_occurrences(filters=filters)
    
    def search_by_location(self, 
                           state: Optional[str] = None,
                           bounds: Optional[Dict] = None,
                           radius_search: Optional[Dict] = None) -> Dict:
        """
        Search by geographic location
        """
        filters = {}
        if state:
            filters['state_province'] = state
        
        if radius_search:
            return self.search_occurrences(
                filters=filters,
                lat=radius_search.get('lat'),
                lon=radius_search.get('lon'),
                radius=radius_search.get('radius', 5)
            )
        
        return self.search_occurrences(filters=filters, bounds=bounds)
    
    def search_by_time(self,
                       year: Optional[int] = None,
                       start_year: Optional[int] = None,
                       end_year: Optional[int] = None) -> Dict:
        """
        Search by temporal parameters
        """
        filters = {}
        
        if year:
            filters['year'] = year
        elif start_year and end_year:
            filters['year_range'] = f"[{start_year} TO {end_year}]"
        
        return self.search_occurrences(filters=filters)
    
    def _is_higher_taxon(self, name: str) -> bool:
        """
        Check if a name is likely a higher taxonomic rank
        """
        # Common suffixes for higher taxa
        higher_taxon_suffixes = [
            'idae',  # Family
            'inae',  # Subfamily
            'ini',   # Tribe
            'ales',  # Order
            'iformes',  # Order (fish, birds)
            'oidea',  # Superfamily
            'acea',   # Various ranks
            'phyta',  # Division (plants)
            'mycota'  # Division (fungi)
        ]
        
        name_lower = name.lower()
        return any(name_lower.endswith(suffix) for suffix in higher_taxon_suffixes)
    
    def _should_include_occurrence(self, occurrence: Dict, bounds: Optional[Dict]) -> bool:
        """
        Additional filtering logic for occurrences
        """
        # If bounds are specified, double-check the occurrence is within them
        if bounds:
            lat = occurrence.get('latitude')
            lon = occurrence.get('longitude')
            if lat is None or lon is None:
                return False
            
            if not (bounds['south'] <= lat <= bounds['north'] and
                    bounds['west'] <= lon <= bounds['east']):
                return False
        
        return True
    
    def _process_occurrence(self, occ: Dict) -> Dict:
        """Enhanced processing of occurrence records"""
        return {
            'id': occ.get('uuid'),
            'latitude': occ.get('decimalLatitude'),
            'longitude': occ.get('decimalLongitude'),
            'scientificName': occ.get('scientificName'),
            'commonName': occ.get('vernacularName', ''),
            'catalogNumber': occ.get('raw_catalogNumber', occ.get('catalogNumber')),
            'collectionName': occ.get('collectionName'),
            'basisOfRecord': occ.get('basisOfRecord'),
            'eventDate': occ.get('eventDate'),
            'locality': occ.get('locality'),
            'stateProvince': occ.get('stateProvince'),
            'institutionName': occ.get('institutionName'),
            'year': occ.get('year'),
            'month': occ.get('month'),
            'day': occ.get('day'),
            # Taxonomic hierarchy
            'kingdom': occ.get('kingdom'),
            'phylum': occ.get('phylum'),
            'class': occ.get('class'),
            'order': occ.get('order'),
            'family': occ.get('family'),
            'genus': occ.get('genus'),
            'species': occ.get('species'),
            # Additional fields
            'recordedBy': occ.get('recordedBy'),
            'identifiedBy': occ.get('identifiedBy'),
            'coordinateUncertaintyInMeters': occ.get('coordinateUncertaintyInMeters'),
            'dataGeneralizations': occ.get('dataGeneralizations'),
            # Image URLs
            'imageUrl': occ.get('imageUrl'),
            'largeImageUrl': occ.get('largeImageUrl'),
            'thumbnailUrl': occ.get('thumbnailUrl'),
            'images': occ.get('images', [])  # Array of all images if multiple
        }
    
    def _process_facets(self, facet_results: List) -> Dict:
        """
        Enhanced facet processing with more field mappings
        """
        facets = {}
        
        # Extended field mapping
        field_map = {
            'collectionName': 'collection_name',
            'stateProvince': 'state_province',
            'year': 'year',
            'family': 'family',
            'order': 'order',
            'class': 'class',
            'basisOfRecord': 'basis_of_record',
            'institutionName': 'institution',
            'kingdom': 'kingdom',
            'phylum': 'phylum',
            'genus': 'genus'
        }
        
        for facet in facet_results:
            field_name = facet.get('fieldName')
            
            if field_name in field_map:
                mapped_name = field_map[field_name]
                facets[mapped_name] = [
                    {
                        'value': item.get('label'),
                        'count': item.get('count')
                    }
                    for item in facet.get('fieldResult', [])
                    if item.get('label')  # Only include non-null labels
                ]
        
        return facets