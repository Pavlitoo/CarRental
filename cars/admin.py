from django.contrib import admin
from .models import Car

@admin.register(Car)
class CarAdmin(admin.ModelAdmin):
    list_display = ('brand', 'model', 'price_per_day', 'is_available')
    list_filter = ('is_available', 'brand')
    search_fields = ('brand', 'model')