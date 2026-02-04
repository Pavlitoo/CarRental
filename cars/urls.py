from django.urls import path
from . import views

urlpatterns = [
    path('', views.car_list, name='car_list'),
    path('<int:pk>/', views.car_detail, name='car_detail'), # <int:pk> - це ID машини (1, 2, 3...)
    path('my_bookings/', views.my_bookings, name='my_bookings'),
    path('signup/', views.signup, name='signup'),
    path('booking/<int:pk>/cancel/', views.cancel_booking, name='cancel_booking'),
]