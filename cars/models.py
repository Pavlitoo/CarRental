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
    price_per_day = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="Ціна за 24 години (грн)")
    description = models.TextField(blank=True, verbose_name="Опис")
    is_available = models.BooleanField(default=True, verbose_name="Доступна для оренди")
    image = models.ImageField(upload_to='cars_images/', blank=True, null=True, verbose_name="Фото")

    def __str__(self):
        return f"{self.brand} {self.model} - {self.price_per_day} грн/доба"

    @property
    def average_rating(self):
        reviews = self.reviews.all()
        if reviews:
            return round(sum(r.rating for r in reviews) / len(reviews), 1)
        return 0

    class Meta:
        verbose_name = "Автомобіль"
        verbose_name_plural = "Автомобілі"

class Review(models.Model):
    RATING_CHOICES = [
        (1, '⭐ 1 - Дуже погано'),
        (2, '⭐⭐ 2 - Погано'),
        (3, '⭐⭐⭐ 3 - Нормально'),
        (4, '⭐⭐⭐⭐ 4 - Добре'),
        (5, '⭐⭐⭐⭐⭐ 5 - Відмінно'),
    ]
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
    
    # 🚨 ЗМІНИЛИ НА DateTimeField (Тепер є і години, і хвилини)
    start_date = models.DateTimeField(verbose_name="Час початку")
    end_date = models.DateTimeField(verbose_name="Час кінця")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Час створення")

    def __str__(self):
        return f"{self.user} забронював {self.car} з {self.start_date.strftime('%d.%m %H:%M')} по {self.end_date.strftime('%d.%m %H:%M')}"

    # 🚨 НОВИЙ АЛГОРИТМ: Рахуємо гроші похвилинно/погодинно
    @property
    def total_price(self):
        # Отримуємо загальну кількість секунд оренди
        duration_seconds = (self.end_date - self.start_date).total_seconds()
        
        # Якщо орендували менше ніж на 1 хвилину, рахуємо як 1 хвилину (60 сек)
        if duration_seconds <= 0:
            duration_seconds = 60
            
        # Переводимо секунди в дробові дні (наприклад, 1.5 дня = 36 годин)
        duration_days = duration_seconds / 86400.0
        
        # Рахуємо точну базову вартість (ціна за день * дробову кількість днів)
        base_price = float(duration_days * float(self.car.price_per_day))
        
        # Знижки залишаємо для тих, хто бере надовго
        if duration_days >= 7:
            discount = base_price * 0.10
        elif duration_days >= 3:
            discount = base_price * 0.05
        else:
            discount = 0
            
        return int(base_price - discount)

    @property
    def has_discount(self):
        duration_seconds = (self.end_date - self.start_date).total_seconds()
        return duration_seconds >= (3 * 86400) # Більше 3 днів у секундах

    @property
    def is_past(self):
        # Порівнюємо з поточним часом
        return self.end_date < timezone.now()

    @property
    def status_label(self):
        if self.is_past:
            return "Завершено"
        return "Підтверджено"

    class Meta:
        verbose_name = "Бронювання"
        verbose_name_plural = "Бронювання"