from django.shortcuts import render
from .models import Car

def car_list(request):
    # Отримуємо всі машини з бази даних
    cars = Car.objects.all()
    # Передаємо їх у шаблон (який зараз створимо)
    return render(request, 'cars/car_list.html', {'cars': cars})