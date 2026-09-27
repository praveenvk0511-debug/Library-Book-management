from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("books/", views.book_list, name="book_list"),
    path("books/<int:pk>/", views.book_detail, name="book_detail"),
    path("books/add/", views.book_create, name="book_create"),
    path("books/<int:pk>/edit/", views.book_update, name="book_update"),
    path("books/<int:pk>/delete/", views.book_delete, name="book_delete"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("members/", views.member_list, name="member_list"),
    path("members/add/", views.member_create, name="member_create"),
    path("members/<int:pk>/edit/", views.member_update, name="member_update"),
    path("members/<int:pk>/delete/", views.member_delete, name="member_delete"),
    path("authors/add/", views.author_create, name="author_create"),
    path("categories/add/", views.category_create, name="category_create"),
    path("loans/", views.loan_list, name="loan_list"),
    path("loans/issue/", views.issue_book, name="issue_book"),
    path("loans/<int:pk>/return/", views.return_book, name="return_book"),
    path("fines/", views.fine_list, name="fine_list"),
    path("fines/<int:pk>/paid/", views.mark_fine_paid, name="mark_fine_paid"),
    path("my/loans/", views.my_loans, name="my_loans"),
    path("my/fines/", views.my_fines, name="my_fines"),
    path("accounts/register/", views.register, name="register"),
    path("accounts/login/", views.LibraryLoginView.as_view(), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
]