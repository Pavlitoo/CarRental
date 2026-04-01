from django.urls import path
from . import views

urlpatterns = [
    path('', views.car_list, name='car_list'),
    path('<int:pk>/', views.car_detail, name='car_detail'),
    path('signup/', views.signup, name='signup'),
    
    # 🚨 НОВА СТОРІНКА ДЛЯ ВВЕДЕННЯ КОДУ З ПОШТИ 🚨
    path('verify-email/', views.verify_email_view, name='verify_email'),
    
    path('my-bookings/', views.my_bookings, name='my_bookings'),
    path('cancel-booking/<int:pk>/', views.cancel_booking, name='cancel_booking'),
    path('export-bookings/', views.export_bookings_csv, name='export_bookings_csv'),
    path('suggestions/', views.car_suggestions, name='car_suggestions'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('download-invoice/<int:pk>/', views.download_invoice, name='download_invoice'),
    
    # Інформаційні сторінки
    path('terms/', views.terms_view, name='terms'),
    path('loyalty/', views.loyalty_view, name='loyalty'),
    path('privacy/', views.privacy_view, name='privacy'),
    
    path('verify/', views.verify_view, name='verify'),
]