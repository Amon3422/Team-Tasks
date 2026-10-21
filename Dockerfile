FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt /app/requirements.txt

RUN python -m pip install -r requirements.txt

COPY . .

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]