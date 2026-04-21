import os
import django

# Setup django environment before importing models
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "malar_site.settings")
django.setup()

from django.test import Client
from django.contrib.auth.models import User

def run_tests():
    client = Client()
    
    # Bypass Djongo boolean filter bug
    all_users = list(User.objects.all())
    admin_user = next((u for u in all_users if u.is_superuser), None)
    
    if not admin_user:
        admin_user = User.objects.create_superuser('testadmin', 'admin@example.com', 'testing321')
    
    # Login
    client.force_login(admin_user)
    
    urls_to_test = [
        '/',
        '/admin-dashboard/',
        '/dealers/',
        '/purchases/',
        '/sales/',
    ]
    
    errors_found = False
    
    for url in urls_to_test:
        try:
            response = client.get(url)
            print(f"Testing {url}: Status {response.status_code}")
            if response.status_code >= 400:
                print(f"ERROR on {url}: HTTP {response.status_code}")
                errors_found = True
        except Exception as e:
            print(f"EXCEPTION on {url}: {e}")
            errors_found = True
            
    if errors_found:
        print("ERRORS DETECTED.")
    else:
        print("ALL TESTS PASSED.")

if __name__ == '__main__':
    run_tests()
