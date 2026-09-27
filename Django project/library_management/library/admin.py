from django.contrib import admin
from django.utils import timezone

from .models import Author, Book, Category, Fine, Loan, Member


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
	list_display = ("name",)
	search_fields = ("name",)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
	list_display = ("name",)
	search_fields = ("name",)


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
	list_display = ("title", "author", "category", "isbn", "total_copies", "available_copies")
	list_filter = ("category", "author")
	search_fields = ("title", "isbn", "author__name", "category__name")
	list_select_related = ("author", "category")


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
	list_display = ("member_id", "name", "email", "department", "year", "registered_at")
	list_filter = ("department", "year", "registered_at")
	search_fields = ("member_id", "name", "email", "phone")


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
	list_display = ("book", "member", "issue_date", "due_date", "return_date", "status")
	list_filter = ("status", "issue_date", "due_date")
	search_fields = ("book__title", "member__name", "member__member_id")
	list_select_related = ("book", "member", "issued_by")
	date_hierarchy = "issue_date"


@admin.action(description="Mark selected fines as paid")
def mark_paid(modeladmin, request, queryset):
	queryset.filter(is_paid=False).update(is_paid=True, paid_at=timezone.now())


@admin.register(Fine)
class FineAdmin(admin.ModelAdmin):
	list_display = ("loan", "amount", "is_paid", "paid_at", "updated_at")
	list_filter = ("is_paid", "updated_at")
	search_fields = ("loan__book__title", "loan__member__name", "loan__member__member_id")
	list_select_related = ("loan__book", "loan__member")
	actions = (mark_paid,)
