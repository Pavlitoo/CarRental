from django.shortcuts import render, get_object_or_404, redirect
from .models import Car, Booking, Category, Review
from .forms import BookingForm, ReviewForm
from django.db.models import Q, Count # <-- Додали Count для аналітики
from django.contrib.auth.decorators import login_required, user_passes_test # <-- Додали захист для адмінів
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.utils import timezone
import csv
from django.http import HttpResponse, JsonResponse
from django.core.mail import send_mail

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
            end_date__lt=timezone.now().date()
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

                        subject = f"🚗 Підтвердження бронювання: {car.brand} {car.model}"
                        message = f"Вітаємо, {request.user.username}!\n\n" \
                                  f"Ви успішно забронювали автомобіль у нашому сервісі CarRental.\n\n" \
                                  f"Деталі замовлення:\n" \
                                  f"- Автомобіль: {car.brand} {car.model}\n" \
                                  f"- Дати: з {booking.start_date.strftime('%d.%m.%Y')} по {booking.end_date.strftime('%d.%m.%Y')}\n" \
                                  f"- До сплати: {booking.total_price} грн\n\n" \
                                  f"Дякуємо, що обрали нас!"

                        user_email = request.user.email if request.user.email else f"{request.user.username}@testmail.com"

                        send_mail(
                            subject,
                            message,
                            'noreply@carrental.com',
                            [user_email],
                            fail_silently=False,
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
    writer.writerow(['Автомобіль', 'Дата початку', 'Дата завершення', 'Кількість днів', 'Ціна за добу (грн)', 'Загальна сума (грн)', 'Статус'])
    bookings = Booking.objects.filter(user=request.user).order_by('-created_at')
    for b in bookings:
        duration = (b.end_date - b.start_date).days
        if duration <= 0: duration = 1
        writer.writerow([f"{b.car.brand} {b.car.model}", b.start_date.strftime("%d.%m.%Y"), b.end_date.strftime("%d.%m.%Y"), duration, b.car.price_per_day, b.total_price, b.status_label])
    return response

def car_suggestions(request):
    query = request.GET.get('q', '')
    if query:
        cars = Car.objects.filter(Q(brand__icontains=query) | Q(model__icontains=query))[:5]
        results = list(set([f"{car.brand} {car.model}" for car in cars]))
    else:
        results = []
    return JsonResponse({'suggestions': results})

# --- НОВА ЛОГІКА ДЛЯ ДАШБОРДА ---
# Дозволяємо доступ тільки адміністраторам (is_staff)
@user_passes_test(lambda u: u.is_staff)
def dashboard(request):
    # 1. Загальна кількість авто та бронювань (запити до БД)
    total_cars = Car.objects.count()
    total_bookings = Booking.objects.count()
    
    # 2. Кількість активних бронювань (на сьогодні і майбутнє)
    active_bookings = Booking.objects.filter(end_date__gte=timezone.now().date()).count()
    
    # 3. Підрахунок загального прибутку 
    # (Використовуємо генератор Python, оскільки total_price — це @property, а не поле БД)
    all_bookings = Booking.objects.all()
    total_revenue = sum(b.total_price for b in all_bookings)
    
    # 4. Топ-5 найпопулярніших авто (Складний запит з анотацією бази даних)
    popular_cars = Car.objects.annotate(num_bookings=Count('booking')).order_by('-num_bookings')[:5]

    context = {
        'total_cars': total_cars,
        'total_bookings': total_bookings,
        'active_bookings': active_bookings,
        'total_revenue': total_revenue,
        'popular_cars': popular_cars,
    }
    return render(request, 'cars/dashboard.html', context)