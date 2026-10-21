# Team Tasks AppSec Lab

A small Django application used to practise web development,
HTTP behavior, secure rendering, input validation and security
regression testing.

## Current features

- Task list and detail pages
- Case-insensitive task search
- Duplicate query-parameter rejection
- HTML auto-escaping demonstrations
- JSON health endpoint
- HTTP form and parameter lab
- Automated Django tests

## Security behaviors

- User-controlled search values are HTML-escaped
- Duplicate single-value parameters are rejected
- Oversized search queries are rejected
- Unsupported HTTP methods receive 405
- Missing resources receive 404
- Health responses expose minimal information

## Requirements

- Python 3.14
- Django 5.2
- Git

## Setup on Windows

```powershell
py -3.14 -m venv .venv

.\.venv\Scripts\python.exe -m pip install `
    --upgrade pip

.\.venv\Scripts\python.exe -m pip install `
    -r requirements.txt

.\.venv\Scripts\python.exe manage.py migrate
```

## Run the application

```powershell
.\.venv\Scripts\python.exe manage.py runserver
```

Open <http://127.0.0.1:8000/tasks/> in your browser.

## Available routes

| Route | Purpose |
|---|---|
| `/tasks/` | List and search tasks |
| `/tasks/<id>/` | Display one task |
| `/health/` | Minimal JSON health check |
| `/http-form/` | Form submission and validation lab |
| `/http-lab/` | Query-parameter and HTTP behavior lab |
| `/admin/` | Django administration |

Example search:

```text
http://127.0.0.1:8000/tasks/?q=http
```

## Run the tests

```powershell
.\.venv\Scripts\python.exe manage.py test
```

The test suite checks successful requests, invalid input, HTTP method
restrictions, missing resources, duplicate parameters and HTML escaping.

## Project structure

```text
appsec-lab/
├── config/                 Django project configuration
├── tasks/                  Task application
│   ├── templates/tasks/    HTML templates
│   ├── tests.py            Behavior and security regression tests
│   ├── urls.py             Application routes
│   └── views.py            Request handling and validation
├── manage.py               Django command-line entry point
├── requirements.txt        Pinned Python dependencies
└── appsec_day6.md          Day 6 learning notes
```

## Configuration

`DJANGO_SECRET_KEY` can be provided through an environment variable:

```powershell
$env:DJANGO_SECRET_KEY = "replace-with-a-random-development-secret"
```

The fallback secret in `config/settings.py` is intended only for local
development. A deployed environment must provide its own secret and disable
debug mode.

## Known limitations

- Tasks are stored in an in-memory Python list and reset when the application
  restarts.
- Form submissions are validated but are not persisted.
- Authentication and authorization are not implemented.
- `DEBUG=True` is intended only for local development.
- The application is a learning lab and is not production-ready.
- The security tests cover only the documented routes, inputs and rendering
  contexts.