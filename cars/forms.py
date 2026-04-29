import datetime
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Booking, Review, UserProfile

class CustomSignupForm(UserCreationForm):
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
        fields = UserCreationForm.Meta.fields + ('email',)

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            profile = user.profile
            profile.birth_date = self.cleaned_data['birth_date']
            profile.driving_experience = self.cleaned_data['driving_experience']
            profile.save()
        return user

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

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        if start_date and end_date:
            # Даємо буфер 15 хвилин для поточного часу (захист від часових поясів)
            now_with_buffer = timezone.now() - datetime.timedelta(minutes=15)
            if start_date < now_with_buffer:
                self.add_error('start_date', "Неможливо забронювати авто в минулому часі!")
            
            if end_date <= start_date:
                self.add_error('end_date', "Час завершення має бути пізніше часу початку!")
            
            duration = end_date - start_date
            if duration.days > 30:
                self.add_error('end_date', "Максимальний термін оренди авто становить 30 днів!")
            
            if duration.total_seconds() < 3600:
                self.add_error('end_date', "Мінімальний час оренди становить 1 годину!")

        return cleaned_data

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.Select(attrs={'class': 'form-select'}),
            'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }