import requests
from bs4 import BeautifulSoup

url = "http://localhost:8000"
session = requests.Session()

# Get login page to grab CSRF token
login_url = f"{url}/login/"
r = session.get(login_url)
if r.status_code != 200:
    print(f"Failed to load login page: {r.status_code}")
    exit(1)

soup = BeautifulSoup(r.text, 'html.parser')
csrf_token = soup.find('input', {'name': 'csrfmiddlewaretoken'})
if not csrf_token:
    print("Could not find CSRF token")
    exit(1)

# We don't have the admin credentials.
# Instead, let's just use django test client directly.
