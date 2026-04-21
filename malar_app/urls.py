from django.urls import path
from . import views
from .views import PurchaseCreateView, PurchaseListView, SaleCreateView, SaleListView
from .views import *
app_name = 'malar_app'

urlpatterns = [
    # Authentication URLs
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),
    
    # Home page
    path('', views.HomeView.as_view(), name='home'),
    
    # Admin Dashboard
    path('admin-dashboard/', views.AdminDashboardView.as_view(), name='admin-dashboard'),
    
    # Product URLs - SPECIFIC patterns BEFORE generic patterns
    path('products/', views.ProductListView.as_view(), name='product-list'),
    path('products/create/', views.ProductCreateView.as_view(), name='product-create'),
    path('products/<str:sku>/edit/', views.ProductUpdateView.as_view(), name='product-update'),
    path('products/<str:sku>/delete/', views.ProductDeleteView.as_view(), name='product-delete'),
    path('products/<str:sku>/', views.ProductDetailView.as_view(), name='product-detail'),
    
    # Category URLs - SPECIFIC patterns BEFORE generic patterns
    path('categories/', views.CategoryListView.as_view(), name='category-list'),
    path('categories/create/', views.CategoryCreateView.as_view(), name='category-create'),
    path('categories/<int:pk>/edit/', views.CategoryUpdateView.as_view(), name='category-update'),
    path('categories/<int:pk>/delete/', views.CategoryDeleteView.as_view(), name='category-delete'),
    
    # Custom Pages
    path('stock-management/', views.StockManagementView.as_view(), name='stock-management'),
    path('analytics/', views.AnalyticsDashboardView.as_view(), name='analytics-dashboard'),
    path('product-import/', views.ProductImportView.as_view(), name='product-import'),
    path('inventory-report/', views.InventoryReportView.as_view(), name='inventory-report'),
    
    # Customer URLs - SPECIFIC patterns BEFORE generic patterns
    path('customers/', views.CustomerListView.as_view(), name='customer-list'),
    path('customers/create/', views.CustomerCreateView.as_view(), name='customer-create'),
    path('customers/<int:pk>/edit/', views.CustomerUpdateView.as_view(), name='customer-update'),
    path('customers/<int:pk>/delete/', views.CustomerDeleteView.as_view(), name='customer-delete'),
    path('customers/<int:pk>/', views.CustomerDetailView.as_view(), name='customer-detail'),
    
    # Dealer URLs - SPECIFIC patterns BEFORE generic patterns
    path('dealers/', views.DealerListView.as_view(), name='dealer-list'),
    path('dealers/create/', views.DealerCreateView.as_view(), name='dealer-create'),
    path('dealers/<int:pk>/edit/', views.DealerUpdateView.as_view(), name='dealer-update'),
    path('dealers/<int:pk>/delete/', views.DealerDeleteView.as_view(), name='dealer-delete'),
    path('dealers/<int:pk>/', views.DealerDetailView.as_view(), name='dealer-detail'),
    
    # Invoice URLs - SPECIFIC patterns BEFORE generic patterns
    path('invoices/', views.InvoiceListView.as_view(), name='invoice-list'),
    path('invoices/create/', views.InvoiceCreateView.as_view(), name='invoice-create'),
    path('invoices/<int:pk>/pdf/', views.InvoiceDetailPDFView.as_view(), name='invoice-pdf'),
    path('invoices/<int:pk>/edit/', views.InvoiceUpdateView.as_view(), name='invoice-update'),
    path('invoices/<int:pk>/delete/', views.InvoiceDeleteView.as_view(), name='invoice-delete'),
    path('invoices/<int:pk>/', views.InvoiceDetailView.as_view(), name='invoice-detail'),
    path('invoices/<int:invoice_pk>/items/add/', views.InvoiceLineItemCreateView.as_view(), name='invoice-item-add'),
    path('invoices/items/<int:pk>/delete/', views.InvoiceLineItemDeleteView.as_view(), name='invoice-item-delete'),
    
    # API URLs
    path('api/products/search/', views.ProductSearchAPIView.as_view(), name='product-search-api'),
    path('api/products/autocomplete/', views.ProductAutoCompleteAPIView.as_view(), name='product-autocomplete-api'),
    path('api/dashboard/stats/', views.DashboardStatsAPIView.as_view(), name='dashboard-stats-api'),

    # Purchase URLs
    path('purchases/', views.PurchaseListView.as_view(), name='purchase-list'),
    path('purchases/create/', views.PurchaseCreateView.as_view(), name='purchase-create'),
    path('purchases/add/', views.PurchaseCreateView.as_view(), name='purchase-add'),

    # Sale URLs
    path('sales/', views.SaleListView.as_view(), name='sale-list'),
    path('sales/create/', views.SaleCreateView.as_view(), name='sale-create'),
    path('sales/add/', views.SaleCreateView.as_view(), name='sale-add'),
    path('sales/<int:pk>/', views.SaleDetailView.as_view(), name='sale-detail'),
]