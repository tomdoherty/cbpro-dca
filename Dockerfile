# syntax=docker/dockerfile:1

FROM python:3.8-slim-buster

WORKDIR /app

ARG CB_KEY
ARG CB_PASS
ARG CB_SECRET
ARG CB_PRODUCT

COPY requirements.txt requirements.txt

RUN pip3 install -r requirements.txt

COPY . .

CMD [ "python3", "main.py" ]
