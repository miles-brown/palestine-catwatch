
import requests
import sys

# Assume backend is running on localhost:8000
API_URL = "http://localhost:8000"

def test_report_generation():
    # 1. Create a dummy protest/media if not exists? 
    # Actually, let's just use an existing one if possible, or try to ingest a fake URL?
    # Better yet, let's look at the database content first.
    pass

if __name__ == "__main__":
    try:
        # Check if server is up
        r = requests.get(f"{API_URL}/")
        print(f"Server Status: {r.status_code}")
        
        # List media
        # We don't have a list media endpoint public? We have list protests.
        # Let's try to get officers, see if any exist.
        officers = requests.get(f"{API_URL}/officers").json()
        print(f"Found {len(officers)} officers.")
        
        if len(officers) > 0:
            # Try to find a media ID from appearances?
            # We can't easily query that from public API.
            # Let's just try to hit report for ID 1, 2, 3...
            for i in range(1, 10):
                resp = requests.get(f"{API_URL}/media/{i}/report")
                if resp.status_code == 200:
                    print(f"SUCCESS: Found report for Media {i}")
                    data = resp.json()
                    print("Stats:", data['stats'])
                    print("First Officer:", data['officers'][0] if data['officers'] else "None")
                    break
                else:
                    print(f"Media {i}: {resp.status_code} - {resp.json().get('detail')}")
        else:
            print("No officers found. Cannot verify report with data.")

    except Exception as e:
        print(f"Test Failed: {e}")
