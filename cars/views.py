import os
import io
import csv
import json
import qrcode
from PIL import Image

from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q, Count
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.utils import timezone
from django.utils.timezone import localtime
from django.core.mail import send_mail
from django.http import HttpResponse, JsonResponse, FileResponse
from django.db import transaction # 🚨 ІМПОРТ ТРАНЗАКЦІЙ БАЗИ ДАНИХ

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics

from .models import Car, Booking, Category, Review
from .forms import BookingForm, ReviewForm

def car_list(request):
    cars = Car.objects.filter(is_available=True)
    categories = Category.objects.all()
    query = request.GET.get('q')
    max_price = request.GET.get('max_price')
    category_id = request.GET.get('category')
    
    if query: cars = cars.filter(Q(brand__icontains=query) | Q(model__icontains=query))
    if max_price:
        try: cars = cars.filter(price_per_day__lte=float(max_price))
        except ValueError: pass
    if category_id: cars = cars.filter(category_id=category_id)
            
    return render(request, 'cars/car_list.html', {'cars': cars, 'categories': categories, 'query': query, 'max_price': max_price, 'selected_category': category_id})

def car_detail(request, pk):
    car = get_object_or_404(Car, pk=pk)
    reviews = car.reviews.all().order_by('-created_at')

    can_review = False
    if request.user.is_authenticated:
        can_review = Booking.objects.filter(user=request.user, car=car, end_date__lt=timezone.now()).exists()

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
                    if Booking.objects.filter(car=car, start_date__lt=end, end_date__gt=start).exists():
                        form.add_error(None, "Вибачте, на цей час машина вже заброньована!")
                    else:
                        # 🚨 ТРАНЗАКЦІЯ: ГАРАНТУЄМО БЕЗПЕКУ СПИСАННЯ ГРОШЕЙ
                        with transaction.atomic():
                            booking = form.save(commit=False)
                            booking.car = car
                            booking.user = request.user
                            
                            # Отримуємо попередню вартість для розрахунку
                            booking.start_date = start
                            booking.end_date = end
                            total_cost = booking.financial_details['total']
                            
                            use_balance = form.cleaned_data.get('use_balance')
                            profile = request.user.profile
                            
                            # Логіка списання балів
                            deducted_amount = 0
                            if use_balance and profile.loyalty_balance > 0:
                                if profile.loyalty_balance >= total_cost:
                                    deducted_amount = total_cost
                                    profile.loyalty_balance -= total_cost
                                else:
                                    deducted_amount = profile.loyalty_balance
                                    profile.loyalty_balance = 0
                                profile.save() 
                            
                            booking.paid_with_balance = deducted_amount
                            booking.save() 

                        # Email logic
                        local_start = localtime(booking.start_date)
                        local_end = localtime(booking.end_date)
                        message = f"Вітаємо, {request.user.username}!\n\nДеталі замовлення:\n- Автомобіль: {car.brand} {car.model}\n- Час оренди: з {local_start.strftime('%d.%m.%Y %H:%M')} по {local_end.strftime('%d.%m.%Y %H:%M')}\n- Оплачено балами: {booking.paid_with_balance} грн\n- До сплати готівкою: {booking.amount_due} грн\n\nВам також нараховано 5% кешбеку! Дякуємо, що обрали нас!"
                        user_email = request.user.email if request.user.email else f"{request.user.username}@testmail.com"
                        send_mail(f"🚗 Підтвердження бронювання: {car.brand} {car.model}", message, 'noreply@carrental.com', [user_email], fail_silently=True)

                        return redirect('car_list')

    # Отримуємо баланс для відображення в HTML
    user_balance = request.user.profile.loyalty_balance if request.user.is_authenticated else 0

    return render(request, 'cars/car_detail.html', {
        'car': car, 'form': form, 'review_form': review_form, 'reviews': reviews, 'can_review': can_review, 'user_balance': user_balance
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
        # Якщо бронювання скасоване, треба повернути бали на баланс
        with transaction.atomic():
            if booking.paid_with_balance > 0:
                profile = request.user.profile
                profile.loyalty_balance += booking.paid_with_balance
                profile.save()
            booking.delete()
        return redirect('my_bookings')
    return redirect('my_bookings')

@login_required
def export_bookings_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="financial_report.csv"'
    response.write('\ufeff'.encode('utf8'))
    writer = csv.writer(response, delimiter=';')
    writer.writerow(['Автомобіль', 'Час початку', 'Час завершення', 'До сплати', 'Сплачено балами', 'Статус'])
    bookings = Booking.objects.filter(user=request.user).order_by('-created_at')
    for b in bookings:
        writer.writerow([f"{b.car.brand} {b.car.model}", localtime(b.start_date).strftime("%d.%m.%Y %H:%M"), localtime(b.end_date).strftime("%d.%m.%Y %H:%M"), b.amount_due, b.paid_with_balance, b.status_label])
    return response

def car_suggestions(request):
    query = request.GET.get('q', '')
    if query:
        cars = Car.objects.filter(Q(brand__icontains=query) | Q(model__icontains=query))[:5]
        results = list(set([f"{car.brand} {car.model}" for car in cars]))
    else:
        results = []
    return JsonResponse({'suggestions': results})

@user_passes_test(lambda u: u.is_staff)
def dashboard(request):
    total_cars = Car.objects.count()
    all_bookings = Booking.objects.all().order_by('-created_at')
    total_bookings = all_bookings.count()
    active_bookings = Booking.objects.filter(end_date__gte=timezone.now()).count()
    
    total_revenue = sum(b.amount_due for b in all_bookings) 
    popular_cars = Car.objects.annotate(num_bookings=Count('booking')).order_by('-num_bookings')[:5]

    revenue_by_date = {}
    for b in all_bookings:
        date_str = localtime(b.created_at).strftime('%Y-%m-%d')
        if date_str not in revenue_by_date:
            revenue_by_date[date_str] = 0
        revenue_by_date[date_str] += b.amount_due

    sorted_dates = sorted(revenue_by_date.keys())[-14:]
    chart_data = [revenue_by_date[date] for date in sorted_dates]

    context = {
        'total_cars': total_cars, 'total_bookings': total_bookings, 'active_bookings': active_bookings,
        'total_revenue': total_revenue, 'popular_cars': popular_cars, 'recent_bookings': all_bookings[:15],
        'chart_labels': json.dumps(sorted_dates), 'chart_data': json.dumps(chart_data),
    }
    return render(request, 'cars/dashboard.html', context)

@login_required
def download_invoice(request, pk):
    booking = get_object_or_404(Booking, pk=pk, user=request.user)
    fin_details = booking.financial_details 

    font_path = os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Fonts', 'arial.ttf')
    try:
        pdfmetrics.registerFont(TTFont('Arial', font_path))
        pdfmetrics.registerFont(TTFont('Arial-Bold', font_path.replace('arial.ttf', 'arialbd.ttf')))
        font_regular = 'Arial'
        font_bold = 'Arial-Bold'
    except Exception:
        font_regular = 'Helvetica'
        font_bold = 'Helvetica-Bold'

    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)

    local_start = localtime(booking.start_date)
    local_end = localtime(booking.end_date)
    local_issue = localtime(timezone.now())

    p.setFont(font_bold, 24)
    p.drawString(50, 800, "ТОВ «CarRental Україна»")
    p.setFont(font_regular, 14)
    p.drawString(50, 780, "ОФІЦІЙНИЙ ЕЛЕКТРОННИЙ ЧЕК")
    p.setLineWidth(2)
    p.line(50, 765, 550, 765)

    invoice_num = f"INV-{local_issue.year}-{booking.pk:04d}"
    p.setFont(font_bold, 12)
    p.drawString(50, 730, f"Квитанція №: {invoice_num}")
    p.setFont(font_regular, 12)
    p.drawString(50, 710, f"Дата створення: {local_issue.strftime('%d.%m.%Y %H:%M')}")
    p.drawString(350, 730, f"Клієнт: {request.user.username}")
    p.drawString(350, 710, f"Email: {request.user.email if request.user.email else 'Не вказано'}")
    p.setLineWidth(1)
    p.line(50, 690, 550, 690)

    p.setFont(font_bold, 14)
    p.drawString(50, 660, "Деталі оренди:")
    p.setFont(font_regular, 12)
    p.drawString(50, 630, f"Автомобіль: {booking.car.brand} {booking.car.model} ({booking.car.year} р.)")
    p.drawString(50, 610, f"Отримання: {local_start.strftime('%d.%m.%Y %H:%M')}")
    p.drawString(50, 590, f"Повернення: {local_end.strftime('%d.%m.%Y %H:%M')}")

    p.setLineWidth(1)
    p.line(50, 550, 550, 550)
    p.setFont(font_bold, 14)
    p.drawString(50, 520, "Деталізація вартості (ГРН):")
    p.setFont(font_regular, 12)
    
    y_pos = 490
    p.drawString(70, y_pos, f"Базовий тариф:")
    p.drawString(450, y_pos, f"+ {fin_details['base']} ₴"); y_pos -= 20
    
    if fin_details['surcharge'] > 0:
        p.setFillColor(colors.red)
        p.drawString(70, y_pos, f"Націнка за вихідні дні (20%):")
        p.drawString(450, y_pos, f"+ {fin_details['surcharge']} ₴")
        p.setFillColor(colors.black) 
    else:
        p.drawString(70, y_pos, f"Націнка за вихідні дні:")
        p.drawString(450, y_pos, f"0 ₴")
    y_pos -= 20

    if booking.paid_with_balance > 0:
        p.setFillColor(colors.magenta) 
        p.drawString(70, y_pos, f"Оплачено з Кешбек-гаманця:")
        p.drawString(450, y_pos, f"- {booking.paid_with_balance} ₴")
        p.setFillColor(colors.black)
    
    p.setLineWidth(2)
    p.line(50, y_pos - 20, 550, y_pos - 20)
    
    p.setFont(font_bold, 18)
    p.setFillColor(colors.green) 
    p.drawString(50, y_pos - 50, f"РАЗОМ ДО СПЛАТИ: {booking.amount_due} ₴") 
    p.setFillColor(colors.black)

    qr_text = f"ЧЕК {invoice_num}\nАвто: {booking.car.brand} {booking.car.model}\nОплачено: {booking.amount_due} UAH\nСтатус: ДІЙСНО"
    qr = qrcode.QRCode(version=1, box_size=10, border=1)
    qr.add_data(qr_text)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    qr_buffer = io.BytesIO()
    qr_img.save(qr_buffer, format='PNG')
    qr_buffer.seek(0)
    p.drawImage(ImageReader(qr_buffer), 430, 150, width=100, height=100)
    p.setFont(font_regular, 8)
    p.drawString(440, 140, "Скануйте для перевірки")

    p.saveState() 
    p.translate(130, 200) 
    p.rotate(18) 
    p.setFillColor(colors.blue)
    p.setStrokeColor(colors.blue)
    p.setLineWidth(2)
    p.circle(0, 0, 60) 
    p.circle(0, 0, 55) 
    p.setFont(font_bold, 14)
    p.drawCentredString(0, 5, "ОПЛАЧЕНО") 
    p.setFont(font_regular, 8)
    p.drawCentredString(0, -15, "ТОВ «CarRental»")
    p.drawCentredString(0, -25, "ЄДРПОУ 12345678")
    p.restoreState() 

    p.setFont(font_regular, 10)
    p.drawString(50, 100, "Дякуємо, що обрали CarRental!")
    p.drawString(50, 85, "Цей документ згенеровано автоматично системою. Мокра печатка не вимагається.")

    p.showPage()
    p.save()

    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename=f'CarRental_Чек_{invoice_num}.pdf')