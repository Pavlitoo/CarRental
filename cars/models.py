from django.db import models
from django.contrib.auth.models import User

class Car(models.Model):
    brand = models.CharField(max_length=50, verbose_name="Марка")
    model = models.CharField(max_length=50, verbose_name="Модель")
    price_per_day = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="Ціна за добу (грн)")
    description = models.TextField(blank=True, verbose_name="Опис")
    is_available = models.BooleanField(default=True, verbose_name="Доступна для оренди")
    image = models.ImageField(upload_to='cars_images/', blank=True, null=True, verbose_name="Фото")

    def __str__(self):
        return f"{self.brand} {self.model} - {self.price_per_day} грн"

    class Meta:
        verbose_name = "Автомобіль"
        verbose_name_plural = "Автомобілі"

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
        # Рахуємо різницю в днях
        duration = (self.end_date - self.start_date).days
        # Якщо бронювання на 1 день або менше, рахуємо як 1 день
        if duration <= 0:
            duration = 1
        return duration * self.car.price_per_day

    class Meta:
        verbose_name = "Бронювання"
        verbose_name_plural = "Бронювання"