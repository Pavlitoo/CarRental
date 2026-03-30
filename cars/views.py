from django.shortcuts import render, get_object_or_404, redirect
from .models import Car, Booking, Category, Review
from .forms import BookingForm, ReviewForm
from django.db.models import Q, Count
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.utils import timezone
from django.core.mail import send_mail
from django.http import HttpResponse, JsonResponse
import csv
import json # <-- ДОДАЛИ ДЛЯ ГРАФІКІВ

def car_list(request):
    cars = Car.objects.filter(is_available=True)
    categories = Category.objects.all()
    
    query = request.GET.get('q')
    max_price = request.GET.get('max_price')
    category_id = request.GET.get('category')
    
    if query:
        cars = cars.filter(Q(brand__icontains=query) | Q(model__icontains=query))
        
    if max_price:
        try:
            cars = cars.filter(price_per_day__lte=float(max_price))
        except ValueError:
            pass
            
    if category_id:
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
    reviews = car.reviews.all().order_by('-created_at')

    can_review = False
    if request.user.is_authenticated:
        can_review = Booking.objects.filter(
            user=request.user,
            car=car,
            end_date__lt=timezone.now()
        ).exists()

    form = BookingForm()
    review_form = ReviewForm()

    if request.method == 'POST':
        if 'rating' in request.POST:
            review_form = ReviewForm(request.POST)
            if review_form.is_valid() and can_review:
                review = review_form.save(commit=False)
                review.car = car
                review.user = request.user
                review.save()
                return redirect('car_detail', pk=car.pk)
        
        else:
            form = BookingForm(request.POST)
            if form.is_valid():
                start = form.cleaned_data['start_date']
                end = form.cleaned_data['end_date']

                if end <= start:
                    form.add_error(None, "Час закінчення має бути пізніше часу початку!")
                else:
                    is_overlap = Booking.objects.filter(
                        car=car,
                        start_date__lt=end,
                        end_date__gt=start
                    ).exists()

                    if is_overlap:
                        form.add_error(None, "Вибачте, на цей час машина вже заброньована!")
                    else:
                        booking = form.save(commit=False)
                        booking.car = car
                        booking.user = request.user
                        booking.save()

                        subject = f"🚗 Підтвердження бронювання: {car.brand} {car.model}"
                        message = f"Вітаємо, {request.user.username}!\n\n" \
                                  f"Ви успішно забронювали автомобіль у нашому сервісі CarRental.\n\n" \
                                  f"Деталі замовлення:\n" \
                                  f"- Автомобіль: {car.brand} {car.model}\n" \
                                  f"- Час оренди: з {booking.start_date.strftime('%d.%m.%Y %H:%M')} по {booking.end_date.strftime('%d.%m.%Y %H:%M')}\n" \
                                  f"- До сплати: {booking.total_price} грн\n\n" \
                                  f"Дякуємо, що обрали нас!"

                        user_email = request.user.email if request.user.email else f"{request.user.username}@testmail.com"

                        send_mail(
                            subject,
                            message,
                            'noreply@carrental.com',
                            [user_email],
                            fail_silently=True,
                        )

                        return redirect('car_list')

    return render(request, 'cars/car_detail.html', {
        'car': car, 
        'form': form,
        'review_form': review_form,
        'reviews': reviews,
        'can_review': can_review
    })

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
    writer.writerow(['Автомобіль', 'Час початку', 'Час завершення', 'Вартість (грн)', 'Статус'])
    bookings = Booking.objects.filter(user=request.user).order_by('-created_at')
    for b in bookings:
        writer.writerow([f"{b.car.brand} {b.car.model}", b.start_date.strftime("%d.%m.%Y %H:%M"), b.end_date.strftime("%d.%m.%Y %H:%M"), b.total_price, b.status_label])
    return response

def car_suggestions(request):
    query = request.GET.get('q', '')
    if query:
        cars = Car.objects.filter(Q(brand__icontains=query) | Q(model__icontains=query))[:5]
        results = list(set([f"{car.brand} {car.model}" for car in cars]))
    else:
        results = []
    return JsonResponse({'suggestions': results})

# --- ОНОВЛЕНИЙ ДАШБОРД (З ГРАФІКОМ І ДЕТАЛІЗАЦІЄЮ) ---
@user_passes_test(lambda u: u.is_staff)
def dashboard(request):
    total_cars = Car.objects.count()
    all_bookings = Booking.objects.all().order_by('-created_at')
    total_bookings = all_bookings.count()
    active_bookings = Booking.objects.filter(end_date__gte=timezone.now()).count()
    
    total_revenue = sum(b.total_price for b in all_bookings)
    popular_cars = Car.objects.annotate(num_bookings=Count('booking')).order_by('-num_bookings')[:5]

    # --- Збираємо дані для графіка (Прибуток по днях) ---
    revenue_by_date = {}
    for b in all_bookings:
        # Беремо тільки дату створення угоди
        date_str = b.created_at.strftime('%Y-%m-%d')
        if date_str not in revenue_by_date:
            revenue_by_date[date_str] = 0
        revenue_by_date[date_str] += b.total_price

    # Сортуємо дати по зростанню і беремо останні 14 днів, коли були угоди
    sorted_dates = sorted(revenue_by_date.keys())[-14:]
    chart_data = [revenue_by_date[date] for date in sorted_dates]

    context = {
        'total_cars': total_cars,
        'total_bookings': total_bookings,
        'active_bookings': active_bookings,
        'total_revenue': total_revenue,
        'popular_cars': popular_cars,
        'recent_bookings': all_bookings[:15], # Останні 15 угод для детальної таблиці
        'chart_labels': json.dumps(sorted_dates), # Передаємо дати в JS
        'chart_data': json.dumps(chart_data),     # Передаємо суми в JS
    }
    return render(request, 'cars/dashboard.html', context)