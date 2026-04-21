from django.core.management.base import BaseCommand
from malar_app.models import Category, Product, Stock, Customer, Invoice, InvoiceLineItem
from decimal import Decimal
from datetime import datetime, timedelta

class Command(BaseCommand):
    help = 'Populate database with sample/fake data'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting data population...'))
        
        # Clear existing data in correct order
        self.stdout.write('Clearing existing data...')
        InvoiceLineItem.objects.all().delete()
        Invoice.objects.all().delete()
        Product.objects.all().delete()
        Category.objects.all().delete()
        Customer.objects.all().delete()
        
        # Create Categories
        self.stdout.write('Creating categories...')
        categories_data = [
            {'name': 'Electronics', 'description': 'Electronic devices and gadgets'},
            {'name': 'Clothing', 'description': 'Apparel and fashion items'},
            {'name': 'Books', 'description': 'Books and reading materials'},
            {'name': 'Home & Garden', 'description': 'Home and garden products'},
            {'name': 'Sports', 'description': 'Sports equipment and accessories'},
        ]
        
        categories = []
        for cat_data in categories_data:
            cat = Category.objects.create(**cat_data)
            categories.append(cat)
            self.stdout.write(f'  ✓ Created category: {cat.name}')
        
        # Create Products
        self.stdout.write('Creating products...')
        products_data = [
            # Electronics
            {'name': 'Laptop Pro', 'sku': 'LAP001', 'price': Decimal('999.99'), 'category': categories[0], 'description': 'High-performance laptop', 'quantity': 15},
            {'name': 'Wireless Mouse', 'sku': 'MOUSE001', 'price': Decimal('29.99'), 'category': categories[0], 'description': 'Ergonomic wireless mouse', 'quantity': 50},
            {'name': 'USB-C Cable', 'sku': 'USB001', 'price': Decimal('12.99'), 'category': categories[0], 'description': 'High-speed USB-C cable', 'quantity': 100},
            
            # Clothing
            {'name': 'Cotton T-Shirt', 'sku': 'TSHIRT001', 'price': Decimal('24.99'), 'category': categories[1], 'description': 'Comfortable cotton t-shirt', 'quantity': 80},
            {'name': 'Denim Jeans', 'sku': 'JEANS001', 'price': Decimal('59.99'), 'category': categories[1], 'description': 'Classic denim jeans', 'quantity': 40},
            {'name': 'Winter Jacket', 'sku': 'JACKET001', 'price': Decimal('129.99'), 'category': categories[1], 'description': 'Warm winter jacket', 'quantity': 25},
            
            # Books
            {'name': 'Python Programming', 'sku': 'BOOK001', 'price': Decimal('49.99'), 'category': categories[2], 'description': 'Learn Python from basics to advanced', 'quantity': 30},
            {'name': 'Django Web Dev', 'sku': 'BOOK002', 'price': Decimal('44.99'), 'category': categories[2], 'description': 'Master Django web framework', 'quantity': 20},
            {'name': 'Clean Code', 'sku': 'BOOK003', 'price': Decimal('39.99'), 'category': categories[2], 'description': 'Writing clean, maintainable code', 'quantity': 25},
            
            # Home & Garden
            {'name': 'Coffee Maker', 'sku': 'COFFEE001', 'price': Decimal('79.99'), 'category': categories[3], 'description': 'Automatic coffee maker', 'quantity': 18},
            {'name': 'Desk Lamp', 'sku': 'LAMP001', 'price': Decimal('34.99'), 'category': categories[3], 'description': 'LED desk lamp with USB charge', 'quantity': 45},
            
            # Sports
            {'name': 'Yoga Mat', 'sku': 'YOGA001', 'price': Decimal('29.99'), 'category': categories[4], 'description': 'Non-slip yoga mat', 'quantity': 60},
            {'name': 'Dumbbells Set', 'sku': 'DUMB001', 'price': Decimal('89.99'), 'category': categories[4], 'description': '5-20kg dumbbell set', 'quantity': 12},
        ]
        
        products = []
        for prod_data in products_data:
            quantity = prod_data.pop('quantity')
            prod = Product.objects.create(**prod_data, is_active=True)
            Stock.objects.create(
                product=prod,
                quantity=quantity,
                warehouse_location=f'Shelf {len(products) % 10}',
                reorder_level=max(5, quantity // 3)
            )
            products.append(prod)
            self.stdout.write(f'  ✓ Created product: {prod.name} (SKU: {prod.sku})')
        
        # Create Customers
        self.stdout.write('Creating customers...')
        customers_data = [
            {'name': 'John Smith', 'email': 'john@example.com', 'phone': '+1-555-0101', 'address': '123 Main St', 'city': 'New York', 'state': 'NY', 'postal_code': '10001'},
            {'name': 'Sarah Johnson', 'email': 'sarah@example.com', 'phone': '+1-555-0102', 'address': '456 Oak Ave', 'city': 'Los Angeles', 'state': 'CA', 'postal_code': '90001'},
            {'name': 'Michael Chen', 'email': 'michael@example.com', 'phone': '+1-555-0103', 'address': '789 Pine Rd', 'city': 'Chicago', 'state': 'IL', 'postal_code': '60601'},
            {'name': 'Emma Wilson', 'email': 'emma@example.com', 'phone': '+1-555-0104', 'address': '321 Elm St', 'city': 'Houston', 'state': 'TX', 'postal_code': '77001'},
        ]
        
        customers = []
        for cust_data in customers_data:
            cust = Customer.objects.create(**cust_data)
            customers.append(cust)
            self.stdout.write(f'  ✓ Created customer: {cust.name}')
        
        # Create Invoices
        self.stdout.write('Creating invoices...')
        for i, customer in enumerate(customers):
            invoice_number = f'INV-2026-{1001 + i}'
            inv = Invoice.objects.create(
                invoice_number=invoice_number,
                customer=customer,
                invoice_date=datetime.now() - timedelta(days=i*5),
                status='completed',
                notes='Sample invoice'
            )
            
            # Add random items to invoice
            for j in range(1, 4):
                if j < len(products):
                    InvoiceLineItem.objects.create(
                        invoice=inv,
                        product=products[j],
                        quantity=j + 1,
                        unit_price=products[j].price
                    )
            
            self.stdout.write(f'  ✓ Created invoice {invoice_number} for {customer.name}')
        
        self.stdout.write(self.style.SUCCESS('✓ Data population completed successfully!'))
        self.stdout.write(f'  - Categories: {len(categories)}')
        self.stdout.write(f'  - Products: {len(products)}')
        self.stdout.write(f'  - Customers: {len(customers)}')
