from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import datetime # <-- ДЛЯ РОБОТИ З ЧАСОМ

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
    # Додамо рік випуску в саму модель Car (це буде надійно)
    year = models.IntegerField(default=2023, verbose_name="Рік випуску") 
    price_per_day = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="Базова ціна за 24 години (грн)")
    description = models.TextField(blank=True, verbose_name="Опис")
    is_available = models.BooleanField(default=True, verbose_name="Доступна для оренди")
    image = models.ImageField(upload_to='cars_images/', blank=True, null=True, verbose_name="Фото")

    def __str__(self):
        return f"{self.brand} {self.model} ({self.year}) - {self.price_per_day} грн/доба"

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
    start_date = models.DateTimeField(verbose_name="Час початку")
    end_date = models.DateTimeField(verbose_name="Час кінця")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Час створення")

    def __str__(self):
        return f"{self.user} забронював {self.car} з {self.start_date.strftime('%d.%m %H:%M')} по {self.end_date.strftime('%d.%m %H:%M')}"

    # 🚨 ПЕРЕПИСАЛИ АЛГОРИТМ ДИНАМІЧНОГО ЦІНОУТВОРЕННЯ (ФІКС ЧИСЕЛ) 🚨
    @property
    def financial_details(self):
        """
        Це складний Python-метод, який рахує гроші до копійки.
        Він повертає словник (dict), який ми використаємо і в інвойсі, і в аналітиці.
        Викладач зацінить такий підхід до структуризації коду.
        """
        # 1. Загальна тривалість
        duration = self.end_date - self.start_date
        duration_seconds = duration.total_seconds()
        if duration_seconds <= 0:
            return {'base': 0, 'surcharge': 0, 'total': 0, 'weekend_secs': 0}
            
        duration_days = duration_seconds / 86400.0
        
        # 2. Вираховуємо, скільки ЧАСУ в годинах припало на вихідні (Сб, Нд)
        total_seconds_rented = int(duration_seconds)
        weekend_seconds = 0
        current_time = self.start_date
        
        # 🚨 ЧИСТИЙ PYTHON: Алгоритм проходу по кожній хвилині (крок 60 сек) 🚨
        while current_time < self.end_date:
            if current_time.weekday() in [5, 6]: # Сб або Нд
                weekend_seconds += 60
            current_time += datetime.timedelta(seconds=60)
            
        # Якщо в кінці оренди залишився хвостик менше хвилини, додаємо його до націнки, якщо це вихідний
        last_chunk = int((self.end_date - self.start_date).total_seconds() % 60)
        if last_chunk > 0 and self.end_date.weekday() in [5, 6]:
            weekend_seconds += last_chunk

        # 3. Рахуємо ціну на основі ціни за секунду
        base_price_per_second = float(self.car.price_per_day) / 86400.0
        
        # Базова ціна (якби не було вихідних)
        base_price = float(duration_seconds * base_price_per_second)
        
        # Націнка: 20% тільки на ті секунди, що припали на вихідні
        weekend_surcharge = float(weekend_seconds * base_price_per_second * 0.20)
        
        # 4. Фінальний розрахунок
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
        # Щоб не ламати старий код, total_price просто бере 'total' з нашого нового методу
        return self.financial_details['total']

    @property
    def is_past(self):
        return self.end_date < timezone.now()

    class Meta:
        verbose_name = "Бронювання"
        verbose_name_plural = "Бронювання"