from typing import Any

from django.contrib.auth.forms import UserCreationForm
from django import forms
from .models import CustomUser, Product, ProducerProfile
from datetime import date, timedelta
from .models import Review


# basic registration form for customers
# extends UserCreationForm which already handles username and password fields
class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'password1', 'password2']

    def clean_email(self):
        # make sure no two accounts share the same email
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'customer'  # always set to customer for this form
        if commit:
            user.save()
        return user


# producer registration needs extra fields for their business info
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

# form for community group registration (S3-010)
class CommunityGroupRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    organisation_name = forms.CharField(max_length=200, help_text='Your community group or organisation name')
    address = forms.CharField(widget=forms.Textarea(attrs={'rows':3}))
    postcode = forms.CharField(max_length=10)

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'password1', 'password2']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        # exclude current user when checking - needed for the edit case
        if CustomUser.objects.filter(email=email).exclude(pk = self.instance.pk).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def save(self, commit = True) -> Any:
        user = super().save(commit=False)
        user.role = 'community_group'
        if commit:
            user.save()
        return user

# form for restaurant registration (S3-010)
class RestaurantRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    restaurant_name = forms.CharField(max_length=200, help_text='Your restaurant name')
    address = forms.CharField(widget=forms.Textarea(attrs={'rows':3}))
    postcode = forms.CharField(max_length=10)

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'password1', 'password2']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exclude(pk = self.instance.pk).exists():
            raise forms.ValidationError('An account with this email already exists.')

    def save(self, commit = True):
        user = super().save(commit=False)
        user.role = 'restaurant'
        if commit:
            user.save()
        return user

# the main form producers use to create and edit products
class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'name', 'category', 'description', 'price', 'stock',
            'allergens', 'is_organic', 'harvest_date', 'best_before',
            'farm_origin', 'is_seasonal', 'seasonal_months',
            'season_status', 'season_start', 'season_end',
            'lead_time_hours', 'low_stock_threshold', 'is_active', 'is_discounted', 'sale_price', 'image',
        ]
        # using DateInput with type=date gives us the browser date picker
        widgets = {
            'harvest_date': forms.DateInput(attrs={'type': 'date'}),
            'best_before': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 4}),
            'allergens': forms.Textarea(attrs={'rows': 2}),
            'season_start': forms.DateInput(attrs={'type': 'date'}),
            'season_end': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        is_discounted = cleaned_data.get('is_discounted')
        sale_price = cleaned_data.get('sale_price')
        price = cleaned_data.get('price')

        # if marked as discounted, the sale price must be set and must be lower than the original
        if is_discounted:
            if not sale_price:
                self.add_error('sale_price', 'Please specify the sale price for this discounted product.')
            elif sale_price and price and sale_price >= price:
                self.add_error('sale_price', 'Sale price must be lower than the original price.')

        return cleaned_data


# form for users to change their email and password from the account settings page
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
        # exclude self so producers can re-save with their existing email
        if CustomUser.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('new_password1')
        p2 = cleaned_data.get('new_password2')
        # only validate passwords if the user actually typed something in
        if p1 or p2:
            if p1 != p2:
                raise forms.ValidationError('The two password fields did not match.')
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('new_password1')
        if password:
            user.set_password(password)  # properly hashes the password
        if commit:
            user.save()
        return user


# separate form for producers to update their business profile info
class ProducerProfileForm(forms.ModelForm):
    class Meta:
        model = ProducerProfile
        fields = ['business_name', 'address', 'postcode', 'description']
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }


# checkout form - collects delivery details before we create the stripe payment
class CheckoutForm(forms.Form):
    full_name = forms.CharField(max_length=200)
    email = forms.EmailField()
    postcode = forms.CharField(max_length=10)
    delivery_address = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}))
    delivery_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    special_delivery_instructions = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'e.g. Deliver to kitchen entrance, contact manager on arrival'}),
        required=False,
)

    def clean_delivery_date(self):
        delivery_date = self.cleaned_data.get('delivery_date')
        # enforce the 48 hour minimum lead time from the spec
        min_date = date.today() + timedelta(hours=48)
        if delivery_date < min_date:
            raise forms.ValidationError('Delivery date must be at least 48 hours from now.')
        return delivery_date

# simple review form - customers rate 1-5 stars and leave a comment
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
