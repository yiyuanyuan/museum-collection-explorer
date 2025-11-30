import requests
from typing import Dict, List, Optional, Union
from config import Config
import sys
from urllib.parse import quote

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
                          radius: Optional[float] = None,
                          show_only_with_images: bool = True) -> Dict:
        """
        Enhanced search occurrences with support for comprehensive filtering
        """
        print(f"[BiocacheService] search_occurrences called with:")
        print(f"[BiocacheService]   show_only_with_images={show_only_with_images}")
        print(f"[BiocacheService]   lat={lat}, lon={lon}, radius={radius}")
        print(f"[BiocacheService]   filters={filters}")
        sys.stdout.flush()
        
        fq = []
        fq.append(f'dataResourceUid:"{self.dataset_id}"')
        
        if bounds:
            fq.append(f'decimalLatitude:[{bounds["south"]} TO {bounds["north"]}]')
            fq.append(f'decimalLongitude:[{bounds["west"]} TO {bounds["east"]}]')
            print(f"[BiocacheService] Searching with bounds: lat [{bounds['south']} TO {bounds['north']}], lon [{bounds['west']} TO {bounds['east']}]")
        
        if filters:
            # Scientific name - determine taxonomic rank
            if filters.get('scientific_name'):
                scientific_name = filters['scientific_name']
                scientific_name = scientific_name.strip()
                scientific_name = ' '.join(scientific_name.split())
                
                import re
                scientific_name = re.sub(r'\([^)]*\)', '', scientific_name).strip()
                scientific_name = ' '.join(scientific_name.split())
                
                rank = self.determine_taxonomic_rank(scientific_name)
                
                parts = scientific_name.split()
                if len(parts) >= 2 and len(parts[0]) > 0 and len(parts[1]) > 0:
                    if parts[0][0].isupper() and parts[1][0].islower():
                        rank = 'species'
                        print(f"[BiocacheService] FORCED to species rank for binomial: {scientific_name}")
                
                if rank == 'species':
                    fq.append(f'species:"{scientific_name}"')
                    print(f"[BiocacheService] Using species field for: {scientific_name}")
                elif rank == 'genus':
                    genus_name = scientific_name.split()[0] if ' ' in scientific_name else scientific_name
                    fq.append(f'genus:"{genus_name}"')
                    print(f"[BiocacheService] Using genus field for: {genus_name}")
                elif rank == 'family':
                    fq.append(f'family:"{scientific_name}"')
                    print(f"[BiocacheService] Using family field for: {scientific_name}")
                else:
                    fq.append(f'(order:"{scientific_name}" OR class:"{scientific_name}" OR phylum:"{scientific_name}" OR kingdom:"{scientific_name}")')
                    print(f"[BiocacheService] Using higher taxonomy search for: {scientific_name}")
            
            # Common name - WILDCARD search for partial matching
            elif filters.get('common_name'):
                common_name = filters['common_name']
                escaped_name = common_name.replace('"', '\\"')
                fq.append(f'vernacularName:*{escaped_name}*')
                print(f"[BiocacheService] Using vernacularName WILDCARD for: *{common_name}*")
            
            # Higher taxonomy filters (from dynamic resolution)
            if filters.get('class'):
                fq.append(f'class:"{filters["class"]}"')
                print(f"[BiocacheService] Using class field for: {filters['class']}")
            
            if filters.get('order'):
                fq.append(f'order:"{filters["order"]}"')
                print(f"[BiocacheService] Using order field for: {filters['order']}")
            
            if filters.get('family') and not filters.get('scientific_name'):
                fq.append(f'family:"{filters["family"]}"')
                print(f"[BiocacheService] Using family field for: {filters['family']}")
            
            if filters.get('genus') and not filters.get('scientific_name'):
                fq.append(f'genus:"{filters["genus"]}"')
                print(f"[BiocacheService] Using genus field for: {filters['genus']}")
            
            if filters.get('phylum'):
                fq.append(f'phylum:"{filters["phylum"]}"')
                print(f"[BiocacheService] Using phylum field for: {filters['phylum']}")
            
            if filters.get('kingdom'):
                fq.append(f'kingdom:"{filters["kingdom"]}"')
                print(f"[BiocacheService] Using kingdom field for: {filters['kingdom']}")
            
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
            
            if filters.get('institution'):
                fq.append(f'institutionName:"{filters["institution"]}"')
            
            if filters.get('has_image'):
                fq.append('multimedia:Image')
        
        q = '*:*'
        if filters and filters.get('free_text_search'):
            q = filters['free_text_search']
        
        params = {
            'q': q,
            'fq': fq,
            'pageSize': page_size,
            'start': page * page_size,
            'facets': 'collectionName,stateProvince,year,family,order,class,institutionName,genus',
            'flimit': 1000,
            'sort': 'score',
            'dir': 'desc'
        }
        
        if lat is not None and lon is not None:
            params['lat'] = lat
            params['lon'] = lon
            if radius is not None:
                params['radius'] = radius
            print(f"[BiocacheService] ✓ Added spatial params: lat={lat}, lon={lon}, radius={radius}")
        else:
            print(f"[BiocacheService] ⚠ No spatial params added")
        
        print(f"[BiocacheService] Query filters: {fq}")
        print(f"[BiocacheService] API params keys: {list(params.keys())}")
        
        response = requests.get(f"{self.base_url}/occurrences/search", params=params, timeout=60)
        response.raise_for_status()
        data = response.json()
        
        processed_occurrences = []
        for occ in data.get('occurrences', []):
            processed = self._process_occurrence(occ)
            if self._should_include_occurrence(processed, bounds, show_only_with_images):
                processed_occurrences.append(processed)
        
        total = data.get('totalRecords', 0)
        print(f"[BiocacheService] Query result: {total} total records, returning {len(processed_occurrences)} records")
        
        print(f"[BiocacheService] About to build URL with filters: {filters}")
        ala_url = self.build_ala_url(filters=filters, bounds=bounds)
        
        return {
            'totalRecords': total,
            'occurrences': processed_occurrences,
            'facets': self._process_facets(data.get('facetResults', [])),
            'ala_url': ala_url
        }
    
    def determine_taxonomic_rank(self, name: str) -> str:
        """Determine the taxonomic rank of a scientific name."""
        import re
        
        name = name.strip()
        name = re.sub(r'\([^)]*\)', '', name).strip()
        name = ' '.join(name.split())
        
        print(f"[BiocacheService] determine_taxonomic_rank input (after cleaning): '{name}'")
        
        parts = name.split()
        print(f"[BiocacheService] Parts: {parts}, Length: {len(parts)}")
        
        if self._is_higher_taxon(name):
            if name.lower().endswith('idae') or name.lower().endswith('inae'):
                print(f"[BiocacheService] Detected as FAMILY (suffix)")
                return 'family'
            print(f"[BiocacheService] Detected as HIGHER taxon")
            return 'higher'
        
        if len(parts) >= 2:
            if parts[0][0].isupper() and parts[1][0].islower():
                print(f"[BiocacheService] Detected as SPECIES (binomial pattern)")
                return 'species'
        
        if len(parts) == 1 and parts[0][0].isupper():
            print(f"[BiocacheService] Detected as GENUS (single word)")
            return 'genus'
        
        print(f"[BiocacheService] Defaulting to GENUS")
        return 'genus'
    
    def build_ala_url(self, filters: Optional[Dict] = None, bounds: Optional[Dict] = None) -> str:
        """Build a URL to the ALA Biocache occurrence search page"""
        base = "https://biocache.ala.org.au/occurrences/search?q=*:*"
        params = []
        
        params.append(f'fq=dataResourceUid:%22{self.dataset_id}%22')
        
        if filters:
            if filters.get('scientific_name'):
                scientific_name = filters['scientific_name']
                
                import re
                scientific_name = scientific_name.strip()
                scientific_name = ' '.join(scientific_name.split())
                scientific_name = re.sub(r'\([^)]*\)', '', scientific_name).strip()
                scientific_name = ' '.join(scientific_name.split())
                
                rank = self.determine_taxonomic_rank(scientific_name)
                print(f"[BiocacheService] build_ala_url: scientific_name='{scientific_name}', taxonomic rank = {rank}")
                
                parts = scientific_name.split()
                if len(parts) >= 2 and len(parts[0]) > 0 and len(parts[1]) > 0:
                    if parts[0][0].isupper() and parts[1][0].islower():
                        rank = 'species'
                
                encoded_name = quote(scientific_name, safe='')
                
                if rank == 'species':
                    print(f"[BiocacheService] build_ala_url: Using species: for {scientific_name}")
                    params.append(f'fq=species:%22{encoded_name}%22')
                elif rank == 'genus':
                    genus_name = scientific_name.split()[0] if ' ' in scientific_name else scientific_name
                    encoded_genus = quote(genus_name, safe='')
                    print(f"[BiocacheService] build_ala_url: Using genus: for {genus_name}")
                    params.append(f'fq=genus:%22{encoded_genus}%22')
                elif rank == 'family':
                    print(f"[BiocacheService] build_ala_url: Using family: for {scientific_name}")
                    params.append(f'fq=family:%22{encoded_name}%22')
                else:
                    print(f"[BiocacheService] build_ala_url: Using scientificName: for {scientific_name}")
                    params.append(f'fq=scientificName:%22{encoded_name}%22')
            
            elif filters.get('common_name'):
                encoded_common = quote(filters["common_name"], safe='')
                params.append(f'fq=vernacularName:*{encoded_common}*')
            
            # Higher taxonomy filters
            if filters.get('class'):
                encoded_class = quote(filters["class"], safe='')
                params.append(f'fq=class:%22{encoded_class}%22')
            
            if filters.get('order'):
                encoded_order = quote(filters["order"], safe='')
                params.append(f'fq=order:%22{encoded_order}%22')
            
            if filters.get('family') and not filters.get('scientific_name'):
                encoded_family = quote(filters["family"], safe='')
                params.append(f'fq=family:%22{encoded_family}%22')
            
            if filters.get('genus') and not filters.get('scientific_name'):
                encoded_genus = quote(filters["genus"], safe='')
                params.append(f'fq=genus:%22{encoded_genus}%22')
            
            if filters.get('phylum'):
                encoded_phylum = quote(filters["phylum"], safe='')
                params.append(f'fq=phylum:%22{encoded_phylum}%22')
            
            if filters.get('kingdom'):
                encoded_kingdom = quote(filters["kingdom"], safe='')
                params.append(f'fq=kingdom:%22{encoded_kingdom}%22')
            
            if filters.get('state_province'):
                encoded_state = quote(filters["state_province"], safe='')
                params.append(f'fq=stateProvince:%22{encoded_state}%22')
            
            if filters.get('locality'):
                encoded_locality = quote(filters["locality"], safe='')
                params.append(f'fq=locality:%22{encoded_locality}%22')
            
            if filters.get('year'):
                params.append(f'fq=year:{filters["year"]}')
            
            if filters.get('year_range'):
                params.append(f'fq=year:{filters["year_range"]}')
            
            if filters.get('month'):
                params.append(f'fq=month:{filters["month"]}')
            
            if filters.get('catalog_number'):
                encoded_catalog = quote(filters["catalog_number"], safe='')
                params.append(f'fq=catalogNumber:%22{encoded_catalog}%22')
            
            if filters.get('recorded_by'):
                encoded_recorded = quote(filters["recorded_by"], safe='')
                params.append(f'fq=recordedBy:%22{encoded_recorded}%22')
            
            if filters.get('identified_by'):
                encoded_identified = quote(filters["identified_by"], safe='')
                params.append(f'fq=identifiedBy:%22{encoded_identified}%22')
            
            if filters.get('collection_name'):
                encoded_collection = quote(filters["collection_name"], safe='')
                params.append(f'fq=collectionName:%22{encoded_collection}%22')
            
            if filters.get('institution'):
                encoded_institution = quote(filters["institution"], safe='')
                params.append(f'fq=institutionName:%22{encoded_institution}%22')
            
            if filters.get('has_image'):
                params.append('fq=multimedia:Image')
        
        if bounds:
            params.append(f'fq=decimalLatitude:[{bounds["south"]}%20TO%20{bounds["north"]}]')
            params.append(f'fq=decimalLongitude:[{bounds["west"]}%20TO%20{bounds["east"]}]')
        
        return base + "&" + "&".join(params)
    
    def _is_species_name(self, name: str) -> bool:
        parts = name.strip().split()
        if len(parts) >= 2:
            if parts[0][0].isupper() and parts[1][0].islower():
                return True
        return False
    
    def _is_higher_taxon(self, name: str) -> bool:
        higher_taxon_suffixes = [
            'idae', 'inae', 'ini', 'ales', 'iformes', 'oidea', 'acea', 'phyta', 'mycota'
        ]
        name_lower = name.lower()
        return any(name_lower.endswith(suffix) for suffix in higher_taxon_suffixes)
    
    def _should_include_occurrence(self, occurrence: Dict, bounds: Optional[Dict], show_only_with_images: bool = True) -> bool:
        lat = occurrence.get('latitude')
        lon = occurrence.get('longitude')
        if lat is None or lon is None:
            return False
        
        if bounds:
            if not (bounds['south'] <= lat <= bounds['north'] and bounds['west'] <= lon <= bounds['east']):
                return False
        
        if show_only_with_images:
            has_image = (
                occurrence.get('imageUrl') or 
                occurrence.get('largeImageUrl') or 
                occurrence.get('thumbnailUrl') or 
                (occurrence.get('images') and len(occurrence.get('images', [])) > 0)
            )
            
            if not hasattr(self, '_debug_count'):
                self._debug_count = 0
            if self._debug_count < 3:
                print(f"[BiocacheService] Specimen {occurrence.get('id')}: has_image={has_image}")
                self._debug_count += 1
            
            if not has_image:
                return False
        else:
            if not hasattr(self, '_debug_no_filter_logged'):
                print(f"[BiocacheService] NOT filtering by images")
                self._debug_no_filter_logged = True
        
        return True
    
    def _process_occurrence(self, occ: Dict) -> Dict:
        return {
            'id': occ.get('uuid'),
            'latitude': occ.get('decimalLatitude'),
            'longitude': occ.get('decimalLongitude'),
            'scientificName': occ.get('scientificName'),
            'commonName': occ.get('vernacularName', ''),
            'catalogNumber': occ.get('raw_catalogNumber', occ.get('catalogNumber')),
            'collectionName': occ.get('collectionName'),
            'eventDate': occ.get('eventDate'),
            'locality': occ.get('locality'),
            'stateProvince': occ.get('stateProvince'),
            'institutionName': occ.get('institutionName'),
            'year': occ.get('year'),
            'month': occ.get('month'),
            'day': occ.get('day'),
            'kingdom': occ.get('kingdom'),
            'phylum': occ.get('phylum'),
            'class': occ.get('class'),
            'order': occ.get('order'),
            'family': occ.get('family'),
            'genus': occ.get('genus'),
            'species': occ.get('species'),
            'recordedBy': occ.get('recordedBy'),
            'identifiedBy': occ.get('identifiedBy'),
            'coordinateUncertaintyInMeters': occ.get('coordinateUncertaintyInMeters'),
            'dataGeneralizations': occ.get('dataGeneralizations'),
            'imageUrl': occ.get('imageUrl'),
            'largeImageUrl': occ.get('largeImageUrl'),
            'thumbnailUrl': occ.get('thumbnailUrl'),
            'images': occ.get('images', [])
        }
    
    def _process_facets(self, facet_results: List) -> Dict:
        facets = {}
        
        field_map = {
            'collectionName': 'collection_name',
            'stateProvince': 'state_province',
            'year': 'year',
            'family': 'family',
            'order': 'order',
            'class': 'class',
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
                    {'value': item.get('label'), 'count': item.get('count')}
                    for item in facet.get('fieldResult', [])
                    if item.get('label')
                ]
        
        return facets
    
    def get_statistics(self) -> Dict:
        params = {
            'q': '*:*',
            'fq': f'dataResourceUid:"{self.dataset_id}"',
            'facets': 'collectionName,stateProvince,class,order,family',
            'flimit': 100,
            'pageSize': 0
        }
        
        response = requests.get(f"{self.base_url}/occurrences/search", params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        return {
            'totalRecords': data.get('totalRecords', 0),
            'facets': self._process_facets(data.get('facetResults', []))
        }