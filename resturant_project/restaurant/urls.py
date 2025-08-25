from django.urls import path
from .views import (
    MenuListCreateView, MenuDetailView,
    TableListCreateView, TableDetailView, TableAvailabilityView,
    ReservationListCreateView, ReservationDetailView,
    OrderListView, OrderDetailView, CreateOrderView, UpdateOrderStatusView,
    DailySalesReportView, LowStockAlertView
)

urlpatterns = [
    # Menu
    path('menu', MenuListCreateView.as_view(), name='menu-list'),
    path('menu/<int:pk>', MenuDetailView.as_view(), name='menu-detail'),

    # Tables
    path('tables', TableListCreateView.as_view(), name='table-list'),
    path('tables/<int:pk>', TableDetailView.as_view(), name='table-detail'),
    path('tables/availability', TableAvailabilityView.as_view(), name='table-availability'),

    # Reservations
    path('reservations', ReservationListCreateView.as_view(), name='reservation-list'),
    path('reservations/<int:pk>', ReservationDetailView.as_view(), name='reservation-detail'),

    # Orders
    path('orders', OrderListView.as_view(), name='order-list'),
    path('orders/<int:pk>', OrderDetailView.as_view(), name='order-detail'),
    path('orders/create', CreateOrderView.as_view(), name='order-create'),
    path('orders/<int:pk>/status', UpdateOrderStatusView.as_view(), name='order-status'),

    # Reports
    path('reports/daily-sales', DailySalesReportView.as_view(), name='report-daily-sales'),
    path('reports/low-stock', LowStockAlertView.as_view(), name='report-low-stock'),
]
