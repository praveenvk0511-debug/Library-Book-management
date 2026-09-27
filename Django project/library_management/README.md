# Stacks Campus Library

A college-level Django application for a small campus library. It demonstrates Django models and relationships, model forms, authentication, role checks, CRUD operations, admin customization, templates, static assets, migrations, and tests.

## Run Locally (Windows)

From the workspace folder, activate the provided virtual environment and install the recorded dependencies:

```powershell
cd "D:\Django project"
.\.venv\Scripts\Activate.ps1
cd library_management
pip install -r requirements.txt
```

If PowerShell blocks activation, use `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in that terminal, then activate again. You can also skip activation and run `..\.venv\Scripts\python.exe manage.py ...` from the project folder.

Prepare the database, create a librarian account, and start Django:

```powershell
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_demo
python manage.py runserver
```

Open <http://127.0.0.1:8000/> for the catalogue or <http://127.0.0.1:8000/admin/> for Django Admin. Register a member through **Join the library**. Librarians sign in with a Django account whose `is_staff` flag is enabled; the superuser created above already has it.

## Roles and Workflows

- **Members** can register, sign in, search/filter the public catalogue, inspect book details, and view their own current loans, history, due dates, and fines.
- **Librarians** are Django staff users. They can use the overview, create/edit/delete books and members, add authors/categories, issue and receive books, search/filter loans, and mark fines paid.
- Book issue and return actions use POST requests with CSRF tokens. Stock updates run inside database transactions and recheck the current stock/status before changing it.
- Fine rate is controlled by `DAILY_FINE_AMOUNT` (default `$1.00` per overdue day). A fine is recorded when an overdue book is returned; ongoing overdue estimates are also visible before return.

## Database and Configuration

SQLite is the default and requires no extra service. For MySQL, install the dependencies from `requirements.txt`, create the target database with `utf8mb4`, and set the following environment variables before running migrations:

```powershell
$env:DB_ENGINE = "mysql"
$env:DB_NAME = "library_management"
$env:DB_USER = "root"
$env:DB_PASSWORD = "your-local-password"
$env:DB_HOST = "127.0.0.1"
$env:DB_PORT = "3306"
python manage.py migrate
```

The project package registers PyMySQL as Django's MySQL driver. Keep secrets in environment variables; `.env.example` documents variable names but is not automatically loaded. The fallback key and `DEBUG=1` are for local development only. Before deployment, set a private `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=0`, and an appropriate `DJANGO_ALLOWED_HOSTS`.

## Project Map

```text
library_management/
├── manage.py                         Django command runner
├── library_management/
│   ├── settings.py                   Database, apps, static/media, and auth configuration
│   ├── urls.py                       Root routes and local media serving
│   ├── wsgi.py / asgi.py             Deployment entry points
│   └── __init__.py                   Optional PyMySQL compatibility setup
├── library/
│   ├── models.py                     Authors, categories, books, members, loans, fines
│   ├── forms.py                      Validated catalogue, member, issue, and signup forms
│   ├── views.py                      CRUD, role checks, authentication, issue/return logic
│   ├── urls.py                       Named application routes
│   ├── admin.py                      Searchable and filterable Django Admin
│   ├── migrations/                   Versioned database schema
│   ├── management/commands/seed_demo.py  Repeatable sample data command
│   ├── tests.py                      Workflow and permission tests
│   └── templates/library/            Responsive HTML pages
├── static/css/library.css            Application styling and mobile layout
├── static/js/library.js              Delete confirmation and dashboard chart
├── requirements.txt                  Python dependencies
└── README.md                         Setup, feature, and troubleshooting guide
```

## Database Relationships

- `Member.user` is an optional one-to-one link to Django's built-in `User`; public registration creates both records together.
- `Book.author` and `Book.category` are protected foreign keys. Each author/category can describe many books.
- `Loan.book` and `Loan.member` are protected foreign keys, so a record with history cannot be removed accidentally.
- `Loan.issued_by` records the librarian who processed the issue.
- `Fine.loan` is one-to-one, allowing at most one final fine record per returned loan.

ISBN and email fields are unique. Phone, positive copy counts, copy availability, and loan date/status combinations are validated. Django handles password hashing, sessions, CSRF, and standard password validators.

## Tests and Sample Data

```powershell
python manage.py test library
python manage.py seed_demo
```

`seed_demo` can be run repeatedly without duplicating its example records. The tests use Django's isolated in-memory test database and cover catalogue rendering/search, signup, role access and redirects, stock updates, duplicate returns, member isolation, and fine calculation.

## Common Setup Issues

- **`No module named django`**: activate `.venv` and run `pip install -r requirements.txt` from this directory.
- **`no such table`**: run `python manage.py makemigrations` and `python manage.py migrate`.
- **PowerShell activation is disabled**: use the process-scoped execution policy command above, or invoke the virtual-environment Python executable directly.
- **Uploaded covers do not load**: run with `DEBUG=1`; local media serving is enabled only in development. The `media/` directory is created when the first cover is uploaded.
- **MySQL connection/driver error**: verify MySQL is running, the database exists, the `DB_*` values are set in the same terminal, and `pip install -r requirements.txt` completed.
- **A normal account cannot access the librarian desk**: use Django Admin to mark a trusted account as staff, or create a superuser. Member registration intentionally never grants staff privileges.
- **Fine amount differs from the example**: the app uses `DAILY_FINE_AMOUNT`; restart the server after changing the environment value.