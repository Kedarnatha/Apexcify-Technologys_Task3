from django.contrib import admin
from .models import MenuItem, Table, Reservation, Order, OrderItem

@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'inventory_count', 'low_stock_threshold', 'is_active')
    search_fields = ('name',)

@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ('number', 'capacity', 'is_active')

@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ('table', 'customer_name', 'party_size', 'reserved_for', 'duration_minutes', 'status')
    list_filter = ('status', 'table')
    search_fields = ('customer_name', 'customer_phone')

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'table', 'reservation', 'status', 'total', 'created_at')
    list_filter = ('status',)
    inlines = [OrderItemInline]
