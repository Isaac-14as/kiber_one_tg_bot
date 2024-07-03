FROM python:3.11.8

RUN mkdir /tg_bot

WORKDIR /tg_bot

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY . .

EXPOSE 9000

CMD ["python3", "main.py"]
