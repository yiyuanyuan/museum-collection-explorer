import requests
from typing import Dict, List, Optional, Union
from config import Config
import sys

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
        Uses EXACTLY what the user asks for - no fallback logic here
        Fallback logic is handled by ChatbotService
        """
        # DEBUG: Log the image filter parameter
        print(f"[BiocacheService] search_occurrences called with show_only_with_images={show_only_with_images}")
        sys.stdout.flush()
        
        # Build filter query array
        fq = []
        
        # Add dataset filter
        fq.append(f'dataResourceUid:"{self.dataset_id}"')
        
        # Add viewport bounds if provided
        if bounds:
            fq.append(f'decimalLatitude:[{bounds["south"]} TO {bounds["north"]}]')
            fq.append(f'decimalLongitude:[{bounds["west"]} TO {bounds["east"]}]')
            print(f"[BiocacheService] Searching with bounds: lat [{bounds['south']} TO {bounds['north']}], lon [{bounds['west']} TO {bounds['east']}]")
        
        # Add user filters
        if filters:
            # RULE 2: Scientific name - determine the taxonomic rank and use appropriate field
            if filters.get('scientific_name'):
                scientific_name = filters['scientific_name']
                
                # CRITICAL: Clean and normalize the name
                scientific_name = scientific_name.strip()
                scientific_name = ' '.join(scientific_name.split())
                
                # Remove subgenus/author info in parentheses
                # e.g., "Rhipidura (Rhipidura) fuliginosa" -> "Rhipidura fuliginosa"
                import re
                scientific_name = re.sub(r'\([^)]*\)', '', scientific_name).strip()
                scientific_name = ' '.join(scientific_name.split())
                
                rank = self.determine_taxonomic_rank(scientific_name)
                
                # DEFENSIVE CHECK: If name has 2+ words with capital+lowercase pattern, FORCE it to be species
                parts = scientific_name.split()
                if len(parts) >= 2 and len(parts[0]) > 0 and len(parts[1]) > 0:
                    if parts[0][0].isupper() and parts[1][0].islower():
                        rank = 'species'
                        print(f"[BiocacheService] FORCED to species rank for binomial: {scientific_name}")
                
                if rank == 'species':
                    # Use species field for binomial names
                    fq.append(f'species:"{scientific_name}"')
                    print(f"[BiocacheService] Using species field for: {scientific_name}")
                elif rank == 'genus':
                    # Extract just the genus name (first word) for genus queries
                    genus_name = scientific_name.split()[0] if ' ' in scientific_name else scientific_name
                    fq.append(f'genus:"{genus_name}"')
                    print(f"[BiocacheService] Using genus field for: {genus_name}")
                elif rank == 'family':
                    # Use family field for family names
                    fq.append(f'family:"{scientific_name}"')
                    print(f"[BiocacheService] Using family field for: {scientific_name}")
                else:
                    # Fallback for other ranks (order, class, phylum, kingdom)
                    # Try multiple fields in case the rank is ambiguous
                    fq.append(f'(order:"{scientific_name}" OR class:"{scientific_name}" OR phylum:"{scientific_name}" OR kingdom:"{scientific_name}")')
                    print(f"[BiocacheService] Using higher taxonomy search for: {scientific_name}")
            
            # RULE 1: Common name search - use vernacularName field ONLY
            # RULE 4: Changed from 'if' to 'elif' to prevent both names being used simultaneously
            elif filters.get('common_name'):
                common_name = filters['common_name']
                fq.append(f'vernacularName:"{common_name}"')
                print(f"[BiocacheService] Using vernacularName field for: {common_name}")
            
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
        
        print(f"[BiocacheService] Query filters: {fq}")
        
        response = requests.get(f"{self.base_url}/occurrences/search", params=params, timeout=60)
        response.raise_for_status()
        data = response.json()
        
        # Process occurrences
        processed_occurrences = []
        for occ in data.get('occurrences', []):
            processed = self._process_occurrence(occ)
            if self._should_include_occurrence(processed, bounds, show_only_with_images):
                processed_occurrences.append(processed)
        
        total_records = data.get('totalRecords', 0)
        print(f"[BiocacheService] Query result: {total_records} total records, returning {len(processed_occurrences)} records")
        
        # DEBUG: Check filters before building URL
        print(f"[BiocacheService] About to build URL with filters: {filters}")
        sys.stdout.flush()
        
        # Build the ALA URL for user reference
        ala_url = self.build_ala_url(filters, bounds)
        
        return {
            'occurrences': processed_occurrences,
            'totalRecords': total_records,
            'facets': self._process_facets(data.get('facetResults', [])),
            'ala_url': ala_url
        }
    
    def determine_taxonomic_rank(self, name: str) -> str:
        """
        Determine the taxonomic rank of a scientific name
        Returns: 'species', 'genus', 'family', or 'higher'
        """
        name = name.strip()
        
        # Remove any extra whitespace between words
        name = ' '.join(name.split())
        
        # CRITICAL: Remove subgenus/author info in parentheses
        # e.g., "Rhipidura (Rhipidura) fuliginosa" -> "Rhipidura fuliginosa"
        import re
        name = re.sub(r'\([^)]*\)', '', name).strip()
        name = ' '.join(name.split())  # Clean up extra spaces after removal
        
        parts = name.split()
        
        print(f"[BiocacheService] determine_taxonomic_rank input (after cleaning): '{name}'")
        print(f"[BiocacheService] Parts: {parts}, Length: {len(parts)}")
        sys.stdout.flush()
        
        # Check for family and higher ranks by suffix
        if self._is_higher_taxon(name):
            print(f"[BiocacheService] Detected as FAMILY (higher taxon)")
            sys.stdout.flush()
            return 'family'
        
        # Check for binomial (species level): "Genus species" or "Genus species subspecies"
        if len(parts) >= 2:
            print(f"[BiocacheService] Has {len(parts)} parts")
            sys.stdout.flush()
            
            # Ensure both parts have content
            if len(parts[0]) > 0 and len(parts[1]) > 0:
                first_char = parts[0][0]
                second_char = parts[1][0]
                
                print(f"[BiocacheService] First part '{parts[0]}' starts with '{first_char}' (isupper={first_char.isupper()})")
                print(f"[BiocacheService] Second part '{parts[1]}' starts with '{second_char}' (islower={second_char.islower()})")
                sys.stdout.flush()
                
                if first_char.isupper() and second_char.islower():
                    print(f"[BiocacheService] ✓ Detected as SPECIES (binomial)")
                    sys.stdout.flush()
                    return 'species'
        
        # Single capitalized word = genus
        if len(parts) == 1 and len(name) > 0 and name[0].isupper():
            print(f"[BiocacheService] Detected as GENUS (single word)")
            sys.stdout.flush()
            return 'genus'
        
        # Default to higher taxonomy
        print(f"[BiocacheService] Defaulting to HIGHER taxonomy")
        sys.stdout.flush()
        return 'higher'
    
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
    
    def search_by_common_name(self, common_name: str) -> Dict:
        """Search by common/vernacular name"""
        filters = {'common_name': common_name}
        return self.search_occurrences(filters=filters)
    
    def get_specimen_by_id(self, specimen_id: str) -> Optional[Dict]:
        """Get a specific specimen by its UUID or catalog number"""
        # Try UUID first
        try:
            response = requests.get(f"{self.base_url}/occurrence/{specimen_id}", timeout=30)
            if response.status_code == 200:
                return self._process_occurrence(response.json())
        except:
            pass
        
        # Try catalog number
        filters = {'catalog_number': specimen_id}
        results = self.search_occurrences(filters=filters, page_size=1)
        
        if results['occurrences']:
            return results['occurrences'][0]
        
        return None
    
    def build_ala_url(self, filters: Optional[Dict] = None, bounds: Optional[Dict] = None) -> str:
        """
        Build a user-friendly ALA URL for viewing results in the ALA website
        IMPORTANT: This URL must match the query logic in search_occurrences()
        """
        base = f"https://biocache.ala.org.au/occurrences/search?q=*:*&fq=dataResourceUid:%22{self.dataset_id}%22"
        params = []
        
        if filters:
            # Scientific name - RULE 2: use appropriate field based on rank
            if filters.get('scientific_name'):
                name = filters['scientific_name']
                
                # Write to debug log file in current directory (works on all OS)
                import os
                log_path = os.path.join(os.getcwd(), 'biocache_debug.log')
                with open(log_path, 'a') as f:
                    f.write(f"\n=== build_ala_url DEBUG ===\n")
                    f.write(f"Input name: '{name}'\n")
                
                # CRITICAL: Clean the name and ensure proper handling
                name = name.strip()
                name = ' '.join(name.split())  # normalize whitespace
                
                # Remove subgenus/author info in parentheses
                # e.g., "Rhipidura (Rhipidura) fuliginosa" -> "Rhipidura fuliginosa"
                import re
                name = re.sub(r'\([^)]*\)', '', name).strip()
                name = ' '.join(name.split())
                
                with open(log_path, 'a') as f:
                    f.write(f"After clean: '{name}'\n")
                    f.write(f"Split parts: {name.split()}\n")
                
                # DEFENSIVE CHECK: If name has 2+ words with capital+lowercase pattern, FORCE it to be species
                parts = name.split()
                if len(parts) >= 2 and len(parts[0]) > 0 and len(parts[1]) > 0:
                    if parts[0][0].isupper() and parts[1][0].islower():
                        rank = 'species'
                        with open(log_path, 'a') as f:
                            f.write(f"FORCED to species rank (defensive check passed)\n")
                        print(f"[BiocacheService] build_ala_url: FORCED to species rank for binomial: {name}")
                    else:
                        rank = self.determine_taxonomic_rank(name)
                        with open(log_path, 'a') as f:
                            f.write(f"Using determine_taxonomic_rank, got: {rank}\n")
                else:
                    rank = self.determine_taxonomic_rank(name)
                    with open(log_path, 'a') as f:
                        f.write(f"Less than 2 parts, using determine_taxonomic_rank: {rank}\n")
                
                with open(log_path, 'a') as f:
                    f.write(f"Final rank: {rank}\n")
                
                print(f"[BiocacheService] build_ala_url: scientific_name='{name}', taxonomic rank = {rank}")
                sys.stdout.flush()
                
                if rank == 'species':
                    url_param = f'fq=species:%22{name}%22'
                    with open(log_path, 'a') as f:
                        f.write(f"Building URL param: {url_param}\n")
                    print(f"[BiocacheService] build_ala_url: Using species: for {name}")
                    params.append(url_param)
                elif rank == 'genus':
                    # Extract just the genus name (first word)
                    genus_name = name.split()[0] if ' ' in name else name
                    url_param = f'fq=genus:%22{genus_name}%22'
                    with open(log_path, 'a') as f:
                        f.write(f"Building URL param: {url_param}\n")
                    print(f"[BiocacheService] build_ala_url: Using genus: for {genus_name}")
                    params.append(url_param)
                elif rank == 'family':
                    url_param = f'fq=family:%22{name}%22'
                    with open(log_path, 'a') as f:
                        f.write(f"Building URL param: {url_param}\n")
                    print(f"[BiocacheService] build_ala_url: Using family: for {name}")
                    params.append(url_param)
                else:
                    # Higher taxonomy - just use the name in a general field
                    url_param = f'fq=order:%22{name}%22'
                    with open(log_path, 'a') as f:
                        f.write(f"Building URL param: {url_param}\n")
                    print(f"[BiocacheService] build_ala_url: Using order/class/phylum for {name}")
                    params.append(url_param)
            
            # Common name - RULE 1: use vernacularName field
            # RULE 4: Changed from 'if' to 'elif'
            elif filters.get('common_name'):
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
    
    def _is_species_name(self, name: str) -> bool:
        """
        Check if a name is a species-level binomial name
        Species names have two parts: "Genus species"
        """
        parts = name.strip().split()
        # Binomial name has exactly 2 parts (or 3+ if includes subspecies/variety)
        # First part starts with capital, second part is lowercase
        if len(parts) >= 2:
            # Check if it looks like a binomial: Capital lowercase
            if parts[0][0].isupper() and parts[1][0].islower():
                return True
        return False
    
    def _is_higher_taxon(self, name: str) -> bool:
        """Check if a name is likely a higher taxonomic rank (family, order, etc.)"""
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
    
    def _should_include_occurrence(self, occurrence: Dict, bounds: Optional[Dict], show_only_with_images: bool = True) -> bool:
        """
        Additional filtering logic for occurrences
        Can optionally filter to only include specimens with valid images
        """
        # Check for valid coordinates
        lat = occurrence.get('latitude')
        lon = occurrence.get('longitude')
        if lat is None or lon is None:
            return False
        
        # Check if coordinates are within bounds (if bounds provided)
        if bounds:
            if not (bounds['south'] <= lat <= bounds['north'] and
                    bounds['west'] <= lon <= bounds['east']):
                return False
        
        # Check for valid image (only if requested)
        if show_only_with_images:
            has_image = (
                occurrence.get('imageUrl') or 
                occurrence.get('largeImageUrl') or 
                occurrence.get('thumbnailUrl') or 
                (occurrence.get('images') and len(occurrence.get('images', [])) > 0)
            )
            
            # DEBUG: Log first few occurrences
            if not hasattr(self, '_debug_count'):
                self._debug_count = 0
            if self._debug_count < 3:
                print(f"[BiocacheService] Specimen {occurrence.get('id')}: has_image={has_image}, show_only_with_images={show_only_with_images}")
                self._debug_count += 1
            
            if not has_image:
                return False
        else:
            # DEBUG: Log that we're NOT filtering by images
            if not hasattr(self, '_debug_no_filter_logged'):
                print(f"[BiocacheService] NOT filtering by images (show_only_with_images={show_only_with_images})")
                self._debug_no_filter_logged = True
        
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