from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import datetime
# 🚨 НОВІ ІМПОРТИ ДЛЯ СИГНАЛІВ
from django.db.models.signals import post_save
from django.dispatch import receiver

# --- НОВА МОДЕЛЬ: ПРОФІЛЬ КОРИСТУВАЧА (ВІРТУАЛЬНИЙ ГАМАНЕЦЬ) ---
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile', verbose_name="Користувач")
    loyalty_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Баланс кешбеку (грн)")

    def __str__(self):
        return f"Гаманець {self.user.username}: {self.loyalty_balance} грн"

    class Meta:
        verbose_name = "Профіль клієнта"
        verbose_name_plural = "Профілі клієнтів"

# --- СИГНАЛИ: АВТОМАТИЧНЕ СТВОРЕННЯ ГАМАНЦЯ ДЛЯ НОВИХ ЮЗЕРІВ ---
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()

# ------------------------------------------------------------------

class Category(models.Model):
    name = models.CharField(max_length=50, verbose_name="Назва категорії")
    def __str__(self): return self.name
    class Meta:
        verbose_name = "Категорія"
        verbose_name_plural = "Категорії"

class Car(models.Model):
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Клас авто")
    brand = models.CharField(max_length=50, verbose_name="Марка")
    model = models.CharField(max_length=50, verbose_name="Модель")
    year = models.IntegerField(default=2023, verbose_name="Рік випуску") 
    price_per_day = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="Базова ціна за 24 години (грн)")
    description = models.TextField(blank=True, verbose_name="Опис")
    is_available = models.BooleanField(default=True, verbose_name="Доступна для оренди")
    image = models.ImageField(upload_to='cars_images/', blank=True, null=True, verbose_name="Фото")

    def __str__(self): return f"{self.brand} {self.model} ({self.year}) - {self.price_per_day} грн/доба"

    @property
    def average_rating(self):
        reviews = self.reviews.all()
        if reviews: return round(sum(r.rating for r in reviews) / len(reviews), 1)
        return 0

    class Meta:
        verbose_name = "Автомобіль"
        verbose_name_plural = "Автомобілі"

class Review(models.Model):
    RATING_CHOICES = [(1, '⭐ 1 - Дуже погано'), (2, '⭐⭐ 2 - Погано'), (3, '⭐⭐⭐ 3 - Нормально'), (4, '⭐⭐⭐⭐ 4 - Добре'), (5, '⭐⭐⭐⭐⭐ 5 - Відмінно')]
    car = models.ForeignKey(Car, on_delete=models.CASCADE, related_name='reviews', verbose_name="Авто")
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Клієнт")
    rating = models.IntegerField(choices=RATING_CHOICES, verbose_name="Оцінка")
    comment = models.TextField(verbose_name="Текст відгуку")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата")

    def __str__(self): return f"{self.user} - {self.car} ({self.rating} зірок)"
    class Meta:
        verbose_name = "Відгук"
        verbose_name_plural = "Відгуки"

class Booking(models.Model):
    car = models.ForeignKey(Car, on_delete=models.CASCADE, verbose_name="Авто")
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Клієнт")
    start_date = models.DateTimeField(verbose_name="Час початку")
    end_date = models.DateTimeField(verbose_name="Час кінця")
    
    # 🚨 НОВЕ ПОЛЕ: Скільки оплачено балами
    paid_with_balance = models.DecimalField(max_digits=8, decimal_places=2, default=0.00, verbose_name="Оплачено балами")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Час створення")

    def __str__(self): return f"{self.user} забронював {self.car}"

    @property
    def financial_details(self):
        duration = self.end_date - self.start_date
        duration_seconds = duration.total_seconds()
        if duration_seconds <= 0: return {'base': 0, 'surcharge': 0, 'total': 0, 'weekend_secs': 0}
            
        duration_days = duration_seconds / 86400.0
        
        weekend_seconds = 0
        current_time = self.start_date
        while current_time < self.end_date:
            if current_time.weekday() in [5, 6]: 
                weekend_seconds += 60
            current_time += datetime.timedelta(seconds=60)
            
        last_chunk = int((self.end_date - self.start_date).total_seconds() % 60)
        if last_chunk > 0 and self.end_date.weekday() in [5, 6]:
            weekend_seconds += last_chunk

        base_price_per_second = float(self.car.price_per_day) / 86400.0
        base_price = float(duration_seconds * base_price_per_second)
        weekend_surcharge = float(weekend_seconds * base_price_per_second * 0.20)
        total_price = base_price + weekend_surcharge
        
        return {
            'base': int(base_price),
            'surcharge': int(weekend_surcharge),
            'total': int(total_price),
            'total_days': round(duration_days, 1),
            'weekend_days': round(weekend_seconds / 86400.0, 1) if weekend_seconds > 0 else 0
        }

    @property
    def total_price(self):
        return self.financial_details['total']

    # 🚨 НОВИЙ МЕТОД: Скільки РЕАЛЬНО треба доплатити після зняття балів
    @property
    def amount_due(self):
        return self.total_price - int(self.paid_with_balance)

    @property
    def is_past(self):
        return self.end_date < timezone.now()

    class Meta:
        verbose_name = "Бронювання"
        verbose_name_plural = "Бронювання"

# --- СИГНАЛ: НАРАХУВАННЯ 5% КЕШБЕКУ ПІСЛЯ УСПІШНОГО БРОНЮВАННЯ ---
@receiver(post_save, sender=Booking)
def award_cashback(sender, instance, created, **kwargs):
    if created: # Якщо бронювання щойно створене (а не просто оновлене)
        # Рахуємо 5% від РЕАЛЬНО сплаченої суми (amount_due)
        cashback_earned = int(instance.amount_due * 0.05)
        if cashback_earned > 0:
            profile = instance.user.profile
            profile.loyalty_balance += cashback_earned
            profile.save()