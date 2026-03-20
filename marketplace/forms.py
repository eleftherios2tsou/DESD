from django.contrib.auth.forms import UserCreationForm
from django import forms
from .models import CustomUser, Product, ProducerProfile
from datetime import date, timedelta
from .models import Review


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'password1', 'password2']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'customer'
        if commit:
            user.save()
        return user


class ProducerRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    business_name = forms.CharField(max_length=200, help_text='Your farm or business name')
    address = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), help_text='Full business address')
    postcode = forms.CharField(max_length=10)
    description = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False,
        help_text='Brief description of your produce (optional)',
    )

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'password1', 'password2']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'name', 'category', 'description', 'price', 'stock',
            'allergens', 'is_organic', 'harvest_date', 'best_before',
            'farm_origin', 'is_seasonal', 'seasonal_months',
            'lead_time_hours', 'is_active', 'image',
        ]
        widgets = {
            'harvest_date': forms.DateInput(attrs={'type': 'date'}),
            'best_before': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 4}),
            'allergens': forms.Textarea(attrs={'rows': 2}),
        }
class AccountSettingsForm(forms.ModelForm):
    new_password1 = forms.CharField(
        label='New password',
        widget=forms.PasswordInput,
        required=False,
        help_text='Leave blank to keep your current password.',
    )
    new_password2 = forms.CharField(
        label='Confirm new password',
        widget=forms.PasswordInput,
        required=False,
    )

    class Meta:
        model = CustomUser
        fields = ['email']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('new_password1')
        p2 = cleaned_data.get('new_password2')
        if p1 or p2:
            if p1 != p2:
                raise forms.ValidationError('The two password fields did not match.')
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('new_password1')
        if password:
            user.set_password(password)
        if commit:
            user.save()
        return user


class ProducerProfileForm(forms.ModelForm):
    class Meta:
        model = ProducerProfile
        fields = ['business_name', 'address', 'postcode', 'description']
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }


class CheckoutForm(forms.Form):
    full_name = forms.CharField(max_length=200)
    email = forms.EmailField()
    postcode = forms.CharField(max_length=10)
    delivery_address = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}))
    delivery_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))

    def clean_delivery_date(self):
        delivery_date = self.cleaned_data.get('delivery_date')
        min_date = date.today() + timedelta(hours=48)
        if delivery_date < min_date:
            raise forms.ValidationError('Delivery date must be at least 48 hours from now.')
        return delivery_date

class ReviewForm(forms.ModelForm):
    rating = forms.ChoiceField(
        choices=[(i, f'{i} ★') for i in range(1, 6)],
        widget=forms.RadioSelect,
    )

    class Meta:
        model = Review
        fields = ['rating', 'comment']
        widgets = {
            'comment': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Share your experience...'})
        }
    