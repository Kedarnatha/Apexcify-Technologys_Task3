from rest_framework import generics, status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db import transaction
from django.db.models import Sum, F
from django.utils import timezone
from django.shortcuts import get_object_or_404

from .models import MenuItem, Table, Reservation, Order, OrderItem
from .serializers import (
    MenuItemSerializer, TableSerializer, ReservationSerializer,
    OrderSerializer, CreateOrderSerializer
)

# ------------ MENU ------------
class MenuListCreateView(generics.ListCreateAPIView):
    queryset = MenuItem.objects.all().order_by('name')
    serializer_class = MenuItemSerializer
    permission_classes = [permissions.AllowAny]  # change to IsAuthenticated for write in prod

class MenuDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = MenuItem.objects.all()
    serializer_class = MenuItemSerializer
    permission_classes = [permissions.AllowAny]

# ------------ TABLES ------------
class TableListCreateView(generics.ListCreateAPIView):
    queryset = Table.objects.all().order_by('number')
    serializer_class = TableSerializer
    permission_classes = [permissions.AllowAny]

class TableDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Table.objects.all()
    serializer_class = TableSerializer
    permission_classes = [permissions.AllowAny]

# Availability check (by time + duration + party size)
class TableAvailabilityView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        """
        Query params:
        - start (ISO datetime): desired start time
        - duration_minutes (int, default 90)
        - party_size (int)
        """
        try:
            start = timezone.datetime.fromisoformat(request.query_params.get('start'))
            if start.tzinfo is None:
                start = timezone.make_aware(start, timezone.get_current_timezone())
        except Exception:
            return Response({"error": "Invalid or missing 'start' datetime (ISO format)."}, status=400)

        duration = int(request.query_params.get('duration_minutes', 90))
        party_size = int(request.query_params.get('party_size', 1))
        end = start + timezone.timedelta(minutes=duration)

        available = []
        for table in Table.objects.filter(is_active=True, capacity__gte=party_size):
            # check overlaps
            overlaps = Reservation.objects.filter(
                table=table, status='booked'
            )
            conflict = False
            for r in overlaps:
                r_end = r.reserved_for + timezone.timedelta(minutes=r.duration_minutes)
                if r.reserved_for < end and start < r_end:
                    conflict = True
                    break
            if not conflict:
                available.append(table)

        data = TableSerializer(available, many=True).data
        return Response(data)

# ------------ RESERVATIONS ------------
class ReservationListCreateView(generics.ListCreateAPIView):
    queryset = Reservation.objects.all().order_by('-reserved_for')
    serializer_class = ReservationSerializer
    permission_classes = [permissions.AllowAny]

class ReservationDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Reservation.objects.all()
    serializer_class = ReservationSerializer
    permission_classes = [permissions.AllowAny]

# ------------ ORDERS ------------
class OrderListView(generics.ListAPIView):
    queryset = Order.objects.all().order_by('-created_at')
    serializer_class = OrderSerializer
    permission_classes = [permissions.AllowAny]

class OrderDetailView(generics.RetrieveAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [permissions.AllowAny]

class CreateOrderView(APIView):
    """
    Body:
    {
      "table": 1,             # OR "reservation": 5
      "items": [
         {"menu_item": 2, "quantity": 3},
         {"menu_item": 5, "quantity": 1}
      ]
    }
    """
    permission_classes = [permissions.AllowAny]

    @transaction.atomic
    def post(self, request):
        serializer = CreateOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        table = None
        reservation = None
        if data.get('table'):
            table = get_object_or_404(Table, pk=data['table'])
        if data.get('reservation'):
            reservation = get_object_or_404(Reservation, pk=data['reservation'])

        # Stock check first (no partial changes)
        items_payload = data['items']
        menu_map = {}
        for item in items_payload:
            mi = get_object_or_404(MenuItem, pk=item['menu_item'], is_active=True)
            if mi.inventory_count < item['quantity']:
                return Response({"error": f"Insufficient stock for '{mi.name}'"}, status=400)
            menu_map[item['menu_item']] = mi

        # Create order + items; deduct stock
        order = Order.objects.create(table=table, reservation=reservation)
        for item in items_payload:
            mi = menu_map[item['menu_item']]
            qty = item['quantity']
            OrderItem.objects.create(
                order=order,
                menu_item=mi,
                quantity=qty,
                unit_price=mi.price
            )
            # deduct stock
            mi.inventory_count = mi.inventory_count - qty
            mi.save(update_fields=['inventory_count'])

        # Finalize total
        order.recalc_total()
        order.save(update_fields=['total'])

        return Response(OrderSerializer(order).data, status=201)

# Mark order PAID / CANCELLED (simple state change)
class UpdateOrderStatusView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        new_status = request.data.get('status')
        if new_status not in ['PAID', 'CANCELLED']:
            return Response({"error": "status must be 'PAID' or 'CANCELLED'."}, status=400)
        order.status = new_status
        order.save(update_fields=['status'])
        return Response(OrderSerializer(order).data)

# ------------ REPORTS (Optional) ------------
class DailySalesReportView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        """
        ?date=YYYY-MM-DD (optional, defaults today)
        Returns total sales and order count for that day (PAID orders).
        """
        date_str = request.query_params.get('date')
        if date_str:
            day = timezone.datetime.fromisoformat(date_str).date()
        else:
            day = timezone.localdate()

        start = timezone.make_aware(timezone.datetime.combine(day, timezone.datetime.min.time()))
        end = timezone.make_aware(timezone.datetime.combine(day, timezone.datetime.max.time()))

        qs = Order.objects.filter(status='PAID', created_at__range=(start, end))
        total_sales = qs.aggregate(s=Sum('total'))['s'] or 0
        count = qs.count()
        return Response({"date": str(day), "orders": count, "total_sales": total_sales})

class LowStockAlertView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        qs = MenuItem.objects.filter(inventory_count__lte=F('low_stock_threshold')).order_by('inventory_count')
        return Response(MenuItemSerializer(qs, many=True).data)
