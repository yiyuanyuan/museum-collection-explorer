# Test script to verify ALA's pagination limit
import requests

url = "https://biocache-ws.ala.org.au/ws/occurrences/search"
params = {
    "q": "*:*",
    "fq": [
        'dataResourceUid:"dr340"',
        'multimedia:Image',
        'decimalLatitude:[-90 TO 90]',
        'decimalLongitude:[-180 TO 180]'
    ],
    "pageSize": 100,
    "startIndex": 5000  # Try to get records starting from 5000
}

response = requests.get(url, params=params)
data = response.json()
print(f"Requesting records 5000-5100...")
print(f"Records returned: {len(data.get('occurrences', []))}")