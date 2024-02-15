from django import forms
from django.contrib.auth.models import User

from blog.models import Post, Comment


class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email')


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        exclude = ('author',)
        widgets = {'pub_date': forms.DateInput(
            format='%Y-%m-%d %H:%M:%S',
            attrs={'type': 'datetime-local'})
        }


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ('text',)
