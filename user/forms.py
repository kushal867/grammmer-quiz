from django import forms
from django.contrib.auth.models import User

# forms.ModelForm ==> model define

class LoginForm(forms.Form):
    username = forms.CharField(widget=forms.TextInput(attrs={"placeholder":"Username"}, ))
    password = forms.CharField(widget=forms.PasswordInput(attrs={"placeholder":"Password"}))


    def clean_username(self):
        username= self.cleaned_data['username']
        if len(username)<=3:
            raise forms.ValidationError("Username length should be greater than 4")
        return username

    def clean_password(self):
        password = self.cleaned_data['password']
        return password