from django.shortcuts import render, get_object_or_404, redirect
from .models import Car, Booking, Category # <-- Додали Category
from .forms import BookingForm
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
import csv
from django.http import HttpResponse, JsonResponse

def car_list(request):
    cars = Car.objects.filter(is_available=True)
    categories = Category.objects.all() # <-- Отримуємо всі категорії для меню
    
    query = request.GET.get('q')
    max_price = request.GET.get('max_price')
    category_id = request.GET.get('category') # <-- Отримуємо вибрану категорію
    
    if query:
        cars = cars.filter(Q(brand__icontains=query) | Q(model__icontains=query))
        
    if max_price:
        try:
            cars = cars.filter(price_per_day__lte=float(max_price))
        except ValueError:
            pass
            
    if category_id: # <-- Фільтруємо по категорії
        cars = cars.filter(category_id=category_id)
            
    return render(request, 'cars/car_list.html', {
        'cars': cars,
        'categories': categories,
        'query': query,
        'max_price': max_price,
        'selected_category': category_id,
    })

def car_detail(request, pk):
    car = get_object_or_404(Car, pk=pk)

    if request.method == 'POST':
        form = BookingForm(request.POST)
        if form.is_valid():
            start = form.cleaned_data['start_date']
            end = form.cleaned_data['end_date']

            if end < start:
                form.add_error(None, "Дата закінчення не може бути раніше початку!")
            else:
                is_overlap = Booking.objects.filter(
                    car=car,
                    start_date__lte=end,
                    end_date__gte=start
                ).exists()

                if is_overlap:
                    form.add_error(None, "Вибачте, на ці дати машина вже заброньована! Спробуйте інші дати.")
                else:
                    booking = form.save(commit=False)
                    booking.car = car
                    booking.user = request.user
                    booking.save()
                    return redirect('car_list')
    else:
        form = BookingForm()

    return render(request, 'cars/car_detail.html', {'car': car, 'form': form})

@login_required
def my_bookings(request):
    bookings = Booking.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'cars/my_bookings.html', {'bookings': bookings})

def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('car_list')
    else:
        form = UserCreationForm()
    return render(request, 'registration/signup.html', {'form': form})

@login_required
def cancel_booking(request, pk):
    booking = get_object_or_404(Booking, pk=pk, user=request.user)
    
    if request.method == 'POST':
        booking.delete()
        return redirect('my_bookings')
    
    return redirect('my_bookings')

@login_required
def export_bookings_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="financial_report.csv"'
    
    response.write('\ufeff'.encode('utf8'))
    writer = csv.writer(response, delimiter=';')
    writer.writerow(['Автомобіль', 'Дата початку', 'Дата завершення', 'Кількість днів', 'Ціна за добу (грн)', 'Загальна сума (грн)', 'Статус'])

    bookings = Booking.objects.filter(user=request.user).order_by('-created_at')

    for b in bookings:
        duration = (b.end_date - b.start_date).days
        if duration <= 0:
            duration = 1
            
        writer.writerow([
            f"{b.car.brand} {b.car.model}",
            b.start_date.strftime("%d.%m.%Y"),
            b.end_date.strftime("%d.%m.%Y"),
            duration,
            b.car.price_per_day,
            b.total_price,
            b.status_label
        ])

    return response

def car_suggestions(request):
    query = request.GET.get('q', '')
    if query:
        cars = Car.objects.filter(Q(brand__icontains=query) | Q(model__icontains=query))[:5]
        results = [f"{car.brand} {car.model}" for car in cars]
        results = list(set(results))
    else:
        results = []
        
    return JsonResponse({'suggestions': results})