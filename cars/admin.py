from django.contrib import admin
from .models import Car, Booking, Category, Review

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)

@admin.register(Car)
class CarAdmin(admin.ModelAdmin):
    list_display = ('brand', 'model', 'category', 'price_per_day', 'is_available')
    list_filter = ('is_available', 'category', 'brand')
    search_fields = ('brand', 'model')

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('car', 'user', 'start_date', 'end_date', 'created_at')

# --- РЕЄСТРАЦІЯ ВІДГУКІВ ---
@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('car', 'user', 'rating', 'created_at')
    list_filter = ('rating', 'car')