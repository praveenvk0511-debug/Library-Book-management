from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.utils import timezone

from .models import Author, Book, Category, Member


class RegistrationForm(UserCreationForm):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    email = forms.EmailField()
    phone = forms.CharField(
        max_length=20,
        validators=[RegexValidator(r"^(?=(?:\D*\d){7,})[0-9+() -]{7,20}$", "Enter a valid phone number.")],
    )
    department = forms.CharField(max_length=100)
    year = forms.IntegerField(min_value=1, max_value=8)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "first_name", "last_name", "email", "phone", "department", "year")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        if Member.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("This email is already registered as a member.")
        return email


class BookForm(forms.ModelForm):
    class Meta:
        model = Book
        fields = (
            "title", "isbn", "author", "category", "publisher", "publication_year",
            "description", "cover", "total_copies", "available_copies",
        )
        widgets = {"description": forms.Textarea(attrs={"rows": 4})}

    def clean_isbn(self):
        return self.cleaned_data["isbn"].replace("-", "").replace(" ", "")


class MemberForm(forms.ModelForm):
    class Meta:
        model = Member
        fields = ("name", "email", "phone", "department", "year")


class AuthorForm(forms.ModelForm):
    class Meta:
        model = Author
        fields = ("name", "biography")
        widgets = {"biography": forms.Textarea(attrs={"rows": 4})}


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ("name", "description")
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}


class IssueForm(forms.Form):
    member = forms.ModelChoiceField(queryset=Member.objects.order_by("name"))
    book = forms.ModelChoiceField(queryset=Book.objects.filter(available_copies__gt=0).order_by("title"))
    due_date = forms.DateField(
        initial=lambda: timezone.localdate() + timezone.timedelta(days=14),
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    def clean_due_date(self):
        due_date = self.cleaned_data["due_date"]
        if due_date < timezone.localdate():
            raise forms.ValidationError("Due date cannot be in the past.")
        return due_date