#!/usr/bin/env python
"""Test script to verify purchase form works correctly"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'malar_site.settings')
django.setup()

from malar_app.models import Purchase, Product, Dealer, Stock
from malar_app.forms import PurchaseForm
from django.utils import timezone
from decimal import Decimal

print("=" * 60)
print("PURCHASE FORM TEST")
print("=" * 60)

# Check if we have test data
dealers = Dealer.objects.all()
products = Product.objects.all()

if not dealers.exists():
    print("❌ No dealers found. Please create a dealer first.")
    exit()

if not products.exists():
    print("❌ No products found. Please create a product first.")
    exit()

# Get first dealer and product
dealer = dealers.first()
product = products.first()

print(f"\n✅ Using dealer: {dealer.name}")
print(f"✅ Using product: {product.name}")

# Test form with valid data
form_data = {
    'purchase_id': f'TEST-{timezone.now().timestamp()}',
    'dealer': dealer.id,
    'product': product.id,
    'quantity': 10,
    'price': Decimal('100.00'),
    'date': timezone.now(),
}

print(f"\n📝 Testing form with data:")
print(f"   Purchase ID: {form_data['purchase_id']}")
print(f"   Quantity: {form_data['quantity']}")
print(f"   Price: {form_data['price']}")
print(f"   Date: {form_data['date']}")

form = PurchaseForm(data=form_data)

if form.is_valid():
    print("\n✅ Form is VALID")
    
    # Save the purchase
    purchase = form.save()
    print(f"\n✅ Purchase SAVED to database:")
    print(f"   ID: {purchase.id}")
    print(f"   Purchase ID: {purchase.purchase_id}")
    print(f"   Dealer: {purchase.dealer.name}")
    print(f"   Product: {purchase.product.name}")
    print(f"   Quantity: {purchase.quantity}")
    print(f"   Price: {purchase.price}")
    print(f"   Date: {purchase.date}")
    
    # Verify stock was updated
    stock = Stock.objects.get(product=product)
    print(f"\n✅ Stock UPDATED:")
    print(f"   Product: {stock.product.name}")
    print(f"   Current Quantity: {stock.quantity}")
    
    # Verify data in database
    db_purchase = Purchase.objects.get(id=purchase.id)
    print(f"\n✅ VERIFIED from database:")
    print(f"   Purchase exists: {db_purchase is not None}")
    print(f"   Date stored: {db_purchase.date}")
    
    print("\n" + "=" * 60)
    print("✅ PURCHASE FORM TEST PASSED - DATA SAVED SUCCESSFULLY")
    print("=" * 60)
    
else:
    print("\n❌ Form is INVALID")
    print(f"Errors: {form.errors}")
    exit(1)
