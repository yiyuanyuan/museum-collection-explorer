import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    GOOGLE_GEOCODING_API_KEY = os.environ.get('GOOGLE_GEOCODING_API_KEY', '')
    
    # ALA Biocache API endpoints
    BIOCACHE_BASE_URL = "https://biocache-ws.ala.org.au/ws"
    BIOCACHE_SEARCH_URL = f"{BIOCACHE_BASE_URL}/occurrences/search"
    BIOCACHE_FACETS_URL = f"{BIOCACHE_BASE_URL}/occurrence/facets"
    
    # Dataset configuration
    DATASET_ID = "dr340"  # Australian Museum OZCAM - exact format from test script
    
    # CORS settings
    CORS_ORIGINS = ["http://localhost:3000"]
    
    # Cache settings
    CACHE_TYPE = "simple"
    CACHE_DEFAULT_TIMEOUT = 300