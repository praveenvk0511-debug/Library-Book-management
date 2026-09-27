from django.core.management.base import BaseCommand
from django.db import transaction

from library.models import Author, Book, Category, Member


class Command(BaseCommand):
    help = "Add a small, repeatable set of sample library records."

    @transaction.atomic
    def handle(self, *args, **options):
        fiction, _ = Category.objects.get_or_create(
            name="Fiction",
            defaults={"description": "Novels and short stories."},
        )
        computing, _ = Category.objects.get_or_create(
            name="Computing",
            defaults={"description": "Software, systems, and computer science."},
        )
        nonfiction, _ = Category.objects.get_or_create(
            name="Nonfiction",
            defaults={"description": "Ideas, habits, and real-world topics."},
        )
        author_objects = {
            name: Author.objects.get_or_create(name=name)[0]
            for name in ("Mary Shelley", "James Clear", "B. Kernighan")
        }
        examples = [
            {
                "title": "Frankenstein",
                "isbn": "9780141439471",
                "author": author_objects["Mary Shelley"],
                "category": fiction,
                "publisher": "Penguin Classics",
                "publication_year": 1818,
                "description": "A landmark novel of creation, responsibility, and belonging.",
                "total_copies": 4,
                "available_copies": 4,
            },
            {
                "title": "Atomic Habits",
                "isbn": "9780735211292",
                "author": author_objects["James Clear"],
                "category": nonfiction,
                "publisher": "Avery",
                "publication_year": 2018,
                "description": "A practical guide to small changes and lasting routines.",
                "total_copies": 3,
                "available_copies": 3,
            },
            {
                "title": "The C Programming Language",
                "isbn": "9780131103627",
                "author": author_objects["B. Kernighan"],
                "category": computing,
                "publisher": "Prentice Hall",
                "publication_year": 1988,
                "description": "A foundational introduction to the C language.",
                "total_copies": 2,
                "available_copies": 2,
            },
        ]
        for book in examples:
            Book.objects.get_or_create(isbn=book["isbn"], defaults=book)

        Member.objects.get_or_create(
            email="reader@example.edu",
            defaults={
                "name": "Jordan Reader",
                "phone": "555-010-1000",
                "department": "Humanities",
                "year": 2,
            },
        )
        self.stdout.write(self.style.SUCCESS("Sample books, authors, categories, and one member are ready."))