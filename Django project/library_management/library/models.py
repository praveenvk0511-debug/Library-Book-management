import re
import uuid
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.utils import timezone


def default_due_date():
	return timezone.localdate() + timedelta(days=14)


class Author(models.Model):
	name = models.CharField(max_length=120)
	biography = models.TextField(blank=True)

	class Meta:
		ordering = ["name"]

	def __str__(self):
		return self.name


class Category(models.Model):
	name = models.CharField(max_length=80, unique=True)
	description = models.TextField(blank=True)

	class Meta:
		ordering = ["name"]
		verbose_name_plural = "categories"

	def __str__(self):
		return self.name


class Member(models.Model):
	user = models.OneToOneField(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="library_member",
		null=True,
		blank=True,
	)
	member_id = models.CharField(max_length=12, unique=True, editable=False)
	name = models.CharField(max_length=120)
	email = models.EmailField(unique=True)
	phone = models.CharField(
		max_length=20,
		validators=[RegexValidator(r"^(?=(?:\D*\d){7,})[0-9+() -]{7,20}$", "Enter a valid phone number.")],
	)
	department = models.CharField(max_length=100)
	year = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(8)])
	registered_at = models.DateField(default=timezone.localdate)

	class Meta:
		ordering = ["name"]

	def save(self, *args, **kwargs):
		if not self.member_id:
			self.member_id = f"M-{uuid.uuid4().hex[:8].upper()}"
		self.email = self.email.strip().lower()
		super().save(*args, **kwargs)

	def __str__(self):
		return f"{self.name} ({self.member_id})"


class Book(models.Model):
	title = models.CharField(max_length=200)
	isbn = models.CharField(max_length=17, unique=True)
	author = models.ForeignKey(Author, on_delete=models.PROTECT, related_name="books")
	category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="books")
	publisher = models.CharField(max_length=120, blank=True)
	publication_year = models.PositiveSmallIntegerField(
		null=True,
		blank=True,
		validators=[MinValueValidator(1000)],
	)
	description = models.TextField(blank=True)
	cover = models.ImageField(upload_to="book_covers/", blank=True)
	total_copies = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
	available_copies = models.PositiveIntegerField(default=1)
	added_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ["title"]
		constraints = [
			models.CheckConstraint(
				condition=models.Q(available_copies__lte=models.F("total_copies")),
				name="available_copies_not_above_total",
			),
		]

	def clean(self):
		self.isbn = self.isbn.replace("-", "").replace(" ", "")
		if self.isbn and not re.fullmatch(r"(?:\d{9}[\dX]|\d{13})", self.isbn.upper()):
			raise ValidationError({"isbn": "Enter a 10- or 13-digit ISBN."})
		if self.available_copies is not None and self.total_copies is not None:
			if self.available_copies > self.total_copies:
				raise ValidationError({"available_copies": "Available copies cannot exceed total copies."})

	@property
	def is_available(self):
		return self.available_copies > 0

	def __str__(self):
		return self.title


class Loan(models.Model):
	class Status(models.TextChoices):
		ISSUED = "issued", "Issued"
		RETURNED = "returned", "Returned"

	book = models.ForeignKey(Book, on_delete=models.PROTECT, related_name="loans")
	member = models.ForeignKey(Member, on_delete=models.PROTECT, related_name="loans")
	issued_by = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.SET_NULL,
		related_name="processed_loans",
		null=True,
		blank=True,
	)
	issue_date = models.DateField(default=timezone.localdate)
	due_date = models.DateField(default=default_due_date)
	return_date = models.DateField(null=True, blank=True)
	status = models.CharField(max_length=10, choices=Status.choices, default=Status.ISSUED)

	class Meta:
		ordering = ["-issue_date", "-pk"]
		constraints = [
			models.CheckConstraint(
				condition=models.Q(due_date__gte=models.F("issue_date")),
				name="loan_due_date_after_issue_date",
			),
		]

	def clean(self):
		if self.due_date and self.issue_date and self.due_date < self.issue_date:
			raise ValidationError({"due_date": "Due date cannot be before the issue date."})
		if self.return_date and self.issue_date and self.return_date < self.issue_date:
			raise ValidationError({"return_date": "Return date cannot be before the issue date."})
		if self.status == self.Status.RETURNED and not self.return_date:
			raise ValidationError({"return_date": "A returned loan must have a return date."})
		if self.status == self.Status.ISSUED and self.return_date:
			raise ValidationError({"return_date": "An issued loan cannot have a return date."})

	@property
	def overdue_days(self):
		end_date = self.return_date or timezone.localdate()
		return max((end_date - self.due_date).days, 0)

	@property
	def is_overdue(self):
		return self.status == self.Status.ISSUED and self.overdue_days > 0

	def __str__(self):
		return f"{self.book} - {self.member} ({self.get_status_display()})"


class Fine(models.Model):
	loan = models.OneToOneField(Loan, on_delete=models.CASCADE, related_name="fine")
	amount = models.DecimalField(max_digits=8, decimal_places=2, default=0)
	is_paid = models.BooleanField(default=False)
	paid_at = models.DateTimeField(null=True, blank=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ["-updated_at"]

	def __str__(self):
		return f"{self.loan.member.name}: ${self.amount}"
