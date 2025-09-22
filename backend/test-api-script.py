#!/usr/bin/env python3
"""
Test script to verify the Biocache API is working correctly
Run this to check if the backend is fetching data properly
"""

import requests
import json

def test_biocache_api():
    """Test the Biocache API directly"""
    url = "https://biocache-ws.ala.org.au/ws/occurrences/search"
    
    # Using exact parameters from your working script
    params = {
        "q": "*:*",
        "fq": ['dataResourceUid:"dr340"', "multimedia:Image"],
        "pageSize": 10
    }
    
    print("Testing Biocache API directly...")
    print(f"URL: {url}")
    print(f"Params: {params}")
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        print(f"\n✅ Success! Total records: {data.get('totalRecords', 0)}")
        print(f"Received {len(data.get('occurrences', []))} occurrences")
        
        # Show first occurrence as sample
        if data.get('occurrences'):
            first = data['occurrences'][0]
            print("\nFirst occurrence sample:")
            print(f"  - UUID: {first.get('uuid')}")
            print(f"  - Scientific Name: {first.get('scientificName')}")
            print(f"  - Common Name: {first.get('vernacularName')}")
            print(f"  - State: {first.get('stateProvince')}")
            print(f"  - Has coordinates: {bool(first.get('decimalLatitude'))}")
            print(f"  - Image URL: {first.get('imageUrl', 'No imageUrl')}")
            print(f"  - Large Image: {first.get('largeImageUrl', 'No largeImageUrl')}")
            print(f"  - Thumbnail: {first.get('thumbnailUrl', 'No thumbnailUrl')}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return False

def test_backend_api():
    """Test our Flask backend API"""
    backend_url = "http://localhost:5000/api/occurrences"
    
    print("\n\nTesting Flask Backend API...")
    print(f"URL: {backend_url}")
    
    try:
        response = requests.get(backend_url)
        response.raise_for_status()
        data = response.json()
        
        print(f"\n✅ Backend Success! Total records: {data.get('totalRecords', 0)}")
        print(f"Received {len(data.get('occurrences', []))} occurrences")
        
        # Check facets
        if data.get('facets'):
            print("\nFacets available:")
            for facet_name, values in data['facets'].items():
                print(f"  - {facet_name}: {len(values)} options")
        
        return True
        
    except requests.exceptions.ConnectionError:
        print("\n❌ Cannot connect to backend. Make sure Flask is running on port 5000")
        return False
    except Exception as e:
        print(f"\n❌ Backend Error: {str(e)}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("ALA BIOCACHE API TEST")
    print("=" * 50)
    
    # Test direct API
    biocache_ok = test_biocache_api()
    
    # Test backend
    backend_ok = test_backend_api()
    
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    print(f"Biocache API: {'✅ Working' if biocache_ok else '❌ Failed'}")
    print(f"Backend API: {'✅ Working' if backend_ok else '❌ Failed'}")
    
    if not backend_ok and biocache_ok:
        print("\nℹ️  The Biocache API works but backend doesn't.")
        print("   Check that your Flask server is running: python app.py")