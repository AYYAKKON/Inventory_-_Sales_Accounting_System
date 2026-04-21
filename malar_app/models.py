from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from decimal import Decimal

# Create your models here.

class Category(models.Model):
    """Product category model"""
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Product(models.Model):
    """Product model for inventory"""
    UNIT_CHOICES = [
        ('piece', 'Piece'),
        ('kg', 'Kilogram'),
        ('g', 'Gram'),
        ('litre', 'Litre'),
        ('ml', 'Millilitre'),
        ('meter', 'Meter'),
        ('cm', 'Centimeter'),
        ('box', 'Box'),
        ('pack', 'Pack'),
        ('dozen', 'Dozen'),
        ('roll', 'Roll'),
        ('bottle', 'Bottle'),
        ('can', 'Can'),
        ('set', 'Set'),
        ('pair', 'Pair'),
        ('other', 'Other'),
    ]
    
    name = models.CharField(max_length=300)
    description = models.TextField(blank=True, null=True)
    sku = models.CharField(max_length=100, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    unit = models.CharField(max_length=50, choices=UNIT_CHOICES, default='piece', help_text='Measurement unit for this product')
    is_active = models.BooleanField(default=True)
    dealers = models.ManyToManyField('Dealer', related_name='products', blank=True, help_text='Select dealers who distribute this product')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.sku})"


class ProductImage(models.Model):
    """Multiple image support for products"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='product_images/%Y/%m/%d/')
    alt_text = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-is_primary', 'created_at']
    
    def __str__(self):
        return f"Image for {self.product.name}"


class Stock(models.Model):
    """Stock/Inventory model for tracking quantities"""
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='stock')
    quantity = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    warehouse_location = models.CharField(max_length=200, blank=True, help_text="e.g., Aisle A, Shelf 3")
    reorder_level = models.IntegerField(default=10, validators=[MinValueValidator(0)], help_text="Alert when stock falls below this")
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Stock"
    
    def __str__(self):
        return f"{self.product.name} - {self.quantity} units"
    
    @property
    def is_low_stock(self):
        return self.quantity <= self.reorder_level


class StockHistory(models.Model):
    """Track stock changes over time"""
    ACTION_CHOICES = [
        ('add', 'Stock Added'),
        ('remove', 'Stock Removed'),
        ('set', 'Stock Set'),
        ('sale', 'Sale'),
        ('return', 'Return'),
        ('adjustment', 'Adjustment'),
    ]
    
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name='history')
    quantity_change = models.IntegerField()
    previous_quantity = models.IntegerField()
    new_quantity = models.IntegerField()
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    notes = models.TextField(blank=True)
    performed_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.stock.product.name}: {self.previous_quantity} → {self.new_quantity} ({self.action})"


class Customer(models.Model):
    """Customer model for managing clients"""
    name = models.CharField(max_length=300)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100, default='India')
    company_name = models.CharField(max_length=200, blank=True)
    gst_number = models.CharField(max_length=20, blank=True, help_text="GST Registration Number")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.email})"
    
    def get_full_address(self):
        return f"{self.address}, {self.city}, {self.state} {self.postal_code}, {self.country}"


class Invoice(models.Model):
    """Invoice/Order model for sales"""
    PENDING = 'pending'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'
    
    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (COMPLETED, 'Completed'),
        (CANCELLED, 'Cancelled'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending Payment'),
        ('partial', 'Partially Paid'),
        ('paid', 'Fully Paid'),
        ('overdue', 'Overdue'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('card', 'Credit/Debit Card'),
        ('bank_transfer', 'Bank Transfer'),
        ('check', 'Check'),
        ('other', 'Other'),
    ]
    
    invoice_number = models.CharField(max_length=50, unique=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='invoices')
    dealer = models.ForeignKey('Dealer', on_delete=models.SET_NULL, null=True, blank=True, related_name='invoices', help_text="Dealer who distributed this order")
    invoice_date = models.DateTimeField(auto_now_add=True)
    due_date = models.DateField(null=True, blank=True)
    subtotal = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'), validators=[MinValueValidator(0)])
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'), validators=[MinValueValidator(0)])
    tax_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('18.00'), validators=[MinValueValidator(0)])
    total_amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'), validators=[MinValueValidator(0)])
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    # Payment tracking fields
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    payment_date = models.DateField(null=True, blank=True)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, null=True, blank=True)
    amount_paid = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'), validators=[MinValueValidator(0)])
    created_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, related_name='created_invoices')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-invoice_date']
    
    def __str__(self):
        return f"Invoice {self.invoice_number} - {self.customer.name}"
    
    def calculate_total(self):
        """Calculate total with tax"""
        self.subtotal = sum([item.line_total for item in self.items.all()])  # type: ignore
        self.tax_amount = self.subtotal * (self.tax_percentage / 100)
        self.total_amount = self.subtotal + self.tax_amount
        return self.total_amount
    
    def get_outstanding_amount(self):
        """Calculate outstanding (unpaid) amount"""
        return self.total_amount - self.amount_paid


class InvoiceLineItem(models.Model):
    """Line items in an invoice"""
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(0)])
    line_total = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'), validators=[MinValueValidator(0)])
    created_at = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        self.line_total = self.quantity * self.unit_price
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.product.name} (x{self.quantity})"


class Dealer(models.Model):
    """Dealer/Distributor model for product distribution"""
    dealer_id = models.CharField(max_length=50, unique=True, blank=True, null=True, help_text="Unique Dealer ID")
    name = models.CharField(max_length=300, unique=True)
    contact_person = models.CharField(max_length=200, blank=True)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20)
    address = models.CharField(max_length=400, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, default='India')
    commission_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'), help_text="Commission % for this dealer")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def get_total_sales(self):
        """Calculate total sales through this dealer"""
        return sum([item.line_total for item in InvoiceLineItem.objects.filter(invoice__dealer=self)])
    
    def get_full_address(self):
        return f"{self.address}, {self.city}, {self.state} {self.postal_code}, {self.country}"


class Purchase(models.Model):
    """Purchase module to track procurement of products from dealers"""
    purchase_id = models.CharField(max_length=50, unique=True)
    dealer = models.ForeignKey(Dealer, on_delete=models.CASCADE, related_name='purchases')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='product_purchases')
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    date = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"Purchase {self.purchase_id} - {self.product.name} from {self.dealer.name}"


class Sale(models.Model):
    """Sale module to track selling products directly"""
    sale_id = models.CharField(max_length=50, unique=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='product_sales')
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    total_price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    date = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"Sale {self.sale_id} - {self.product.name}"
