from django.db import models

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