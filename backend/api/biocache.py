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
        Enhanced search occurrences with support for comprehensive filtering
        """
        # Build filter query array
        fq = []
        
        # Add dataset filter
        fq.append(f'dataResourceUid:"{self.dataset_id}"')
        
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
                taxonomic_query_parts = []
                
                if self._is_higher_taxon(scientific_name):
                    taxonomic_query_parts.extend([
                        f'family:"{scientific_name}"',
                        f'order:"{scientific_name}"',
                        f'class:"{scientific_name}"',
                        f'phylum:"{scientific_name}"',
                        f'kingdom:"{scientific_name}"'
                    ])
                
                taxonomic_query_parts.extend([
                    f'scientificName:"{scientific_name}"',
                    f'genus:"{scientific_name}"',
                    f'species:"{scientific_name}"',
                    f'raw_scientificName:"{scientific_name}"'
                ])
                
                fq.append(f'({" OR ".join(taxonomic_query_parts)})')
                print(f"Searching for scientific name: {scientific_name}")
            
            # Common name search
            if filters.get('common_name'):
                common_name = filters['common_name']
                fq.append(f'(vernacularName:"{common_name}" OR raw_vernacularName:"{common_name}")')
                print(f"Searching for common name: {common_name}")
            
            # Geographic filters
            if filters.get('state_province'):
                fq.append(f'stateProvince:"{filters["state_province"]}"')
            
            if filters.get('locality'):
                fq.append(f'locality:"{filters["locality"]}"')
            
            # Temporal filters
            if filters.get('year'):
                fq.append(f'year:{filters["year"]}')
            
            if filters.get('year_range'):
                fq.append(f'year:{filters["year_range"]}')
            
            if filters.get('month'):
                fq.append(f'month:{filters["month"]}')
            
            if filters.get('day'):
                fq.append(f'day:{filters["day"]}')
            
            # Specimen identification
            if filters.get('catalog_number'):
                fq.append(f'(catalogNumber:"{filters["catalog_number"]}" OR raw_catalogNumber:"{filters["catalog_number"]}")')
            
            if filters.get('recorded_by'):
                fq.append(f'recordedBy:"{filters["recorded_by"]}"')
            
            if filters.get('identified_by'):
                fq.append(f'identifiedBy:"{filters["identified_by"]}"')
            
            # Collection filters
            if filters.get('collection_name'):
                fq.append(f'collectionName:"{filters["collection_name"]}"')
            
            if filters.get('basis_of_record'):
                fq.append(f'basisOfRecord:"{filters["basis_of_record"]}"')
            
            if filters.get('institution'):
                fq.append(f'institutionName:"{filters["institution"]}"')
            
            # Image filter (only if explicitly requested)
            if filters.get('has_image'):
                fq.append('multimedia:Image')
        
        # Build the main query
        q = '*:*'
        
        # If free text search provided, use it as main query
        if filters and filters.get('free_text_search'):
            q = filters['free_text_search']
        
        # Build params with all filters
        params = {
            'q': q,
            'fq': fq,
            'pageSize': page_size,
            'start': page * page_size,
            'facets': 'collectionName,stateProvince,year,family,order,class,basisOfRecord,institutionName,genus',
            'flimit': 1000,
            'sort': 'score',
            'dir': 'desc'
        }
        
        # Add spatial query parameters if provided
        if lat is not None and lon is not None:
            params['lat'] = lat
            params['lon'] = lon
            if radius is not None:
                params['radius'] = radius
        
        print(f"Query parameters: q={params['q']}, filters={params['fq']}")
        
        response = requests.get(f"{self.base_url}/occurrences/search", params=params, timeout=60)
        response.raise_for_status()
        data = response.json()
        
        # Process occurrences
        processed_occurrences = []
        for occ in data.get('occurrences', []):
            processed = self._process_occurrence(occ)
            if self._should_include_occurrence(processed, bounds):
                processed_occurrences.append(processed)
        
        total_records = data.get('totalRecords', 0)
        print(f"Query result: {total_records} total records, returning {len(processed_occurrences)} records")
        
        # Build the ALA URL for user reference
        ala_url = self.build_ala_url(filters, bounds)
        
        return {
            'occurrences': processed_occurrences,
            'totalRecords': total_records,
            'facets': self._process_facets(data.get('facetResults', [])),
            'ala_url': ala_url
        }
    
    def get_statistics(self, filters: Optional[Dict] = None) -> Dict:
        """Get statistics about the dataset with optional filters"""
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
        """Search by taxonomic name at any rank"""
        filters = {'scientific_name': taxon_name}
        return self.search_occurrences(filters=filters)
    
    def search_by_location(self, 
                           state: Optional[str] = None,
                           bounds: Optional[Dict] = None,
                           radius_search: Optional[Dict] = None) -> Dict:
        """Search by geographic location"""
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
        """Search by temporal parameters"""
        filters = {}
        
        if year:
            filters['year'] = year
        elif start_year and end_year:
            filters['year_range'] = f"[{start_year} TO {end_year}]"
        
        return self.search_occurrences(filters=filters)
    
    def build_ala_url(self, filters: Optional[Dict] = None, bounds: Optional[Dict] = None) -> str:
        """Build a valid ALA search URL - uses URL-encoded format that ALA expects"""
        base = "https://biocache.ala.org.au/occurrences/search?q=*:*"
        # Use %22 for quotes (URL encoded) and camelCase field names
        params = [f"fq=dataResourceUid:%22{self.dataset_id}%22"]
        
        if filters:
            # Scientific name - check if higher taxon
            if filters.get('scientific_name'):
                name = filters['scientific_name']
                if self._is_higher_taxon(name):
                    params.append(f'fq=family:%22{name}%22')
                else:
                    params.append(f'fq=genus:%22{name}%22')
            
            # Common name
            if filters.get('common_name'):
                params.append(f'fq=vernacularName:%22{filters["common_name"]}%22')
            
            # Geographic
            if filters.get('state_province'):
                params.append(f'fq=stateProvince:%22{filters["state_province"]}%22')
            
            if filters.get('locality'):
                params.append(f'fq=locality:%22{filters["locality"]}%22')
            
            # Temporal
            if filters.get('year'):
                params.append(f'fq=year:%22{filters["year"]}%22')
            
            if filters.get('year_range'):
                # Year ranges don't use quotes, just brackets
                year_range = filters['year_range'].replace(' ', '%20')
                params.append(f'fq=year:{year_range}')
            
            if filters.get('month'):
                params.append(f'fq=month:{filters["month"]}')
            
            # Specimen details
            if filters.get('catalog_number'):
                params.append(f'fq=catalogNumber:%22{filters["catalog_number"]}%22')
            
            if filters.get('recorded_by'):
                params.append(f'fq=recordedBy:%22{filters["recorded_by"]}%22')
            
            if filters.get('identified_by'):
                params.append(f'fq=identifiedBy:%22{filters["identified_by"]}%22')
            
            # Collection
            if filters.get('collection_name'):
                params.append(f'fq=collectionName:%22{filters["collection_name"]}%22')
            
            if filters.get('institution'):
                params.append(f'fq=institutionName:%22{filters["institution"]}%22')
            
            if filters.get('basis_of_record'):
                params.append(f'fq=basisOfRecord:%22{filters["basis_of_record"]}%22')
            
            # Images
            if filters.get('has_image'):
                params.append('fq=multimedia:Image')
        
        # Add bounds if provided
        if bounds:
            params.append(f'fq=decimalLatitude:[{bounds["south"]}%20TO%20{bounds["north"]}]')
            params.append(f'fq=decimalLongitude:[{bounds["west"]}%20TO%20{bounds["east"]}]')
        
        return base + "&" + "&".join(params)
    
    def _is_higher_taxon(self, name: str) -> bool:
        """Check if a name is likely a higher taxonomic rank"""
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
        """Additional filtering logic for occurrences"""
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
        """Enhanced processing of occurrence records with all fields"""
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
            # People
            'recordedBy': occ.get('recordedBy'),
            'identifiedBy': occ.get('identifiedBy'),
            # Spatial precision
            'coordinateUncertaintyInMeters': occ.get('coordinateUncertaintyInMeters'),
            'dataGeneralizations': occ.get('dataGeneralizations'),
            # Image URLs - all quality levels
            'imageUrl': occ.get('imageUrl'),  # Medium quality
            'largeImageUrl': occ.get('largeImageUrl'),  # High quality
            'thumbnailUrl': occ.get('thumbnailUrl'),  # Thumbnail
            'images': occ.get('images', [])  # Array of all images
        }
    
    def _process_facets(self, facet_results: List) -> Dict:
        """Enhanced facet processing with comprehensive field mappings"""
        facets = {}
        
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
                    if item.get('label')
                ]
        
        return facets