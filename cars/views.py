from django.shortcuts import render, get_object_or_404, redirect # <-- Додай get_object_or_404
from .models import Car, Booking
from .forms import BookingForm
from django.db.models import Q # <-- Це для складних запитів, хоча тут можна і без нього, але хай буде для профі
from django.contrib.auth.decorators import login_required # <-- Додай цей імпорт на самому верху!
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login

def car_list(request):
    cars = Car.objects.all()
    return render(request, 'cars/car_list.html', {'cars': cars})

def car_detail(request, pk):
    car = get_object_or_404(Car, pk=pk)

    if request.method == 'POST':
        form = BookingForm(request.POST)
        if form.is_valid():
            # Отримуємо дати, які ввів юзер
            start = form.cleaned_data['start_date']
            end = form.cleaned_data['end_date']

            # 1. Перевірка: Дата кінця не може бути раніше дати початку
            if end < start:
                form.add_error(None, "Дата закінчення не може бути раніше початку!")
            else:
                # 2. Головна перевірка: Шукаємо перетини в базі
                # Логіка: (Start_New <= End_Old) AND (End_New >= Start_Old)
                is_overlap = Booking.objects.filter(
                    car=car,
                    start_date__lte=end, # Початок старого <= Кінець нового
                    end_date__gte=start  # Кінець старого >= Початок нового
                ).exists()

                if is_overlap:
                    form.add_error(None, "Вибачте, на ці дати машина вже заброньована! Спробуйте інші дати.")
                else:
                    # Якщо все чисто - зберігаємо
                    booking = form.save(commit=False)
                    booking.car = car
                    booking.user = request.user
                    booking.save()
                    return redirect('car_list')
    else:
        form = BookingForm()

    return render(request, 'cars/car_detail.html', {'car': car, 'form': form})

@login_required # Ця штука не пустить сюди незареєстрованих
def my_bookings(request):
    # Шукаємо бронювання, де user = той, хто зараз на сайті
    bookings = Booking.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'cars/my_bookings.html', {'bookings': bookings})


def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user) # Одразу логінимо користувача після реєстрації
            return redirect('car_list')
    else:
        form = UserCreationForm()
    return render(request, 'registration/signup.html', {'form': form})

@login_required
def cancel_booking(request, pk):
    # Шукаємо бронювання. Якщо воно чуже - видасть помилку 404
    booking = get_object_or_404(Booking, pk=pk, user=request.user)
    
    if request.method == 'POST':
        booking.delete()
        return redirect('my_bookings')
    
    # Якщо хтось спробує відкрити це посилання просто так - повернемо назад
    return redirect('my_bookings')