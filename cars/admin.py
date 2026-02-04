from django.contrib import admin
from .models import Car, Booking

@admin.register(Car)
class CarAdmin(admin.ModelAdmin):
    list_display = ('brand', 'model', 'price_per_day', 'is_available')
    list_filter = ('is_available', 'brand')
    search_fields = ('brand', 'model')

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('car', 'user', 'start_date', 'end_date', 'created_at')