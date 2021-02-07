FROM python:3.8

RUN apt-get update && apt-get install -y graphviz graphviz-dev

RUN mkdir /app
COPY . /app
WORKDIR /app

RUN pip3 install -r requirements.txt

CMD ["python", "/app/api.py"]