from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser
from django import forms
LIMITED_CHOICES = (
    ('producer', 'Producer'),
    ('customer', 'Customer'),
)
class RegistrationForm(UserCreationForm):
    
    role = forms.ChoiceField(choices=LIMITED_CHOICES)
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'role' , 'password1', 'password2']
        

