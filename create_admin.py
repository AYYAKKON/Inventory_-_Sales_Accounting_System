#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'malar_site.settings')
django.setup()

from django.contrib.auth.models import User

# Create superuser if it doesn't exist
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@test.com', 'admin123')
    print("✅ Admin account created!")
    print("   Username: admin")
    print("   Password: admin123")
else:
    print("✅ Admin account already exists")
    print("   Username: admin")
    print("   Password: admin123")
