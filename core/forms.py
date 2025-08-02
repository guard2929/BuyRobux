from django import forms


class LoginForm(forms.Form):
    roblox_nick = forms.CharField(
        max_length=150,
        label='Roblox Nickname',
        widget=forms.TextInput(attrs={'class': 'code-input', 'placeholder': 'Введите ник Roblox'})
    )
