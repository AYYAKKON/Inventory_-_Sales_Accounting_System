from django.contrib import admin
from django.db.models import F
from .models import Category, Product, ProductImage, Stock, StockHistory, Customer, Invoice, InvoiceLineItem, Dealer

# Register your models here.

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at']
    search_fields = ['name', 'description']
    list_filter = ['created_at']
    readonly_fields = ['created_at', 'updated_at']


class ProductImageInline(admin.TabularInline):
    """Inline admin for product images"""
    model = ProductImage
    extra = 1
    fields = ['image', 'alt_text', 'is_primary']
    readonly_fields = ['created_at']


class StockInline(admin.StackedInline):
    """Inline admin for product stock"""
    model = Stock
    extra = 0
    fields = ['quantity', 'warehouse_location', 'reorder_level', 'last_updated']
    readonly_fields = ['last_updated']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'sku', 'price', 'category', 'get_stock_quantity', 'get_dealers_count', 'is_active', 'created_at']
    search_fields = ['name', 'sku', 'description']
    list_filter = ['is_active', 'category', 'created_at']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [ProductImageInline, StockInline]
    fieldsets = (
        ('Product Information', {
            'fields': ('name', 'sku', 'description')
        }),
        ('Pricing & Category', {
            'fields': ('price', 'category', 'unit')
        }),
        ('Dealers', {
            'fields': ('dealers',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_stock_quantity(self, obj):
        try:
            return obj.stock.quantity
        except:
            return 'N/A'
    get_stock_quantity.short_description = 'Stock Quantity'  # type: ignore
    
    def get_dealers_count(self, obj):
        return obj.dealers.count()
    get_dealers_count.short_description = 'Dealers'  # type: ignore


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ['product', 'is_primary', 'created_at']
    list_filter = ['is_primary', 'created_at', 'product__category']
    search_fields = ['product__name', 'alt_text']
    readonly_fields = ['created_at']
    fieldsets = (
        ('Image Information', {
            'fields': ('product', 'image', 'alt_text')
        }),
        ('Settings', {
            'fields': ('is_primary',)
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ['product', 'quantity', 'reorder_level', 'is_low_stock', 'warehouse_location', 'last_updated']
    list_filter = ['last_updated', 'warehouse_location']
    search_fields = ['product__name', 'product__sku', 'warehouse_location']
    readonly_fields = ['last_updated']
    fieldsets = (
        ('Product & Location', {
            'fields': ('product', 'warehouse_location')
        }),
        ('Stock Levels', {
            'fields': ('quantity', 'reorder_level')
        }),
        ('Metadata', {
            'fields': ('last_updated',),
            'classes': ('collapse',)
        }),
    )
    
    def is_low_stock(self, obj):
        return obj.is_low_stock
    is_low_stock.boolean = True  # type: ignore
    is_low_stock.short_description = 'Low Stock?'  # type: ignore


@admin.register(StockHistory)
class StockHistoryAdmin(admin.ModelAdmin):
    list_display = ['stock', 'quantity_change', 'previous_quantity', 'new_quantity', 'action', 'performed_by', 'created_at']
    list_filter = ['action', 'created_at']
    search_fields = ['stock__product__name', 'notes']
    readonly_fields = ['created_at']
    fieldsets = (
        ('Stock Information', {
            'fields': ('stock', 'action')
        }),
        ('Quantity Changes', {
            'fields': ('previous_quantity', 'quantity_change', 'new_quantity')
        }),
        ('Details', {
            'fields': ('notes', 'performed_by', 'created_at'),
            'classes': ('collapse',)
        }),
    )


class InvoiceLineItemInline(admin.TabularInline):
    """Inline admin for invoice line items"""
    model = InvoiceLineItem
    extra = 1
    fields = ['product', 'quantity', 'unit_price', 'line_total']
    readonly_fields = ['line_total', 'created_at']


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'phone', 'city', 'country', 'is_active', 'created_at']
    search_fields = ['name', 'email', 'phone', 'company_name']
    list_filter = ['is_active', 'country', 'city', 'created_at']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Personal Information', {
            'fields': ('name', 'email', 'phone', 'company_name')
        }),
        ('Address', {
            'fields': ('address', 'city', 'state', 'postal_code', 'country')
        }),
        ('Business Information', {
            'fields': ('gst_number',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'customer', 'dealer', 'total_amount', 'payment_status', 'status', 'invoice_date']
    search_fields = ['invoice_number', 'customer__name', 'dealer__name']
    list_filter = ['status', 'payment_status', 'invoice_date', 'customer', 'dealer']
    readonly_fields = ['invoice_number', 'created_by', 'created_at', 'updated_at', 'outstanding_amount']
    inlines = [InvoiceLineItemInline]
    actions = ['mark_as_paid']
    fieldsets = (
        ('Invoice Information', {
            'fields': ('invoice_number', 'customer', 'dealer', 'invoice_date', 'due_date')
        }),
        ('Amounts', {
            'fields': ('subtotal', 'tax_percentage', 'tax_amount', 'total_amount')
        }),
        ('Payment Information', {
            'fields': ('payment_status', 'amount_paid', 'outstanding_amount', 'payment_date', 'payment_method')
        }),
        ('Status & Notes', {
            'fields': ('status', 'notes')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def outstanding_amount(self, obj):
        """Display outstanding amount"""
        return f"${obj.get_outstanding_amount():.2f}"
    outstanding_amount.short_description = "Outstanding Amount"  # type: ignore
    
    def mark_as_paid(self, request, queryset):
        """Admin action to mark invoices as paid"""
        from django.utils import timezone
        updated = queryset.update(
            payment_status='paid',
            payment_date=timezone.now().date(),
            amount_paid=F('total_amount')
        )
        self.message_user(request, f'{updated} invoice(s) marked as paid.')
    mark_as_paid.short_description = "Mark selected invoices as paid"  # type: ignore
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(InvoiceLineItem)
class InvoiceLineItemAdmin(admin.ModelAdmin):
    list_display = ['invoice', 'product', 'quantity', 'unit_price', 'line_total']
    search_fields = ['invoice__invoice_number', 'product__name']
    list_filter = ['invoice__invoice_date', 'product']
    readonly_fields = ['line_total', 'created_at']
    fieldsets = (
        ('Invoice & Product', {
            'fields': ('invoice', 'product')
        }),
        ('Quantity & Price', {
            'fields': ('quantity', 'unit_price', 'line_total')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(Dealer)
class DealerAdmin(admin.ModelAdmin):
    list_display = ['name', 'contact_person', 'email', 'phone', 'city', 'commission_percentage', 'is_active', 'created_at']
    search_fields = ['name', 'email', 'phone', 'contact_person']
    list_filter = ['is_active', 'country', 'city', 'created_at']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Dealer Information', {
            'fields': ('name', 'contact_person', 'email', 'phone')
        }),
        ('Address', {
            'fields': ('address', 'city', 'state', 'postal_code', 'country')
        }),
        ('Business Information', {
            'fields': ('commission_percentage',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
