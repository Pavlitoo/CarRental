from django.contrib import admin
from .models import Car, Booking, Category

# Додаємо керування категоріями
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)

@admin.register(Car)
class CarAdmin(admin.ModelAdmin):
    # Додали 'category' в список колонок
    list_display = ('brand', 'model', 'category', 'price_per_day', 'is_available')
    # Додали 'category' у фільтри справа
    list_filter = ('is_available', 'category', 'brand')
    search_fields = ('brand', 'model')

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('car', 'user', 'start_date', 'end_date', 'created_at')