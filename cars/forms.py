from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Booking, Review, UserProfile

class CustomSignupForm(UserCreationForm):
    # 🚨 ДОДАЛИ ОБОВ'ЯЗКОВЕ ПОЛЕ EMAIL 🚨
    email = forms.EmailField(
        label="Електронна пошта", 
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'example@mail.com'}),
        required=True
    )
    birth_date = forms.DateField(
        label="Дата народження", 
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        required=True
    )
    driving_experience = forms.IntegerField(
        label="Стаж водіння (років)", 
        min_value=0, 
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Наприклад: 3'}),
        required=True
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('email',) # Додали email до полів

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email'] # Зберігаємо email
        if commit:
            user.save()
            profile = user.profile
            profile.birth_date = self.cleaned_data['birth_date']
            profile.driving_experience = self.cleaned_data['driving_experience']
            profile.save()
        return user

# 🚨 ФОРМА ДЛЯ ЗАВАНТАЖЕННЯ ПАСПОРТА 🚨
class VerifyForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['passport_photo']
        widgets = {
            'passport_photo': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'})
        }

class BookingForm(forms.ModelForm):
    use_balance = forms.BooleanField(
        required=False, 
        label="Списати кешбек",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    promo_code_entry = forms.CharField(
        required=False, 
        label="Промокод", 
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Введіть код...'})
    )

    class Meta:
        model = Booking
        fields = ['start_date', 'end_date']
        widgets = {
            'start_date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'end_date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
        }

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.Select(attrs={'class': 'form-select'}),
            'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }