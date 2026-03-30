from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Category(models.Model):
    name = models.CharField(max_length=50, verbose_name="Назва категорії")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Категорія"
        verbose_name_plural = "Категорії"

class Car(models.Model):
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Клас авто")
    brand = models.CharField(max_length=50, verbose_name="Марка")
    model = models.CharField(max_length=50, verbose_name="Модель")
    price_per_day = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="Ціна за добу (грн)")
    description = models.TextField(blank=True, verbose_name="Опис")
    is_available = models.BooleanField(default=True, verbose_name="Доступна для оренди")
    image = models.ImageField(upload_to='cars_images/', blank=True, null=True, verbose_name="Фото")

    def __str__(self):
        return f"{self.brand} {self.model} - {self.price_per_day} грн"

    # Вираховуємо середній рейтинг авто на основі відгуків
    @property
    def average_rating(self):
        reviews = self.reviews.all()
        if reviews:
            return round(sum(r.rating for r in reviews) / len(reviews), 1)
        return 0

    class Meta:
        verbose_name = "Автомобіль"
        verbose_name_plural = "Автомобілі"

# --- НОВА МОДЕЛЬ: ВІДГУКИ ---
class Review(models.Model):
    RATING_CHOICES = [
        (1, '⭐ 1 - Дуже погано'),
        (2, '⭐⭐ 2 - Погано'),
        (3, '⭐⭐⭐ 3 - Нормально'),
        (4, '⭐⭐⭐⭐ 4 - Добре'),
        (5, '⭐⭐⭐⭐⭐ 5 - Відмінно'),
    ]
    # related_name='reviews' дозволяє нам легко отримувати всі відгуки машини: car.reviews.all()
    car = models.ForeignKey(Car, on_delete=models.CASCADE, related_name='reviews', verbose_name="Авто")
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Клієнт")
    rating = models.IntegerField(choices=RATING_CHOICES, verbose_name="Оцінка")
    comment = models.TextField(verbose_name="Текст відгуку")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата")

    def __str__(self):
        return f"{self.user} - {self.car} ({self.rating} зірок)"

    class Meta:
        verbose_name = "Відгук"
        verbose_name_plural = "Відгуки"

class Booking(models.Model):
    car = models.ForeignKey(Car, on_delete=models.CASCADE, verbose_name="Авто")
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Клієнт")
    start_date = models.DateField(verbose_name="Дата початку")
    end_date = models.DateField(verbose_name="Дата кінця")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Час створення")

    def __str__(self):
        return f"{self.user} забронював {self.car} з {self.start_date} по {self.end_date}"

    @property
    def total_price(self):
        duration = (self.end_date - self.start_date).days
        if duration <= 0:
            duration = 1
        base_price = float(duration * self.car.price_per_day)
        
        if duration >= 7:
            discount = base_price * 0.10
        elif duration >= 3:
            discount = base_price * 0.05
        else:
            discount = 0
            
        return int(base_price - discount)

    @property
    def has_discount(self):
        return (self.end_date - self.start_date).days >= 3

    @property
    def is_past(self):
        return self.end_date < timezone.now().date()

    @property
    def status_label(self):
        if self.is_past:
            return "Завершено"
        return "Підтверджено"

    class Meta:
        verbose_name = "Бронювання"
        verbose_name_plural = "Бронювання"