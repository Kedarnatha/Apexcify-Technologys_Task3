from rest_framework import serializers
from django.utils import timezone
from django.db.models import Q
from .models import MenuItem, Table, Reservation, Order, OrderItem

# -------- Menu & Table --------
class MenuItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = MenuItem
        fields = ['id', 'name', 'description', 'price', 'inventory_count', 'is_active', 'low_stock_threshold']

class TableSerializer(serializers.ModelSerializer):
    class Meta:
        model = Table
        fields = ['id', 'number', 'capacity', 'is_active']

# -------- Reservations --------
class ReservationSerializer(serializers.ModelSerializer):
    reserved_until = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Reservation
        fields = [
            'id', 'table', 'customer_name', 'customer_phone', 'party_size',
            'reserved_for', 'duration_minutes', 'status', 'notes', 'reserved_until'
        ]
        read_only_fields = ['status']

    def validate(self, data):
        table = data['table']
        party_size = data['party_size']
        start = data['reserved_for']
        duration = data.get('duration_minutes', 90)
        if party_size > table.capacity:
            raise serializers.ValidationError("Party size exceeds table capacity.")
        end = start + timezone.timedelta(minutes=duration)

        # overlap check: any existing 'booked' reservation with time overlap
        qs = Reservation.objects.filter(
            table=table,
            status='booked'
        ).filter(
            Q(reserved_for__lt=end) & Q(reserved_for__gte=start) |
            Q(reserved_for__lte=start) & Q(reserved_for__gte=start - timezone.timedelta(minutes=duration))
        )
        # simpler and clearer:
        qs = Reservation.objects.filter(
            table=table, status='booked'
        ).filter(
            reserved_for__lt=end,
            reserved_for__gte=start - timezone.timedelta(minutes=duration)
        )
        # better overlap condition:
        qs = Reservation.objects.filter(table=table, status='booked') \
            .filter(reserved_for__lt=end) \
            .filter(reserved_for__gte=start - timezone.timedelta(minutes=duration))

        # Final explicit overlap logic (classic interval overlap):
        qs = Reservation.objects.filter(table=table, status='booked') \
            .filter(reserved_for__lt=end, reserved_for__gte=start - timezone.timedelta(minutes=duration))

        # To be precise, let's compute overlap against each existing reservation:
        overlaps = Reservation.objects.filter(table=table, status='booked').exclude(pk=self.instance.pk if self.instance else None)
        for r in overlaps:
            r_end = r.reserved_for + timezone.timedelta(minutes=r.duration_minutes)
            if r.reserved_for < end and start < r_end:
                raise serializers.ValidationError("This table is not available for the requested time window.")

        return data

# -------- Orders --------
class OrderItemInputSerializer(serializers.Serializer):
    menu_item = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)

class OrderItemSerializer(serializers.ModelSerializer):
    menu_item_name = serializers.ReadOnlyField(source='menu_item.name')
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ['id', 'menu_item', 'menu_item_name', 'quantity', 'unit_price', 'subtotal']

    def get_subtotal(self, obj):
        return obj.subtotal

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'table', 'reservation', 'status', 'created_at', 'total', 'items']
        read_only_fields = ['status', 'created_at', 'total']

class CreateOrderSerializer(serializers.Serializer):
    table = serializers.IntegerField(required=False)
    reservation = serializers.IntegerField(required=False)
    items = OrderItemInputSerializer(many=True)

    def validate(self, data):
        if not data.get('table') and not data.get('reservation'):
            raise serializers.ValidationError("Provide either table or reservation.")
        return data
