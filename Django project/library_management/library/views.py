from decimal import Decimal
from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import F, Q, Sum
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .forms import AuthorForm, BookForm, CategoryForm, IssueForm, MemberForm, RegistrationForm
from .models import Author, Book, Category, Fine, Loan, Member


def librarian_required(view):
    @login_required
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return wrapped


def daily_fine_amount():
    return Decimal(str(settings.DAILY_FINE_AMOUNT))


def outstanding_for(loan):
    if loan.status == Loan.Status.RETURNED:
        try:
            fine = loan.fine
        except Fine.DoesNotExist:
            return Decimal("0.00")
        return fine.amount if not fine.is_paid else Decimal("0.00")
    return daily_fine_amount() * loan.overdue_days


def book_list(request):
    books = Book.objects.select_related("author", "category")
    query = request.GET.get("q", "").strip()
    category_id = request.GET.get("category", "")
    availability = request.GET.get("availability", "")
    if query:
        books = books.filter(
            Q(title__icontains=query)
            | Q(author__name__icontains=query)
            | Q(isbn__icontains=query)
            | Q(category__name__icontains=query)
        )
    if category_id:
        books = books.filter(category_id=category_id)
    if availability == "available":
        books = books.filter(available_copies__gt=0)
    elif availability == "unavailable":
        books = books.filter(available_copies=0)
    return render(request, "library/book_list.html", {
        "books": books,
        "categories": Category.objects.all(),
        "query": query,
        "selected_category": category_id,
        "availability": availability,
    })


def book_detail(request, pk):
    book = get_object_or_404(Book.objects.select_related("author", "category"), pk=pk)
    return render(request, "library/book_detail.html", {"book": book})


@librarian_required
def dashboard(request):
    active_loans = Loan.objects.filter(status=Loan.Status.ISSUED).select_related("book", "member")
    overdue_loans = active_loans.filter(due_date__lt=timezone.localdate())
    accrued_fines = sum((outstanding_for(loan) for loan in overdue_loans), Decimal("0.00"))
    recorded_fines = Fine.objects.filter(is_paid=False).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    categories = list(Category.objects.annotate(book_count=Sum("books__total_copies")).values("name", "book_count"))
    context = {
        "title": "Library overview",
        "total_books": Book.objects.aggregate(total=Sum("total_copies"))["total"] or 0,
        "available_books": Book.objects.aggregate(total=Sum("available_copies"))["total"] or 0,
        "issued_books": sum(book.total_copies - book.available_copies for book in Book.objects.all()),
        "total_members": Member.objects.count(),
        "overdue_count": overdue_loans.count(),
        "total_fines": recorded_fines + accrued_fines,
        "recent_loans": Loan.objects.select_related("book", "member").order_by("-issue_date")[:6],
        "recent_books": Book.objects.select_related("author").order_by("-added_at")[:5],
        "category_labels": [item["name"] for item in categories],
        "category_values": [item["book_count"] or 0 for item in categories],
    }
    return render(request, "library/dashboard.html", context)


@librarian_required
def book_create(request):
    form = BookForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        form.save()
        messages.success(request, "Book added to the catalogue.")
        return redirect("book_list")
    return render(request, "library/form.html", {"form": form, "title": "Add a book"})


@librarian_required
def book_update(request, pk):
    book = get_object_or_404(Book, pk=pk)
    form = BookForm(request.POST or None, request.FILES or None, instance=book)
    if form.is_valid():
        form.save()
        messages.success(request, "Book details updated.")
        return redirect("book_detail", pk=book.pk)
    return render(request, "library/form.html", {"form": form, "title": "Edit book"})


@librarian_required
def book_delete(request, pk):
    book = get_object_or_404(Book, pk=pk)
    if request.method == "POST":
        try:
            book.delete()
            messages.success(request, "Book removed from the catalogue.")
        except ProtectedError:
            messages.error(request, "This book has borrowing history and cannot be removed.")
        return redirect("book_list")
    return render(request, "library/confirm_delete.html", {"object": book, "title": "Delete book"})


@librarian_required
def member_list(request):
    members = Member.objects.select_related("user")
    query = request.GET.get("q", "").strip()
    if query:
        members = members.filter(
            Q(name__icontains=query) | Q(email__icontains=query) | Q(member_id__icontains=query)
        )
    return render(request, "library/member_list.html", {"members": members, "query": query})


@librarian_required
def member_create(request):
    form = MemberForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, "Member added.")
        return redirect("member_list")
    return render(request, "library/form.html", {"form": form, "title": "Add a member"})


@librarian_required
def member_update(request, pk):
    member = get_object_or_404(Member, pk=pk)
    form = MemberForm(request.POST or None, instance=member)
    if form.is_valid():
        form.save()
        messages.success(request, "Member details updated.")
        return redirect("member_list")
    return render(request, "library/form.html", {"form": form, "title": "Edit member"})


@librarian_required
def member_delete(request, pk):
    member = get_object_or_404(Member, pk=pk)
    if request.method == "POST":
        try:
            member.delete()
            messages.success(request, "Member removed.")
        except ProtectedError:
            messages.error(request, "This member has borrowing history and cannot be removed.")
        return redirect("member_list")
    return render(request, "library/confirm_delete.html", {"object": member, "title": "Remove member"})


@librarian_required
def author_create(request):
    form = AuthorForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, "Author added.")
        return redirect("book_list")
    return render(request, "library/form.html", {"form": form, "title": "Add an author"})


@librarian_required
def category_create(request):
    form = CategoryForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, "Category added.")
        return redirect("book_list")
    return render(request, "library/form.html", {"form": form, "title": "Add a category"})


@librarian_required
def loan_list(request):
    loans = Loan.objects.select_related("book", "member", "fine")
    status = request.GET.get("status", "")
    query = request.GET.get("q", "").strip()
    if status == "overdue":
        loans = loans.filter(status=Loan.Status.ISSUED, due_date__lt=timezone.localdate())
    elif status in (Loan.Status.ISSUED, Loan.Status.RETURNED):
        loans = loans.filter(status=status)
    if query:
        loans = loans.filter(Q(book__title__icontains=query) | Q(member__name__icontains=query))
    return render(request, "library/loan_list.html", {"loans": loans, "status": status, "query": query})


@librarian_required
def issue_book(request):
    form = IssueForm(request.POST or None)
    if form.is_valid():
        try:
            with transaction.atomic():
                book = Book.objects.select_for_update().get(pk=form.cleaned_data["book"].pk)
                if book.available_copies < 1:
                    form.add_error("book", "No copies of this title are currently available.")
                else:
                    book.available_copies = F("available_copies") - 1
                    book.save(update_fields=["available_copies"])
                    Loan.objects.create(
                        book=book,
                        member=form.cleaned_data["member"],
                        issued_by=request.user,
                        due_date=form.cleaned_data["due_date"],
                    )
            if not form.errors:
                messages.success(request, "Book issued successfully.")
                return redirect("loan_list")
        except Book.DoesNotExist:
            form.add_error("book", "This book no longer exists.")
    return render(request, "library/form.html", {"form": form, "title": "Issue a book"})


@librarian_required
def return_book(request, pk):
    if request.method != "POST":
        return redirect("loan_list")
    with transaction.atomic():
        loan = get_object_or_404(Loan.objects.select_for_update().select_related("book"), pk=pk)
        if loan.status == Loan.Status.RETURNED:
            messages.error(request, "This book has already been returned.")
        else:
            loan.return_date = timezone.localdate()
            loan.status = Loan.Status.RETURNED
            loan.save(update_fields=["return_date", "status"])
            Book.objects.filter(pk=loan.book_id).update(available_copies=F("available_copies") + 1)
            amount = daily_fine_amount() * loan.overdue_days
            if amount:
                Fine.objects.update_or_create(loan=loan, defaults={"amount": amount, "is_paid": False, "paid_at": None})
            messages.success(request, "Return recorded. Fine assessed: ${:.2f}.".format(amount))
    return redirect("loan_list")


@librarian_required
def fine_list(request):
    fines = Fine.objects.select_related("loan__book", "loan__member")
    accruing_loans = Loan.objects.filter(
        status=Loan.Status.ISSUED,
        due_date__lt=timezone.localdate(),
    ).select_related("book", "member")
    status = request.GET.get("status", "")
    if status == "unpaid":
        fines = fines.filter(is_paid=False)
    elif status == "paid":
        fines = fines.filter(is_paid=True)
    if status == "paid":
        accruing_rows = []
    else:
        accruing_rows = [
            {"loan": loan, "amount": outstanding_for(loan)}
            for loan in accruing_loans
        ]
    return render(request, "library/fine_list.html", {
        "fines": fines,
        "accruing_rows": accruing_rows,
        "status": status,
    })


@librarian_required
def mark_fine_paid(request, pk):
    if request.method == "POST":
        fine = get_object_or_404(Fine, pk=pk)
        if not fine.is_paid:
            fine.is_paid = True
            fine.paid_at = timezone.now()
            fine.save(update_fields=["is_paid", "paid_at", "updated_at"])
            messages.success(request, "Fine marked as paid.")
    return redirect("fine_list")


@login_required
def my_loans(request):
    member = Member.objects.filter(user=request.user).first()
    loans = Loan.objects.filter(member=member).select_related("book", "fine") if member else Loan.objects.none()
    return render(request, "library/my_loans.html", {"loans": loans, "member": member})


@login_required
def my_fines(request):
    member = Member.objects.filter(user=request.user).first()
    loans = Loan.objects.filter(member=member).select_related("book", "fine") if member else Loan.objects.none()
    fine_rows = []
    fine_total = Decimal("0.00")
    for loan in loans:
        fine = Fine.objects.filter(loan=loan).first()
        amount = fine.amount if fine else (
            daily_fine_amount() * loan.overdue_days if loan.status == Loan.Status.ISSUED else Decimal("0.00")
        )
        if amount or fine:
            fine_rows.append({"loan": loan, "amount": amount, "is_paid": fine.is_paid if fine else False})
            if not fine or not fine.is_paid:
                fine_total += amount
    return render(request, "library/my_fines.html", {
        "fine_rows": fine_rows,
        "fine_total": fine_total,
    })


def register(request):
    if request.user.is_authenticated:
        return redirect("book_list")
    form = RegistrationForm(request.POST or None)
    if form.is_valid():
        with transaction.atomic():
            user = form.save(commit=False)
            user.email = form.cleaned_data["email"]
            user.save()
            Member.objects.create(
                user=user,
                name=f"{user.first_name} {user.last_name}".strip(),
                email=user.email,
                phone=form.cleaned_data["phone"],
                department=form.cleaned_data["department"],
                year=form.cleaned_data["year"],
            )
        login(request, user)
        messages.success(request, "Your member account is ready.")
        return redirect("book_list")
    return render(request, "library/form.html", {"form": form, "title": "Create a member account", "registration": True})


class LibraryLoginView(LoginView):
    template_name = "library/login.html"

    def get_default_redirect_url(self):
        destination = "dashboard" if self.request.user.is_staff else "book_list"
        return reverse(destination)


def home(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect("dashboard")
    return redirect("book_list")
