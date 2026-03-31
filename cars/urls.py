from django.urls import path
from . import views

urlpatterns = [
    path('', views.car_list, name='car_list'),
    path('<int:pk>/', views.car_detail, name='car_detail'),
    path('my-bookings/', views.my_bookings, name='my_bookings'),
    path('signup/', views.signup, name='signup'),
    path('booking/<int:pk>/cancel/', views.cancel_booking, name='cancel_booking'),
    path('my-bookings/export/', views.export_bookings_csv, name='export_bookings_csv'),
    path('api/suggestions/', views.car_suggestions, name='car_suggestions'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('booking/<int:pk>/invoice/', views.download_invoice, name='download_invoice'), # <-- НОВИЙ МАРШРУТ ДЛЯ PDF
]