from django.db import models, transaction
from django.utils import timezone
from decimal import Decimal

class MenuItem(models.Model):
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    inventory_count = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    low_stock_threshold = models.IntegerField(default=5)  # for alerts

    def __str__(self):
        return f"{self.name} - ₹{self.price}"

class Table(models.Model):
    number = models.PositiveIntegerField(unique=True)
    capacity = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Table {self.number} (cap {self.capacity})"

class Reservation(models.Model):
    STATUS = (
        ('booked', 'Booked'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    )
    table = models.ForeignKey(Table, on_delete=models.CASCADE, related_name='reservations')
    customer_name = models.CharField(max_length=120)
    customer_phone = models.CharField(max_length=20, blank=True)
    party_size = models.PositiveIntegerField()
    reserved_for = models.DateTimeField()  # start time
    duration_minutes = models.PositiveIntegerField(default=90)
    status = models.CharField(max_length=20, choices=STATUS, default='booked')
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.customer_name} @ Table {self.table.number} ({self.reserved_for})"

    @property
    def reserved_until(self):
        return self.reserved_for + timezone.timedelta(minutes=self.duration_minutes)

class Order(models.Model):
    STATUS = (
        ('OPEN', 'Open'),
        ('PAID', 'Paid'),
        ('CANCELLED', 'Cancelled'),
    )
    table = models.ForeignKey(Table, null=True, blank=True, on_delete=models.SET_NULL, related_name='orders')
    reservation = models.ForeignKey(Reservation, null=True, blank=True, on_delete=models.SET_NULL, related_name='orders')
    status = models.CharField(max_length=12, choices=STATUS, default='OPEN')
    created_at = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    def __str__(self):
        return f"Order #{self.id} [{self.status}]"

    def recalc_total(self):
        total = Decimal('0.00')
        for item in self.items.all():
            total += item.subtotal
        self.total = total
        return total

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    menu_item = models.ForeignKey(MenuItem, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=8, decimal_places=2)

    @property
    def subtotal(self):
        return self.unit_price * self.quantity

    def __str__(self):
        return f"{self.menu_item.name} x {self.quantity}"
