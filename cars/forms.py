from django import forms
from .models import Booking, Review

class BookingForm(forms.ModelForm):
    use_balance = forms.BooleanField(
        required=False, 
        label="Списати кешбек",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    # ПОЛЕ ДЛЯ ПРОМОКОДУ
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