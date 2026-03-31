from django.contrib import admin
from .models import Car, Booking, Category, Review, UserProfile, PromoCode

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)

@admin.register(Car)
class CarAdmin(admin.ModelAdmin):
    list_display = ('brand', 'model', 'year', 'category', 'price_per_day', 'is_available', 'trips_since_last_service')
    list_filter = ('is_available', 'category', 'brand', 'year')
    search_fields = ('brand', 'model')
    
    actions = ['perform_maintenance']

    @admin.action(description="🛠️ Провести ТО (Скинути лічильник поїздок та повернути в оренду)")
    def perform_maintenance(self, request, queryset):
        updated_count = queryset.update(trips_since_last_service=0, is_available=True)
        self.message_user(request, f"Успішно проведено ТО для {updated_count} автомобілів. Вони знову в каталозі!")

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('car', 'user', 'start_date', 'end_date', 'paid_with_balance', 'promo_code', 'created_at')

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('car', 'user', 'rating', 'created_at')
    list_filter = ('rating', 'car')

# 🚨 ОНОВЛЕНО: Тепер використовуємо is_verified замість documents_verified 🚨
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'birth_date', 'driving_experience', 'is_verified', 'loyalty_balance', 'get_vip_status')
    list_editable = ('is_verified',) # Змінили назву поля тут
    search_fields = ('user__username',)

    def get_vip_status(self, obj):
        return obj.vip_status
    get_vip_status.short_description = 'VIP Статус'

@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_percent', 'valid_until', 'current_uses', 'usage_limit', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('code',)