from django import forms
from .models import Booking, Review

class BookingForm(forms.ModelForm):
    # Додаємо віртуальну галочку, якої немає в БД, але вона є на сайті
    use_balance = forms.BooleanField(
        required=False, 
        label="Використати баланс гаманця для знижки",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
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
            'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Напишіть ваші враження від авто...'}),
        }