from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .forms import BookForm, MemberForm
from .models import Author, Book, Category, Fine, Loan, Member

@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class LibraryWorkflowTests(TestCase):
	def setUp(self):
		self.author = Author.objects.create(name="A. Writer")
		self.category = Category.objects.create(name="Fiction")
		self.book = Book.objects.create(
			title="A Useful Story",
			isbn="9780306406157",
			author=self.author,
			category=self.category,
			total_copies=1,
			available_copies=1,
		)
		self.member_user = User.objects.create_user(username="student", password="student-password-321")
		self.member = Member.objects.create(
			user=self.member_user,
			name="Sam Student",
			email="sam@example.edu",
			phone="+1 555 010 2222",
			department="History",
			year=2,
		)
		self.librarian = User.objects.create_user(
			username="librarian", password="library-password-321", is_staff=True
		)

	def test_catalogue_search_and_detail_render(self):
		response = self.client.get(reverse("book_list"), {"q": "writer"})
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "A Useful Story")
		self.assertEqual(self.client.get(reverse("book_detail", args=[self.book.pk])).status_code, 200)

	def test_dashboard_requires_librarian(self):
		self.client.force_login(self.member_user)
		self.assertEqual(self.client.get(reverse("dashboard")).status_code, 403)
		self.client.force_login(self.librarian)
		self.assertEqual(self.client.get(reverse("dashboard")).status_code, 200)

	def test_login_redirects_by_role(self):
		response = self.client.post(reverse("login"), {
			"username": "student",
			"password": "student-password-321",
		})
		self.assertRedirects(response, reverse("book_list"))
		self.client.post(reverse("logout"))
		response = self.client.post(reverse("login"), {
			"username": "librarian",
			"password": "library-password-321",
		})
		self.assertRedirects(response, reverse("dashboard"))

	def test_registration_creates_linked_member(self):
		response = self.client.post(reverse("register"), {
			"username": "newreader",
			"first_name": "New",
			"last_name": "Reader",
			"email": "new.reader@example.edu",
			"phone": "555-010-3456",
			"department": "Biology",
			"year": 1,
			"password1": "UnrelatedPassword998!",
			"password2": "UnrelatedPassword998!",
		})
		self.assertEqual(response.status_code, 302)
		user = User.objects.get(username="newreader")
		self.assertEqual(user.library_member.email, "new.reader@example.edu")

	def test_registration_rejects_invalid_phone(self):
		response = self.client.post(reverse("register"), {
			"username": "badphone",
			"first_name": "Bad",
			"last_name": "Phone",
			"email": "badphone@example.edu",
			"phone": "-------",
			"department": "Biology",
			"year": 1,
			"password1": "UnrelatedPassword998!",
			"password2": "UnrelatedPassword998!",
		})
		self.assertEqual(response.status_code, 200)
		self.assertFalse(User.objects.filter(username="badphone").exists())
		self.assertContains(response, "Enter a valid phone number.")

	def test_issue_and_return_update_inventory_once(self):
		self.client.force_login(self.librarian)
		due_date = timezone.localdate() + timedelta(days=10)
		response = self.client.post(reverse("issue_book"), {
			"member": self.member.pk,
			"book": self.book.pk,
			"due_date": due_date.isoformat(),
		})
		self.assertEqual(response.status_code, 302)
		self.book.refresh_from_db()
		self.assertEqual(self.book.available_copies, 0)
		loan = Loan.objects.get(book=self.book, member=self.member)

		response = self.client.post(reverse("issue_book"), {
			"member": self.member.pk,
			"book": self.book.pk,
			"due_date": due_date.isoformat(),
		})
		self.assertEqual(response.status_code, 200)
		self.assertEqual(Loan.objects.count(), 1)

		self.client.post(reverse("return_book", args=[loan.pk]))
		loan.refresh_from_db()
		self.book.refresh_from_db()
		self.assertEqual(loan.status, Loan.Status.RETURNED)
		self.assertEqual(self.book.available_copies, 1)
		self.client.post(reverse("return_book", args=[loan.pk]))
		self.book.refresh_from_db()
		self.assertEqual(self.book.available_copies, 1)

	@override_settings(DAILY_FINE_AMOUNT="2.50")
	def test_return_calculates_overdue_fine_using_configured_rate(self):
		today = timezone.localdate()
		self.book.available_copies = 0
		self.book.save(update_fields=["available_copies"])
		loan = Loan.objects.create(
			book=self.book,
			member=self.member,
			issue_date=today - timedelta(days=20),
			due_date=today - timedelta(days=5),
		)
		self.client.force_login(self.librarian)
		self.client.post(reverse("return_book", args=[loan.pk]))
		fine = Fine.objects.get(loan=loan)
		self.assertEqual(fine.amount, Decimal("12.50"))
		self.assertFalse(fine.is_paid)

	def test_member_can_only_view_own_loans(self):
		Loan.objects.create(book=self.book, member=self.member)
		self.client.force_login(self.member_user)
		response = self.client.get(reverse("my_loans"))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "A Useful Story")

	def test_forms_reject_duplicate_isbn_negative_copies_and_invalid_phone(self):
		book_form = BookForm(data={
			"title": "Duplicate copy",
			"isbn": "978-0306406157",
			"author": self.author.pk,
			"category": self.category.pk,
			"publisher": "",
			"publication_year": "",
			"description": "",
			"total_copies": "-1",
			"available_copies": "-1",
		})
		self.assertFalse(book_form.is_valid())
		self.assertIn("isbn", book_form.errors)
		self.assertIn("total_copies", book_form.errors)

		member_form = MemberForm(data={
			"name": "Bad Phone",
			"email": "bad.phone@example.edu",
			"phone": "-------",
			"department": "History",
			"year": 1,
		})
		self.assertFalse(member_form.is_valid())
		self.assertIn("phone", member_form.errors)

	@override_settings(DAILY_FINE_AMOUNT="2.50")
	def test_member_and_librarian_see_configured_accrued_fines(self):
		today = timezone.localdate()
		Loan.objects.create(
			book=self.book,
			member=self.member,
			issue_date=today - timedelta(days=10),
			due_date=today - timedelta(days=3),
		)
		paid_loan = Loan.objects.create(
			book=self.book,
			member=self.member,
			issue_date=today - timedelta(days=15),
			due_date=today - timedelta(days=8),
			return_date=today,
			status=Loan.Status.RETURNED,
		)
		Fine.objects.create(loan=paid_loan, amount=Decimal("9.50"), is_paid=True)

		self.client.force_login(self.member_user)
		response = self.client.get(reverse("my_fines"))
		self.assertEqual(response.context["fine_total"], Decimal("7.50"))
		self.assertContains(response, "$7.50")
		self.assertContains(response, "$9.50")

		self.client.force_login(self.librarian)
		response = self.client.get(reverse("fine_list"))
		self.assertContains(response, "$7.50")

	def test_book_with_borrowing_history_cannot_be_deleted(self):
		Loan.objects.create(book=self.book, member=self.member)
		self.client.force_login(self.librarian)
		response = self.client.post(reverse("book_delete", args=[self.book.pk]))
		self.assertRedirects(response, reverse("book_list"))
		self.assertTrue(Book.objects.filter(pk=self.book.pk).exists())
from django.test import TestCase

# Create your tests here.
