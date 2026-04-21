from .models import Dealer, Purchase, Sale
from django import forms
from .models import Product, Stock, Category, ProductImage, Customer, Invoice, InvoiceLineItem, Dealer, Purchase, Sale
import csv
from io import StringIO


class StockUpdateForm(forms.ModelForm):
    """Form to update stock quantity"""
    action = forms.ChoiceField(
        choices=[
            ('add', 'Add Stock'),
            ('remove', 'Remove Stock'),
            ('set', 'Set Stock (Exact Amount)'),
        ],
        label='Action',
        help_text='Select whether to add, remove, or set exact quantity'
    )
    quantity_change = forms.IntegerField(
        min_value=0,
        label='Quantity',
        help_text='Amount to add/remove or exact quantity to set'
    )
    notes = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False,
        label='Notes',
        help_text='Reason for stock change (optional)'
    )
    
    class Meta:
        model = Stock
        fields = ['quantity', 'warehouse_location', 'reorder_level']


class ProductBulkImportForm(forms.Form):
    """Form for bulk importing products via CSV"""
    csv_file = forms.FileField(
        label='CSV File',
        help_text='Upload CSV with columns: name, description, sku, price, category_name, quantity'
    )
    
    def clean_csv_file(self):
        csv_file = self.cleaned_data['csv_file']
        
        # Check file size
        if csv_file.size > 5 * 1024 * 1024:  # 5MB limit
            raise forms.ValidationError("File size should not exceed 5MB")
        
        # Verify it's a CSV
        if not csv_file.name.endswith('.csv'):
            raise forms.ValidationError("Only CSV files are allowed")
        
        return csv_file


class InventoryReportForm(forms.Form):
    """Form for generating inventory reports"""
    REPORT_TYPE_CHOICES = [
        ('all', 'All Products'),
        ('low_stock', 'Low Stock Items'),
        ('category', 'By Category'),
        ('inactive', 'Inactive Products'),
    ]
    
    EXPORT_FORMAT_CHOICES = [
        ('pdf', 'PDF'),
        ('csv', 'CSV'),
    ]
    
    report_type = forms.ChoiceField(
        choices=REPORT_TYPE_CHOICES,
        label='Report Type',
        widget=forms.RadioSelect()
    )
    
    export_format = forms.ChoiceField(
        choices=EXPORT_FORMAT_CHOICES,
        label='Export Format',
        widget=forms.RadioSelect()
    )
    
    category = forms.ModelChoiceField(
        queryset=Category.objects.none(),  # Empty queryset initially, will be populated in __init__
        required=False,
        empty_label='-- Select Category --',
        label='Category (if applicable)'
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            # Set category queryset dynamically at form instantiation time
            self.fields['category'].queryset = Category.objects.all()
        except (AttributeError, TypeError) as e:
            # Specific exception handling for queryset issues
            self.fields['category'].queryset = Category.objects.none()
        except Exception as e:
            # Log unexpected errors
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Unexpected error loading categories in InventoryReportForm: {e}")
            self.fields['category'].queryset = Category.objects.none()


class CustomProductForm(forms.ModelForm):
    """Enhanced product creation form"""
    images = forms.FileField(
        required=False,
        label='Product Images',
        help_text='You can select multiple images',
    )
    initial_stock = forms.IntegerField(
        required=False,
        min_value=0,
        label='Initial Stock Quantity',
        help_text='Stock quantity when creating product',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0', 'min': '0'})
    )
    warehouse_location = forms.CharField(
        required=False,
        max_length=200,
        label='Warehouse Location',
        help_text='e.g., Aisle A, Shelf 3',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Aisle A, Shelf 3'})
    )
    reorder_level = forms.IntegerField(
        initial=10,
        min_value=0,
        label='Reorder Level',
        help_text='Alert when stock falls below this',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '10', 'min': '0'})
    )
    dealers = forms.ModelMultipleChoiceField(
        queryset=Dealer.objects.none(),  # Empty queryset initially, will be populated in __init__
        required=False,
        label='Dealers',
        help_text='Select dealers who will distribute this product',
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'})
    )
    
    class Meta:
        model = Product
        fields = ['name', 'description', 'sku', 'price', 'category', 'unit', 'dealers', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Product Name'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Product Description'}),
            'sku': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'SKU-001'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00', 'step': '0.01', 'min': '0'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'unit': forms.Select(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            # Load all dealers and filter in Python (Djongo-safe approach)
            # Avoids Djongo SQL parsing bugs with boolean fields
            try:
                all_dealers = list(Dealer.objects.all())
                # Filter active dealers in Python
                active_dealers = [d for d in all_dealers if d.is_active]
                # Create a queryset from the filtered list
                if active_dealers:
                    dealer_ids = [d.id for d in active_dealers]
                    self.fields['dealers'].queryset = Dealer.objects.filter(id__in=dealer_ids)
                else:
                    self.fields['dealers'].queryset = Dealer.objects.none()
            except Exception as e:
                logger.warning(f"Could not load dealers: {type(e).__name__}: {e}")
                # Fallback: use all dealers without filtering
                try:
                    self.fields['dealers'].queryset = Dealer.objects.all()
                except:
                    self.fields['dealers'].queryset = Dealer.objects.none()
            
            # Try to load all categories
            try:
                categories_qs = Category.objects.all()
                self.fields['category'].queryset = categories_qs
            except Exception as e:
                logger.warning(f"Could not load categories: {type(e).__name__}: {e}")
                if 'category' in self.fields:
                    self.fields['category'].queryset = Category.objects.none()
                    
        except Exception as e:
            # Catch any other errors in form initialization
            logger.exception(f"Unexpected error in CustomProductForm.__init__: {type(e).__name__}: {e}")
            # Set safe defaults
            try:
                self.fields['dealers'].queryset = Dealer.objects.none()
                if 'category' in self.fields:
                    self.fields['category'].queryset = Category.objects.none()
            except:
                pass  # If even this fails, let Django handle it
    
    def clean_images(self):
        """Validate image file size and format"""
        images = self.files.getlist('images')
        max_file_size = 5 * 1024 * 1024  # 5MB
        allowed_formats = {'image/jpeg', 'image/png', 'image/gif', 'image/webp'}
        
        for image in images:
            # Check file size
            if image.size > max_file_size:
                raise forms.ValidationError(f"Image '{image.name}' exceeds 5MB limit. Size: {image.size / (1024*1024):.2f}MB")
            
            # Check file format
            if image.content_type not in allowed_formats:
                raise forms.ValidationError(f"Image '{image.name}' has invalid format. Allowed: JPEG, PNG, GIF, WebP")
        
        return images
    
    def clean_sku(self):
        """Validate SKU is unique and handle read-only on edit"""
        sku = self.cleaned_data.get('sku')
        if sku:
            # Check if this is an update (instance exists) or create
            if self.instance.pk:
                # Update case: if SKU changed, reject (SKU is read-only on edit)
                if self.instance.sku != sku:
                    raise forms.ValidationError("SKU cannot be changed after product creation.")
            else:
                # Create case: must be unique
                if Product.objects.filter(sku=sku).exists():
                    raise forms.ValidationError("A product with this SKU already exists.")
        return sku

class CustomerForm(forms.ModelForm):
    """Form for creating and editing customers"""
    class Meta:
        model = Customer
        fields = ['name', 'email', 'phone', 'address', 'city', 'state', 'postal_code', 'country', 'company_name', 'gst_number', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full Name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'customer@example.com'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+91 XXXXXXXXXX'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Street Address'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City'}),
            'state': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'State/Province'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Postal Code'}),
            'country': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Country'}),
            'company_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Company Name (Optional)'}),
            'gst_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'GST Number (Optional)'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def clean_email(self):
        """Validate email is unique across customers"""
        email = self.cleaned_data.get('email')
        if email:
            # Exclude current customer if updating
            qs = Customer.objects.filter(email=email)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            
            if qs.exists():
                raise forms.ValidationError("A customer with this email address already exists.")
        return email


class InvoiceForm(forms.ModelForm):
    """Form for creating invoices"""
    class Meta:
        model = Invoice
        fields = ['customer', 'dealer', 'due_date', 'tax_percentage', 'notes']
        widgets = {
            'customer': forms.Select(attrs={'class': 'form-control'}),
            'dealer': forms.Select(attrs={'class': 'form-control'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'tax_percentage': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '18', 'step': '0.01'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Invoice notes...'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            # Note: Djongo has issues with BooleanField filters, so we get all and filter in Python
            all_customers = list(Customer.objects.all().order_by('name'))
            active_customers = [c for c in all_customers if c.is_active]
            
            all_dealers = list(Dealer.objects.all().order_by('name'))
            active_dealers = [d for d in all_dealers if d.is_active]
            
            # Create querysets from filtered lists
            customer_ids = [c.id for c in active_customers]
            dealer_ids = [d.id for d in active_dealers]
            
            # Set querysets using id__in to avoid boolean filter issues
            if customer_ids:
                self.fields['customer'].queryset = Customer.objects.filter(id__in=customer_ids).order_by('name')
            else:
                self.fields['customer'].queryset = Customer.objects.none()
                
            if dealer_ids:
                self.fields['dealer'].queryset = Dealer.objects.filter(id__in=dealer_ids).order_by('name')
            else:
                self.fields['dealer'].queryset = Dealer.objects.none()
            
            # Make customer required and dealer optional with proper labels
            self.fields['customer'].empty_label = '--- Select a Customer ---'
            self.fields['customer'].required = True
            self.fields['dealer'].empty_label = '--- No Dealer ---'
            self.fields['dealer'].required = False
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error initializing InvoiceForm querysets: {e}")
            # Fallback: Get all objects without filtering
            self.fields['customer'].queryset = Customer.objects.all().order_by('name')
            self.fields['dealer'].queryset = Dealer.objects.all().order_by('name')


class InvoiceLineItemForm(forms.ModelForm):
    """Form for invoice line items"""
    class Meta:
        model = InvoiceLineItem
        fields = ['product', 'quantity', 'unit_price']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '1', 'min': '1'}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            # Note: Djongo has issues with BooleanField filters, so we get all and filter in Python
            all_products = list(Product.objects.all().order_by('name'))
            active_products = [p for p in all_products if p.is_active]
            
            product_ids = [p.id for p in active_products]
            
            # Set product queryset using id__in to avoid boolean filter issues
            if product_ids:
                self.fields['product'].queryset = Product.objects.filter(id__in=product_ids).order_by('name')
            else:
                self.fields['product'].queryset = Product.objects.none()
        except Exception as e:
            # Fallback: Get all products without filtering
            self.fields['product'].queryset = Product.objects.all().order_by('name')


class DealerForm(forms.ModelForm):
    """Form for creating and managing dealers"""
    class Meta:
        model = Dealer
        fields = ['dealer_id', 'name', 'contact_person', 'email', 'phone', 'address', 'city', 'state', 'postal_code', 'country', 'commission_percentage', 'is_active']
        widgets = {
            'dealer_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Dealer ID (Optional)'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Dealer Name'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contact Person Name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'dealer@example.com'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+91 XXXXXXXXXX'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Street Address'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City'}),
            'state': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'State/Province'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Postal Code'}),
            'country': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Country'}),
            'commission_percentage': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '5', 'step': '0.01', 'min': '0'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class PurchaseForm(forms.ModelForm):
    """Form for creating purchases from dealers"""
    class Meta:
        model = Purchase
        fields = ['purchase_id', 'dealer', 'product', 'quantity', 'price', 'date']
        widgets = {
            'purchase_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Purchase ID/Invoice No'}),
            'dealer': forms.Select(attrs={'class': 'form-control'}),
            'product': forms.Select(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from django.utils import timezone
        # Set current date and time as initial value
        if not self.instance.pk:  # Only for new purchases
            self.fields['date'].initial = timezone.now()


class SaleForm(forms.ModelForm):
    """Form for recording direct sales"""
    class Meta:
        model = Sale
        fields = ['sale_id', 'product', 'quantity', 'total_price', 'date']
        widgets = {
            'sale_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Sale ID'}),
            'product': forms.Select(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'total_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from django.utils import timezone
        # Set current date and time as initial value
        if not self.instance.pk:  # Only for new sales
            self.fields['date'].initial = timezone.now()
