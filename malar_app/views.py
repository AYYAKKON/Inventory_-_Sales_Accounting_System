from .models import Sale
from .models import Purchase, StockHistory
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from .models import Dealer
from django.views.generic import ListView
from django.views.generic import CreateView
from django.urls import reverse_lazy
from django.contrib import messages
from .models import Purchase, StockHistory
from django.shortcuts import render, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, Http404
from django.db.models import Sum, F, ExpressionWrapper, DecimalField, Count
from django.db import DatabaseError
from django.conf import settings
from decimal import Decimal
from .models import Product, Category, Stock, StockHistory, ProductImage, Customer, Invoice, InvoiceLineItem, Dealer, Purchase, Sale
from .forms import StockUpdateForm, ProductBulkImportForm, InventoryReportForm, CustomProductForm, CustomerForm, InvoiceForm, InvoiceLineItemForm, DealerForm, PurchaseForm, SaleForm
import csv
from io import StringIO, TextIOWrapper, BytesIO
from datetime import datetime, timedelta
from django.utils import timezone
import json
import logging

logger = logging.getLogger(__name__)

# ===== AUTHENTICATION VIEWS =====

class CustomLoginView(LoginView):
    """Custom login view with Bootstrap styling"""
    template_name = 'malar_app/login.html'
    redirect_authenticated_user = True
    
    def get_success_url(self):
        """Redirect to admin dashboard after login"""
        return reverse_lazy('admin:index')


class CustomLogoutView(LogoutView):
    """Custom logout view"""
    next_page = 'malar_app:home'


# Create your views here.

class HomeView(TemplateView):
    """Welcome/home page with inventory statistics"""
    template_name = 'malar_app/home.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        debug_log = []
        try:
            debug_log.append("Starting HomeView...")
            # Simplified queries for MongoDB compatibility - load all data into memory
            all_products = list(Product.objects.all())
            debug_log.append(f"Loaded {len(all_products)} products")
            
            all_categories = list(Category.objects.all())
            debug_log.append(f"Loaded {len(all_categories)} categories")
            
            all_stocks = list(Stock.objects.all())
            debug_log.append(f"Loaded {len(all_stocks)} stocks")
            
            # Filter in Python to avoid djongo issues
            active_products = [p for p in all_products if p.is_active]
            low_stock = [s for s in all_stocks if s.quantity <= s.reorder_level]
            
            # Build context
            context['total_products'] = len(active_products)
            context['total_categories'] = len(all_categories)
            context['low_stock_products'] = len(low_stock)
            
            # Calculate inventory value
            total_value = 0.0
            for s in all_stocks:
                try:
                    # Handle MongoDB Decimal128 type
                    price = s.product.price
                    if hasattr(price, 'to_decimal'):
                        price_val = float(price.to_decimal())
                    else:
                        price_val = float(price)
                    value = price_val * float(s.quantity)
                    total_value += value
                except Exception as e:
                    debug_log.append(f"Error calculating stock value: {e}")
            
            context['total_inventory_value'] = total_value
            
            # Featured products - first 6 active products
            context['featured_products'] = active_products[:6]
            context['categories'] = all_categories
            
            debug_log.append(f"Success! Products: {context['total_products']}, Categories: {context['total_categories']}")
            
        except Exception as e:
            import traceback
            debug_log.append(f"ERROR: {e}")
            debug_log.append(traceback.format_exc())
            
            context['total_products'] = 0
            context['total_categories'] = 0
            context['low_stock_products'] = 0
            context['total_inventory_value'] = 0
            context['featured_products'] = []
            context['categories'] = []
        
        # Write debug log
        try:
            import os
            log_dir = os.path.join(settings.BASE_DIR, 'logs')
            os.makedirs(log_dir, exist_ok=True)
            log_path = os.path.join(log_dir, 'homeview_debug.log')
            with open(log_path, 'a') as f:
                f.write('\n'.join(debug_log) + '\n---\n')
        except IOError as e:
            logger.warning(f"Could not write debug log: {e}")
        
        return context


class AdminRequiredMixin(UserPassesTestMixin):
    """Mixin to require user to be admin or staff"""
    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser
    
    def handle_no_permission(self):
        """Handle when user doesn't have admin permission"""
        if not self.request.user.is_authenticated:
            messages.error(self.request, "You must be logged in to access this page.")
            return redirect('malar_app:login')
        else:
            messages.error(self.request, "You must be an admin/staff member to access this page.")
            return redirect('malar_app:product-list')


# ===== ADMIN DASHBOARD VIEW =====

class AdminDashboardView(LoginRequiredMixin, AdminRequiredMixin, TemplateView):
    """Comprehensive admin dashboard with all KPIs and metrics"""
    template_name = 'malar_app/admin_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            now = timezone.now()
            thirty_days_ago = now - timedelta(days=30)
            
            # Load all data into memory (MongoDB/djongo compatible)
            all_invoices = list(Invoice.objects.all())
            all_products = list(Product.objects.all())
            all_stocks = list(Stock.objects.all())
            all_customers = list(Customer.objects.all())
            all_dealers = list(Dealer.objects.all())
            
            # Filter in Python
            completed_invoices = [inv for inv in all_invoices if inv.status == Invoice.COMPLETED]
            pending_invoices = [inv for inv in all_invoices if inv.status == Invoice.PENDING]
            recent_invoices = [inv for inv in completed_invoices if inv.invoice_date >= thirty_days_ago]
            
            # Calculate metrics
            def to_f(val):
                if hasattr(val, 'to_decimal'):
                    return float(val.to_decimal())
                return float(val) if val is not None else 0.0

            total_revenue = sum(to_f(inv.total_amount) for inv in completed_invoices)
            monthly_revenue = sum(to_f(inv.total_amount) for inv in recent_invoices)
            
            context['total_revenue'] = total_revenue
            context['monthly_revenue'] = monthly_revenue
            context['yearly_revenue'] = total_revenue
            context['total_orders'] = len(completed_invoices)
            context['monthly_orders'] = len(recent_invoices)
            context['avg_order_value'] = total_revenue / len(completed_invoices) if completed_invoices else 0.0
            
            # Inventory metrics
            total_qty = sum(int(s.quantity) for s in all_stocks)
            low_stock = [s for s in all_stocks if s.quantity <= s.reorder_level]
            out_of_stock = [s for s in all_stocks if s.quantity == 0]
            
            context['total_items'] = total_qty
            context['low_stock_count'] = len(low_stock)
            context['out_of_stock_count'] = len(out_of_stock)
            context['total_inventory_value'] = sum(float(s.quantity) * to_f(s.product.price) for s in all_stocks)
            
            # Customer metrics
            active_customers = [c for c in all_customers if c.is_active]
            new_customers = [c for c in all_customers if c.created_at >= thirty_days_ago]
            
            context['total_customers'] = len(all_customers)
            context['active_customers'] = len(active_customers)
            context['new_customers_count'] = len(new_customers)
            
            # Product metrics
            active_products = [p for p in all_products if p.is_active]
            
            context['total_products'] = len(all_products)
            context['active_products'] = len(active_products)
            context['inactive_products'] = len(all_products) - len(active_products)
            
            # Dealer metrics
            active_dealers = [d for d in all_dealers if d.is_active]
            new_dealers = [d for d in all_dealers if d.created_at >= thirty_days_ago]
            
            context['total_dealers'] = len(all_dealers)
            context['active_dealers'] = len(active_dealers)
            context['new_dealers_count'] = len(new_dealers)
            
            # Order stats
            context['pending_invoices'] = len(pending_invoices)
            context['completed_invoices'] = len(completed_invoices)
            context['cancelled_invoices'] = len([i for i in all_invoices if i.status == Invoice.CANCELLED])
            
            # Purchase & Sale Metrics (New)
            all_purchases = list(Purchase.objects.all())
            all_sales = list(Sale.objects.all())
            context['total_purchases_count'] = len(all_purchases)
            context['total_purchases_value'] = sum(float(p.quantity) * to_f(p.price) for p in all_purchases)
            context['total_sales_count'] = len(all_sales)
            context['total_sales_value'] = sum(to_f(s.total_price) for s in all_sales)

            # Simple category breakdown
            all_categories = list(Category.objects.all())
            context['category_labels'] = [cat.name for cat in all_categories]
            context['category_data'] = [len([p for p in all_products if p.category.id == cat.id]) for cat in all_categories]
            
            # Revenue trend (simple)
            context['revenue_trend_labels'] = []
            context['revenue_trend_data'] = []
            for i in range(6, -1, -1):
                day = (now - timedelta(days=i)).date()
                context['revenue_trend_labels'].append(str(day))
                context['revenue_trend_data'].append(0)  # Simplified
            
            context['top_customers'] = []
            context['top_selling_products'] = []
            context['recent_activities'] = []
            
        except Exception as e:
            # Fallback for any errors if not already set
            pass
            
        return context


class ProductListView(ListView):
    """View to display all products in inventory"""
    model = Product
    template_name = 'malar_app/product_list.html'
    context_object_name = 'products'
    paginate_by = 12
    
    def get_queryset(self):
        try:
            from django.db.models import Q
            # Load all products and filter in Python (Djongo-safe approach)
            # Avoids Djongo SQL parsing bugs with boolean fields
            try:
                all_products = list(Product.objects.all())
                # Filter active products in Python
                active_products = [p for p in all_products if p.is_active]
            except Exception as e:
                logger.warning(f"Could not load products: {e}")
                active_products = []
            
            # Filter by category if provided
            category_id = self.request.GET.get('category')
            if category_id:
                try:
                    active_products = [p for p in active_products if p.category_id == int(category_id)]
                except (ValueError, TypeError):
                    pass  # Invalid category ID, ignore filter
            
            # Search by name or SKU
            search = self.request.GET.get('search')
            if search:
                search_lower = search.lower()
                active_products = [
                    p for p in active_products 
                    if search_lower in p.name.lower() or search_lower in (p.sku or '').lower()
                ]
            
            # Sort by ID descending
            active_products.sort(key=lambda p: p.id, reverse=True)
            
            # Convert back to QuerySet using IDs (for pagination compatibility)
            product_ids = [p.id for p in active_products]
            if product_ids:
                # Preserve the filtered order
                return Product.objects.filter(id__in=product_ids).order_by('-id')
            else:
                return Product.objects.none()
        except Exception as e:
            logger.exception(f"Error loading products: {type(e).__name__}: {e}")
            return Product.objects.none()
    
    def get_context_data(self, **kwargs):
        try:
            context = super().get_context_data(**kwargs)
            try:
                context['categories'] = Category.objects.all().order_by('name')
            except Exception as e:
                logger.exception(f"Error loading categories: {type(e).__name__}: {e}")
                context['categories'] = []
            context['selected_category'] = self.request.GET.get('category', '')
            context['search_query'] = self.request.GET.get('search', '')
            return context
        except Exception as e:
            logger.exception(f"Error in get_context_data for ProductListView: {type(e).__name__}: {e}")
            # Return safe context if pagination fails
            context = {
                'products': [],
                'categories': [],
                'selected_category': self.request.GET.get('category', ''),
                'search_query': self.request.GET.get('search', ''),
                'is_paginated': False,
                'paginator': None,
                'page_obj': None,
            }
            return context


class ProductDetailView(View):
    """View to display detailed product information with all images - Custom View for better Djongo compatibility"""
    template_name = 'malar_app/product_detail.html'
    
    def get(self, request, sku):
        """Handle GET request to display product details"""
        try:
            # Use filter().first() instead of get() for better Djongo compatibility
            product = Product.objects.filter(sku=sku).first()
            
            if not product:
                raise Http404(f"Product with SKU '{sku}' not found")
            
            # Prepare context with robust error handling
            context = {'product': product}
            
            # Safely get images
            try:
                context['images'] = list(product.images.all())
            except (DatabaseError, Exception) as e:
                logger.exception(f"Error fetching product images for {sku}: {e}")
                context['images'] = []
            
            # Safely get primary image
            try:
                context['primary_image'] = product.images.filter(is_primary=True).first()
            except (DatabaseError, Exception) as e:
                logger.exception(f"Error fetching primary image for {sku}: {e}")
                context['primary_image'] = None
            
            # Safely get stock information
            try:
                context['stock'] = product.stock
            except Stock.DoesNotExist:
                context['stock'] = None
            except (DatabaseError, Exception) as e:
                logger.exception(f"Error fetching stock for {sku}: {e}")
                context['stock'] = None
            
            return render(request, self.template_name, context)
            
        except Http404:
            raise
        except (DatabaseError, Exception) as e:
            logger.exception(f"DatabaseError in ProductDetailView for SKU {sku}: {e}")
            raise Http404("Unable to load product details - database error")



class ProductCreateView(LoginRequiredMixin, AdminRequiredMixin, View):
    """View to create a new product (admin only) - Enhanced form with images and stock"""
    template_name = 'malar_app/custom_product_form.html'
    
    def get(self, request):
        """Show product creation form"""
        try:
            form = CustomProductForm()
            context = {
                'form': form,
                'title': 'Create New Product',
                'page_heading': 'Add New Product',
            }
            return render(request, self.template_name, context)
        except (DatabaseError, Exception) as e:
            logger.exception(f"Error loading product creation form: {type(e).__name__}: {e}")
            # Show form even if there's an error loading related data
            try:
                form = CustomProductForm()
                messages.warning(request, "Some form options may be unavailable. Please try again.")
                return render(request, self.template_name, {'form': form})
            except Exception as e2:
                logger.exception(f"Critical error: cannot create form even with fallback: {e2}")
                messages.error(request, "Error loading form. Please contact support.")
                return redirect('malar_app:product-list')
    
    def post(self, request):
        """Handle product creation with comprehensive error handling"""
        try:
            form = CustomProductForm(request.POST, request.FILES)
            
            
            if form.is_valid():
                try:
                    product = form.save(commit=False)
                    product.save()
                    
                    # Save many-to-many dealers field
                    try:
                        form.save_m2m()
                    except (DatabaseError, Exception) as e:
                        logger.exception(f"Error saving dealers for product {product.sku}: {e}")
                    
                    # Create stock entry with error handling
                    try:
                        initial_stock = form.cleaned_data.get('initial_stock', 0)
                        warehouse_location = form.cleaned_data.get('warehouse_location', '')
                        reorder_level = form.cleaned_data.get('reorder_level', 10)
                        
                        Stock.objects.get_or_create(
                            product=product,
                            defaults={
                                'quantity': initial_stock,
                                'warehouse_location': warehouse_location,
                                'reorder_level': reorder_level
                            }
                        )
                    except (DatabaseError, Exception) as e:
                        logger.exception(f"Error creating stock for product {product.sku}: {e}")
                        messages.warning(request, "Product created but stock information could not be initialized.")
                    
                    # Handle multiple image uploads with error handling
                    try:
                        files = request.FILES.getlist('images')
                        for i, image_file in enumerate(files):
                            is_primary = (i == 0)
                            ProductImage.objects.create(
                                product=product,
                                image=image_file,
                                is_primary=is_primary
                            )
                    except (DatabaseError, Exception) as e:
                        logger.exception(f"Error saving product images for {product.sku}: {e}")
                        messages.warning(request, "Product created but images could not be saved.")
                    
                    messages.success(request, f"✅ Product '{product.name}' created successfully!")
                    return redirect('malar_app:product-detail', sku=product.sku)
                except (DatabaseError, Exception) as e:
                    logger.exception(f"Error creating product: {e}")
                    messages.error(request, "Error creating product. Please try again.")
            else:
                # Form validation errors with detailed feedback
                error_messages = []
                for field, errors in form.errors.items():
                    error_messages.append(f"{field}: {', '.join(errors)}")
                messages.error(request, f"Please correct the errors: {'; '.join(error_messages)}")
            
            return render(request, self.template_name, {'form': form})
        except (DatabaseError, Exception) as e:
            logger.exception(f"Error in product creation: {e}")
            messages.error(request, "Error processing product creation. Please try again.")
            return render(request, self.template_name, {'form': CustomProductForm()})


class ProductUpdateView(LoginRequiredMixin, AdminRequiredMixin, View):
    """View to update product information (admin only) with images and stock"""
    template_name = 'malar_app/custom_product_form.html'
    
    def get(self, request, sku):
        try:
            product = Product.objects.filter(sku=sku).first()
            if not product:
                messages.error(request, "Product not found")
                return redirect('malar_app:product-list')
            form = CustomProductForm(instance=product)
            return render(request, self.template_name, {'form': form, 'object': product})
        except (DatabaseError, Exception) as e:
            logger.error(f"Error loading product {sku} for edit: {e}")
            messages.error(request, "Error loading product. Please try again.")
            return redirect('malar_app:product-list')
    
    def post(self, request, sku):
        try:
            product = Product.objects.filter(sku=sku).first()
            if not product:
                messages.error(request, "Product not found")
                return redirect('malar_app:product-list')
                
            form = CustomProductForm(request.POST, request.FILES, instance=product)
            
            if form.is_valid():
                try:
                    product = form.save(commit=False)
                    product.save()
                    
                    # Save many-to-many dealers field
                    try:
                        form.save_m2m()
                    except (DatabaseError, Exception) as e:
                        logger.error(f"Error saving dealers for product {sku}: {e}")
                    
                    # Update stock entry with error handling
                    try:
                        initial_stock = form.cleaned_data.get('initial_stock', 0)
                        warehouse_location = form.cleaned_data.get('warehouse_location', '')
                        reorder_level = form.cleaned_data.get('reorder_level', 10)
                        
                        stock, created = Stock.objects.get_or_create(product=product)
                        stock.quantity = initial_stock
                        stock.warehouse_location = warehouse_location
                        stock.reorder_level = reorder_level
                        stock.save()
                    except (DatabaseError, Exception) as e:
                        logger.error(f"Error updating stock for product {sku}: {e}")
                        messages.warning(request, "Product updated but stock information could not be updated.")
                    
                    # Handle multiple image uploads with error handling
                    try:
                        files = request.FILES.getlist('images')
                        for i, image_file in enumerate(files):
                            is_primary = (i == 0)
                            ProductImage.objects.create(
                                product=product,
                                image=image_file,
                                is_primary=is_primary
                            )
                    except (DatabaseError, Exception) as e:
                        logger.error(f"Error saving product images for {sku}: {e}")
                        messages.warning(request, "Product updated but some images could not be saved.")
                    
                    messages.success(request, f"✅ Product '{product.name}' updated successfully!")
                    return redirect('malar_app:product-detail', sku=product.sku)
                except (DatabaseError, Exception) as e:
                    logger.error(f"Error saving product {sku}: {e}")
                    messages.error(request, "Error saving product. Please try again.")
            else:
                # Form validation errors with detailed feedback
                error_messages = []
                for field, errors in form.errors.items():
                    error_messages.append(f"{field}: {', '.join(errors)}")
                messages.error(request, f"Please correct the errors: {'; '.join(error_messages)}")
            
            return render(request, self.template_name, {'form': form, 'object': product})
        except Product.DoesNotExist:
            messages.error(request, "Product not found")
            return redirect('malar_app:product-list')
        except (DatabaseError, Exception) as e:
            logger.error(f"Error updating product {sku}: {e}")
            messages.error(request, "Error updating product. Please try again.")
            return redirect('malar_app:product-list')



class ProductDeleteView(LoginRequiredMixin, AdminRequiredMixin, View):
    """View to delete a product (admin only) - Custom View for better Djongo compatibility"""
    template_name = 'malar_app/confirm_delete.html'
    
    def get(self, request, sku):
        """Display delete confirmation"""
        try:
            product = Product.objects.filter(sku=sku).first()
            if not product:
                messages.error(request, f"Product with SKU '{sku}' not found")
                return redirect('malar_app:product-list')
            return render(request, self.template_name, {'object': product})
        except (DatabaseError, Exception) as e:
            logger.error(f"Error loading product {sku} for deletion: {e}")
            messages.error(request, "Error loading product for deletion")
            return redirect('malar_app:product-list')
    
    def post(self, request, sku):
        """Delete the product"""
        try:
            product = Product.objects.filter(sku=sku).first()
            if not product:
                messages.error(request, f"Product with SKU '{sku}' not found")
                return redirect('malar_app:product-list')
            
            product_name = product.name
            product.delete()
            messages.success(request, f"✅ Product '{product_name}' deleted successfully")
            return redirect('malar_app:product-list')
        except (DatabaseError, Exception) as e:
            logger.error(f"Error deleting product {sku}: {e}")
            messages.error(request, "Error deleting product")
            return redirect('malar_app:product-list')


class CategoryListView(ListView):
    """View to list all categories"""
    model = Category
    template_name = 'malar_app/category_list.html'
    context_object_name = 'categories'


class CategoryCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    """View to create a new category"""
    model = Category
    fields = ['name', 'description']
    template_name = 'malar_app/category_form.html'
    success_url = reverse_lazy('malar_app:category-list')
    
    def form_valid(self, form):
        messages.success(self.request, f"✅ Category '{form.cleaned_data['name']}' created successfully!")
        return super().form_valid(form)


class CategoryUpdateView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    """View to update category"""
    model = Category
    fields = ['name', 'description']
    template_name = 'malar_app/category_form.html'
    success_url = reverse_lazy('malar_app:category-list')
    
    def form_valid(self, form):
        messages.success(self.request, f"✅ Category '{self.object.name}' updated successfully!")
        return super().form_valid(form)


class CategoryDeleteView(LoginRequiredMixin, AdminRequiredMixin, DeleteView):
    """View to delete category"""
    model = Category
    template_name = 'malar_app/category_confirm_delete.html'
    success_url = reverse_lazy('malar_app:category-list')


# ===== NEW CUSTOM VIEWS =====

class StockManagementView(LoginRequiredMixin, AdminRequiredMixin, TemplateView):
    """View to manage stock - add, remove, or adjust quantities"""
    template_name = 'malar_app/stock_management.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            # Load all data and filter in Python to avoid Djongo issues
            all_products = list(Product.objects.all())
            active_products = [p for p in all_products if p.is_active]
            context['products'] = active_products
            
            # Filter low stock items in Python
            all_stocks = list(Stock.objects.all())
            low_stock = [s for s in all_stocks if s.quantity <= s.reorder_level]
            context['low_stock_items'] = low_stock
        except Exception as e:
            context['products'] = []
            context['low_stock_items'] = []
            context['error'] = str(e)
        return context
    
    def post(self, request, *args, **kwargs):
        """Handle stock update"""
        product_id = request.POST.get('product_id')
        action = request.POST.get('action')
        
        try:
            quantity = int(request.POST.get('quantity', 0))
        except ValueError:
            messages.error(request, "❌ Invalid quantity - must be a number")
            return redirect('malar_app:stock-management')
        
        try:
            # Get product with specific error handling
            try:
                product = Product.objects.get(id=product_id)
            except Product.DoesNotExist:
                messages.error(request, "❌ Product not found")
                return redirect('malar_app:stock-management')
            
            # Get stock with specific error handling
            try:
                stock = product.stock
            except Stock.DoesNotExist:
                messages.error(request, f"❌ No stock record found for {product.name}")
                return redirect('malar_app:stock-management')
            
            # Validate action
            if action not in ['add', 'remove', 'set']:
                messages.error(request, "❌ Invalid action - must be add, remove, or set")
                return redirect('malar_app:stock-management')
            
            previous_quantity = stock.quantity
            
            if action == 'add':
                stock.quantity += quantity
                change = quantity
            elif action == 'remove':
                change = min(quantity, stock.quantity)
                stock.quantity = max(0, stock.quantity - quantity)
            elif action == 'set':
                change = quantity - stock.quantity
                stock.quantity = quantity
            
            stock.save()
            
            StockHistory.objects.create(
                stock=stock,
                quantity_change=change,
                previous_quantity=previous_quantity,
                new_quantity=stock.quantity,
                action=action,
                notes=request.POST.get('notes', ''),
                performed_by=request.user if request.user.is_authenticated else None
            )
            
            messages.success(request, f"✅ Stock updated for {product.name} ({action}: {quantity})")
        except Exception as e:
            logger.error(f"Unexpected error in stock update: {e}")
            messages.error(request, f"❌ An unexpected error occurred: {str(e)}")
        
        return redirect('malar_app:stock-management')


class AnalyticsDashboardView(LoginRequiredMixin, AdminRequiredMixin, TemplateView):
    """Analytics dashboard with charts and metrics"""
    template_name = 'malar_app/analytics_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        try:
            # Load all data into memory and filter in Python (avoid Djongo issues)
            all_products = list(Product.objects.all())
            all_categories = list(Category.objects.all())
            all_stocks = list(Stock.objects.all())
            
            # Basic metrics - filter in Python
            active_products = [p for p in all_products if p.is_active]
            inactive_products = [p for p in all_products if not p.is_active]
            
            context['total_products'] = len(all_products)
            context['active_products'] = len(active_products)
            context['inactive_products'] = len(inactive_products)
            context['total_categories'] = len(all_categories)
            
            # Stock metrics
            context['total_stock_value'] = sum([
                s.quantity * float(s.product.price) for s in all_stocks
            ])
            context['total_items_in_stock'] = sum([s.quantity for s in all_stocks])
            context['low_stock_count'] = len([s for s in all_stocks if s.quantity <= s.reorder_level])
            
            # Top products
            context['top_products'] = all_products[:5]
            
            # Category breakdown
            category_data = {}
            for product in all_products:
                cat_name = product.category.name
                category_data[cat_name] = category_data.get(cat_name, 0) + 1
            
            context['category_data'] = json.dumps({
                'labels': list(category_data.keys()),
                'data': list(category_data.values())
            })
            
            # Stock status breakdown - filter in Python
            in_stock = len([s for s in all_stocks if s.quantity > 0])
            low_stock = len([s for s in all_stocks if s.quantity <= s.reorder_level and s.quantity > 0])
            out_of_stock = len([s for s in all_stocks if s.quantity == 0])
            
            context['stock_status'] = {
                'in_stock': in_stock,
                'low_stock': low_stock,
                'out_of_stock': out_of_stock,
            }
        except Exception as e:
            import traceback
            context['error'] = str(e)
            context['traceback'] = traceback.format_exc()
        
        return context


class ProductImportView(LoginRequiredMixin, AdminRequiredMixin, View):
    """View for bulk importing products from CSV"""
    template_name = 'malar_app/product_import.html'
    
    def get(self, request):
        form = ProductBulkImportForm()
        return render(request, self.template_name, {'form': form})
    
    def post(self, request):
        form = ProductBulkImportForm(request.POST, request.FILES)
        
        if form.is_valid():
            csv_file = request.FILES['csv_file']
            success_count = 0
            error_count = 0
            errors = []
            
            try:
                # Read CSV
                decoded_file = csv_file.read().decode('utf-8')
                csv_reader = csv.DictReader(StringIO(decoded_file))
                
                for row_num, row in enumerate(csv_reader, start=2):
                    try:
                        # Get or create category
                        category, _ = Category.objects.get_or_create(
                            name=row['category_name'],
                            defaults={'description': ''}
                        )
                        
                        # Create product
                        product = Product.objects.create(
                            name=row['name'],
                            description=row.get('description', ''),
                            sku=row['sku'],
                            price=Decimal(row['price']),
                            category=category,
                            is_active=True
                        )
                        
                        # Create stock entry
                        quantity = int(row.get('quantity', 0))
                        Stock.objects.create(
                            product=product,
                            quantity=quantity,
                            reorder_level=10
                        )
                        
                        success_count += 1
                    except Exception as e:
                        error_count += 1
                        errors.append(f"Row {row_num}: {str(e)}")
                
                messages.success(request, f"✅ Imported {success_count} products successfully!")
                if errors:
                    messages.warning(request, f"⚠️ {error_count} rows failed: {', '.join(errors[:5])}")
                    
            except Exception as e:
                messages.error(request, f"❌ CSV Error: {str(e)}")
        else:
            messages.error(request, "❌ Invalid form submission")
        
        return redirect('malar_app:product-import')


class InventoryReportView(LoginRequiredMixin, AdminRequiredMixin, View):
    """Generate inventory reports in PDF or CSV"""
    template_name = 'malar_app/inventory_report.html'
    
    def get(self, request):
        form = InventoryReportForm()
        return render(request, self.template_name, {'form': form})
    
    def post(self, request):
        form = InventoryReportForm(request.POST)
        
        if form.is_valid():
            report_type = form.cleaned_data['report_type']
            export_format = form.cleaned_data['export_format']
            
            # Get data based on report type (Djongo-safe filtering in Python)
            if report_type == 'all':
                products = list(Product.objects.all())
            elif report_type == 'low_stock':
                # Load all products and filter in Python (Djongo-safe)
                all_products = list(Product.objects.all())
                products = []
                for p in all_products:
                    try:
                        stock = p.stock
                        if stock and stock.quantity <= stock.reorder_level:
                            products.append(p)
                    except Stock.DoesNotExist:
                        pass
            elif report_type == 'category':
                category = form.cleaned_data.get('category')
                if category:
                    products = [p for p in list(Product.objects.all()) if p.category_id == category.id]
                else:
                    products = list(Product.objects.all())
            elif report_type == 'inactive':
                # Load all and filter inactive in Python (Djongo-safe)
                all_products = list(Product.objects.all())
                products = [p for p in all_products if not p.is_active]
            else:
                products = list(Product.objects.all())
            
            if export_format == 'csv':
                return self.generate_csv(products)
            elif export_format == 'pdf':
                return self.generate_pdf(products)
        
        return redirect('inventory-report')
    
    def generate_csv(self, products):
        """Generate CSV report"""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="inventory_report_{datetime.now().strftime("%Y%m%d")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Product Name', 'SKU', 'Category', 'Price', 'Stock Quantity', 'Warehouse Location', 'Status'])
        
        for product in products:
            try:
                stock = product.stock
                qty = stock.quantity
                location = stock.warehouse_location
            except:
                qty = 'N/A'
                location = 'N/A'
            
            writer.writerow([
                product.name,
                product.sku,
                product.category.name,
                product.price,
                qty,
                location,
                'Active' if product.is_active else 'Inactive'
            ])
        
        return response
    
    def generate_pdf(self, products):
        """Generate PDF report (requires reportlab)"""
        try:
            from reportlab.lib.pagesizes import letter, A4
            from reportlab.lib import colors
            from reportlab.lib.units import inch
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet
            
            response = HttpResponse(content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="inventory_report_{datetime.now().strftime("%Y%m%d")}.pdf"'
            
            doc = SimpleDocTemplate(response, pagesize=letter)
            story = []
            styles = getSampleStyleSheet()
            
            # Title
            title = Paragraph(f"<b>Inventory Report - {datetime.now().strftime('%Y-%m-%d')}</b>", styles['Title'])
            story.append(title)
            story.append(Spacer(1, 0.3*inch))
            
            # Table data
            data = [['Product Name', 'SKU', 'Category', 'Price', 'Stock', 'Location', 'Status']]
            for product in products:
                try:
                    stock = product.stock
                    qty = stock.quantity
                    location = stock.warehouse_location
                except:
                    qty = 'N/A'
                    location = 'N/A'
                
                data.append([
                    product.name[:20],
                    product.sku,
                    product.category.name[:15],
                    f"${product.price}",
                    str(qty),
                    location[:20],
                    'Active' if product.is_active else 'Inactive'
                ])
            
            # Create table
            table = Table(data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
            ]))
            story.append(table)
            
            doc.build(story)
            return response
        except ImportError:
            return redirect('inventory-report')


# ===== CUSTOMER MANAGEMENT VIEWS =====

class CustomerListView(LoginRequiredMixin, ListView):
    """View to display all customers"""
    model = Customer
    template_name = 'malar_app/customer_list.html'
    context_object_name = 'customers'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Customer.objects.all()
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(name__icontains=search) | queryset.filter(email__icontains=search)
        return queryset


class CustomerDetailView(LoginRequiredMixin, DetailView):
    """View to display single customer details"""
    model = Customer
    template_name = 'malar_app/customer_detail.html'
    context_object_name = 'customer'
    pk_url_kwarg = 'pk'


class CustomerCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    """View to create a new customer"""
    model = Customer
    form_class = CustomerForm
    template_name = 'malar_app/customer_form.html'
    success_url = reverse_lazy('malar_app:customer-list')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"✅ Customer '{self.object.name}' created successfully!")
        return response


class CustomerUpdateView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    """View to update customer details"""
    model = Customer
    form_class = CustomerForm
    template_name = 'malar_app/customer_form.html'
    pk_url_kwarg = 'pk'
    success_url = reverse_lazy('malar_app:customer-list')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"✅ Customer '{self.object.name}' updated successfully!")
        return response


class CustomerDeleteView(LoginRequiredMixin, AdminRequiredMixin, DeleteView):
    """View to delete a customer"""
    model = Customer
    template_name = 'malar_app/customer_confirm_delete.html'
    pk_url_kwarg = 'pk'
    success_url = reverse_lazy('malar_app:customer-list')


# ===== DEALER MANAGEMENT VIEWS =====

class DealerListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    """View to display all dealers"""
    model = Dealer
    template_name = 'malar_app/dealer_list.html'
    context_object_name = 'dealers'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Dealer.objects.all()
        search = self.request.GET.get('search')
        
        if search:
            queryset = queryset.filter(name__icontains=search) | queryset.filter(email__icontains=search) | queryset.filter(city__icontains=search)
        
        return queryset.order_by('-is_active', 'name')


class DealerDetailView(LoginRequiredMixin, AdminRequiredMixin, DetailView):
    """View to display single dealer details"""
    model = Dealer
    template_name = 'malar_app/dealer_detail.html'
    context_object_name = 'dealer'
    pk_url_kwarg = 'pk'


class DealerCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    """View to create a new dealer"""
    model = Dealer
    form_class = DealerForm
    template_name = 'malar_app/dealer_form.html'
    success_url = reverse_lazy('malar_app:dealer-list')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"✅ Dealer '{self.object.name}' created successfully!")
        return response


class DealerUpdateView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    """View to update dealer details"""
    model = Dealer
    form_class = DealerForm
    template_name = 'malar_app/dealer_form.html'
    pk_url_kwarg = 'pk'
    success_url = reverse_lazy('malar_app:dealer-list')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"✅ Dealer '{self.object.name}' updated successfully!")
        return response


class DealerDeleteView(LoginRequiredMixin, AdminRequiredMixin, DeleteView):
    """View to delete a dealer"""
    model = Dealer
    template_name = 'malar_app/dealer_confirm_delete.html'
    pk_url_kwarg = 'pk'
    success_url = reverse_lazy('malar_app:dealer-list')


# ===== INVOICE MANAGEMENT VIEWS =====

class InvoiceListView(LoginRequiredMixin, ListView):
    """View to display all invoices"""
    model = Invoice
    template_name = 'malar_app/invoice_list.html'
    context_object_name = 'invoices'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Invoice.objects.select_related('customer')
        search = self.request.GET.get('search')
        status = self.request.GET.get('status')
        
        if search:
            queryset = queryset.filter(invoice_number__icontains=search) | queryset.filter(customer__name__icontains=search)
        if status:
            queryset = queryset.filter(status=status)
        
        return queryset


class InvoiceDetailView(LoginRequiredMixin, DetailView):
    """View to display single invoice"""
    model = Invoice
    template_name = 'malar_app/invoice_detail.html'
    context_object_name = 'invoice'
    pk_url_kwarg = 'pk'


class InvoiceDetailPDFView(LoginRequiredMixin, DetailView):
    """View to download invoice as PDF"""
    model = Invoice
    pk_url_kwarg = 'pk'
    
    def get(self, request, *args, **kwargs):
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.lib import colors
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
        
        invoice = self.get_object()
        
        # Validate invoice has items
        if not invoice.items.exists():
            messages.error(request, "Cannot generate PDF for invoice with no line items. Please add items first.")
            return redirect('malar_app:invoice-detail', pk=invoice.pk)
        
        # Create PDF in memory
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
        elements = []
        
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1f4788'),
            spaceAfter=30,
            alignment=TA_CENTER
        )
        
        # Title
        elements.append(Paragraph("INVOICE", title_style))
        
        # Invoice header info
        header_data = [
            ['Invoice #:', invoice.invoice_number, 'Invoice Date:', invoice.invoice_date.strftime('%b %d, %Y')],
            ['Due Date:', invoice.due_date.strftime('%b %d, %Y') if invoice.due_date else 'N/A', 'Status:', invoice.get_status_display().upper()],
        ]
        header_table = Table(header_data)
        header_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Customer and Company info
        customer_data = [
            ['Bill To:', 'Invoice From:'],
            [f"{invoice.customer.name}\n{invoice.customer.get_full_address()}\nEmail: {invoice.customer.email}\nPhone: {invoice.customer.phone}", 
             'Inventory Management System\nInventory Pro'],
        ]
        customer_table = Table(customer_data, colWidths=[3.5*inch, 3*inch])
        customer_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        elements.append(customer_table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Line items table - now guaranteed to have items
        items_data = [['Product', 'SKU', 'Quantity', 'Unit Price', 'Total']]
        for item in invoice.items.all():
            items_data.append([
                item.product.name[:30],
                item.product.sku,
                str(item.quantity),
                f"${item.unit_price:.2f}",
                f"${item.line_total:.2f}"
            ])
        
        items_table = Table(items_data, colWidths=[2.5*inch, 1.2*inch, 1*inch, 1.2*inch, 1*inch])
        items_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4788')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ALIGN', (0, 1), (3, -1), 'RIGHT'),
        ]))
        elements.append(items_table)
        elements.append(Spacer(1, 0.2*inch))
        
        # Totals section
        totals_data = [
            ['', 'Subtotal:', f"${invoice.subtotal:.2f}"],
            ['', 'Tax ({:.2f}%):'.format(invoice.tax_percentage), f"${invoice.tax_amount:.2f}"],
            ['', 'TOTAL:', f"${invoice.total_amount:.2f}"],
        ]
        
        if invoice.amount_paid > 0:
            totals_data.append(['', 'Amount Paid:', f"${invoice.amount_paid:.2f}"])
            totals_data.append(['', 'Outstanding:', f"${invoice.get_outstanding_amount():.2f}"])
        
        totals_table = Table(totals_data, colWidths=[3.5*inch, 1.5*inch, 1.5*inch])
        totals_table.setStyle(TableStyle([
            ('FONTNAME', (0, 2), (-1, 2), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BACKGROUND', (0, 2), (-1, 2), colors.HexColor('#f0f0f0')),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ]))
        elements.append(totals_table)
        elements.append(Spacer(1, 0.2*inch))
        
        # Payment info
        if invoice.payment_status != 'pending':
            payment_data = [
                ['Payment Status:', invoice.get_payment_status_display()],
                ['Payment Date:', invoice.payment_date.strftime('%b %d, %Y') if invoice.payment_date else 'N/A'],
                ['Payment Method:', invoice.get_payment_method_display() if invoice.payment_method else 'N/A'],
            ]
            payment_table = Table(payment_data)
            payment_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f9f9f9')),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            elements.append(payment_table)
        
        # Notes
        if invoice.notes:
            elements.append(Spacer(1, 0.2*inch))
            elements.append(Paragraph("<b>Notes:</b>", styles['Normal']))
            elements.append(Paragraph(invoice.notes, styles['Normal']))
        
        # Build PDF
        doc.build(elements)
        buffer.seek(0)
        
        # Return PDF response
        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Invoice_{invoice.invoice_number}.pdf"'
        return response


class InvoiceCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    """View to create a new invoice"""
    model = Invoice
    form_class = InvoiceForm
    template_name = 'malar_app/invoice_form.html'
    
    def get(self, request, *args, **kwargs):
        """Handle GET request with error handling"""
        try:
            customer_count = Customer.objects.count()
            if customer_count == 0:
                messages.warning(request, "⚠️ No customers found. Please create a customer first.")
        except Exception as e:
            logger.error(f"Error checking customers: {e}")
        
        return super().get(request, *args, **kwargs)
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        # Generate invoice number
        from django.utils import timezone
        count = Invoice.objects.count() + 1
        form.instance.invoice_number = f"INV-{timezone.now().strftime('%Y%m%d')}-{count:04d}"
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('malar_app:invoice-detail', kwargs={'pk': self.object.pk})


class InvoiceUpdateView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    """View to update invoice"""
    model = Invoice
    form_class = InvoiceForm
    template_name = 'malar_app/invoice_form.html'
    pk_url_kwarg = 'pk'
    
    def get_success_url(self):
        return reverse_lazy('malar_app:invoice-detail', kwargs={'pk': self.object.pk})


class InvoiceDeleteView(LoginRequiredMixin, AdminRequiredMixin, DeleteView):
    """View to delete invoice"""
    model = Invoice
    template_name = 'malar_app/invoice_confirm_delete.html'
    pk_url_kwarg = 'pk'
    success_url = reverse_lazy('malar_app:invoice-list')


class InvoiceLineItemCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    """View to add line items to invoice"""
    model = InvoiceLineItem
    form_class = InvoiceLineItemForm
    template_name = 'malar_app/invoice_lineitem_form.html'
    
    def form_valid(self, form):
        invoice_id = self.kwargs.get('invoice_pk')
        form.instance.invoice_id = invoice_id
        response = super().form_valid(form)
        
        # Recalculate invoice total
        invoice = Invoice.objects.get(pk=invoice_id)
        invoice.calculate_total()
        invoice.save()
        
        return response
    
    def get_success_url(self):
        return reverse_lazy('malar_app:invoice-detail', kwargs={'pk': self.kwargs.get('invoice_pk')})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['invoice'] = Invoice.objects.get(pk=self.kwargs.get('invoice_pk'))
        return context


class InvoiceLineItemDeleteView(LoginRequiredMixin, AdminRequiredMixin, DeleteView):
    """View to delete line item from invoice"""
    model = InvoiceLineItem
    template_name = 'malar_app/invoice_lineitem_confirm_delete.html'
    pk_url_kwarg = 'pk'
    
    def get_success_url(self):
        invoice_pk = self.object.invoice.pk
        invoice = Invoice.objects.get(pk=invoice_pk)
        invoice.calculate_total()
        invoice.save()
        return reverse_lazy('malar_app:invoice-detail', kwargs={'pk': invoice_pk})


# ===== API VIEWS =====

class ProductSearchAPIView(View):
    """API view to search products (returns JSON)"""
    
    def get(self, request):
        try:
            query = request.GET.get('q', '').lower()
            # Load all products into memory for filtering (avoid Djongo query issues)
            all_products = list(Product.objects.all())
            
            # Filter active products and search results in Python
            active_products = [p for p in all_products if p.is_active]
            
            if query:
                # Filter in Python to avoid Djongo compatibility issues
                active_products = [p for p in active_products if query in p.name.lower() or query in p.sku.lower()]
            
            results = []
            for p in active_products[:10]:
                try:
                    stock_qty = p.stock.quantity
                except Stock.DoesNotExist:
                    stock_qty = 0
                
                results.append({
                    'id': p.id,
                    'name': p.name,
                    'sku': p.sku,
                    'price': str(p.price),
                    'stock': stock_qty,
                    'category': p.category.name
                })
            
            return JsonResponse({'products': results})
        except Exception as e:
            return JsonResponse({'products': [], 'error': str(e)}, status=400)


class ProductAutoCompleteAPIView(View):
    """API view for product autocomplete"""
    
    def get(self, request):
        try:
            query = request.GET.get('q', '').lower()
            if len(query) < 2:
                return JsonResponse({'results': []})
            
            # Load all products and filter in Python (avoid Djongo issues)
            all_products = list(Product.objects.all())
            active_products = [p for p in all_products if p.is_active]
            products = [p for p in active_products if query in p.name.lower()][:5]
            
            results = [{'id': p.id, 'name': f"{p.name} ({p.sku})", 'sku': p.sku} for p in products]
            return JsonResponse({'results': results})
        except Exception as e:
            return JsonResponse({'results': [], 'error': str(e)}, status=400)


class DashboardStatsAPIView(View):
    """API view for dashboard statistics"""
    
    def get(self, request):
        try:
            # Load all data into memory and filter in Python (avoid Djongo issues)
            all_products = list(Product.objects.all())
            all_categories = list(Category.objects.all())
            all_customers = list(Customer.objects.all())
            all_stocks = list(Stock.objects.all())
            
            # Filter active products
            active_products = [p for p in all_products if p.is_active]
            
            # Count low stock
            low_stock = len([s for s in all_stocks if s.quantity <= s.reorder_level])
            
            # Calculate inventory value
            total_stock_value = 0
            for s in all_stocks:
                try:
                    price_val = float(s.product.price)
                    total_stock_value += price_val * s.quantity
                except:
                    pass
            
            return JsonResponse({
                'total_products': len(active_products),
                'total_categories': len(all_categories),
                'total_customers': len(all_customers),
                'low_stock': low_stock,
                'total_stock_value': str(total_stock_value)
            })
        except Exception as e:
            return JsonResponse({
                'total_products': 0,
                'total_categories': 0,
                'total_customers': 0,
                'low_stock': 0,
                'total_stock_value': '0',
                'error': str(e)
            }, status=400)

# ===== DEALER VIEWS =====

class DealerListView(ListView):
    model = Dealer
    template_name = 'malar_app/dealer_list.html'
    context_object_name = 'dealers'
    paginate_by = 10

    def get_queryset(self):
        query = self.request.GET.get('search')
        if query:
            from django.db.models import Q
            return Dealer.objects.filter(
                Q(name__icontains=query) | 
                Q(email__icontains=query) | 
                Q(city__icontains=query)
            )
        return Dealer.objects.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        return context


class DealerCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    model = Dealer
    form_class = DealerForm
    template_name = 'malar_app/dealer_form.html'
    success_url = reverse_lazy('malar_app:dealer-list')

    def form_valid(self, form):
        messages.success(self.request, f"Dealer '{form.cleaned_data['name']}' created successfully!")
        return super().form_valid(form)


class DealerUpdateView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    model = Dealer
    form_class = DealerForm
    template_name = 'malar_app/dealer_form.html'
    success_url = reverse_lazy('malar_app:dealer-list')

    def form_valid(self, form):
        messages.success(self.request, f"Dealer '{form.cleaned_data['name']}' updated successfully!")
        return super().form_valid(form)


class DealerDeleteView(LoginRequiredMixin, AdminRequiredMixin, DeleteView):
    model = Dealer
    template_name = 'malar_app/confirm_delete.html'
    success_url = reverse_lazy('malar_app:dealer-list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Delete Dealer"
        context['message'] = f"Are you sure you want to delete the dealer '{self.object.name}'?"
        context['cancel_url'] = reverse_lazy('malar_app:dealer-list')
        return context


# ===== PURCHASE VIEWS =====

class PurchaseListView(ListView):
    model = Purchase
    template_name = 'malar_app/purchase_list.html'
    context_object_name = 'purchases'
    paginate_by = 10


class PurchaseCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    model = Purchase
    form_class = PurchaseForm
    template_name = 'malar_app/purchase_form.html'
    success_url = reverse_lazy('malar_app:purchase-list')

    def form_valid(self, form):
        response = super().form_valid(form)
        # Increase product stock
        purchase = self.object
        stock, created = Stock.objects.get_or_create(product=purchase.product)
        previous_quantity = stock.quantity
        stock.quantity += purchase.quantity
        stock.save()
        
        # Log to StockHistory
        StockHistory.objects.create(
            stock=stock,
            quantity_change=purchase.quantity,
            previous_quantity=previous_quantity,
            new_quantity=stock.quantity,
            action='add',
            notes=f"Purchase {purchase.purchase_id} added.",
            performed_by=self.request.user if self.request.user.is_authenticated else None
        )
        
        messages.success(self.request, f"Purchase '{purchase.purchase_id}' recorded! Stock increased by {purchase.quantity}.")
        return response


# ===== SALE VIEWS =====

class SaleListView(ListView):
    model = Sale
    template_name = 'malar_app/sale_list.html'
    context_object_name = 'sales'
    paginate_by = 10


class SaleDetailView(LoginRequiredMixin, DetailView):
    model = Sale
    template_name = 'malar_app/sale_detail.html'
    context_object_name = 'sale'


class SaleCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    model = Sale
    form_class = SaleForm
    template_name = 'malar_app/sale_form.html'
    success_url = reverse_lazy('malar_app:sale-list')

    def form_valid(self, form):
        sale = form.save(commit=False)
        stock, created = Stock.objects.get_or_create(product=sale.product)
        
        if stock.quantity < sale.quantity:
            form.add_error('quantity', f"Insufficient stock! Only {stock.quantity} available.")
            return self.form_invalid(form)
            
        # Decrease stock
        previous_quantity = stock.quantity
        stock.quantity -= sale.quantity
        stock.save()
        
        # Save sale
        response = super().form_valid(form)
        
        # Log to StockHistory
        StockHistory.objects.create(
            stock=stock,
            quantity_change=-sale.quantity,
            previous_quantity=previous_quantity,
            new_quantity=stock.quantity,
            action='sale',
            notes=f"Sale {sale.sale_id} processed.",
            performed_by=self.request.user if self.request.user.is_authenticated else None
        )
        
        messages.success(self.request, f"Sale '{sale.sale_id}' recorded! Stock decreased by {sale.quantity}.")
        return response