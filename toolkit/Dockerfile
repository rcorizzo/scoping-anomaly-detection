FROM python:3.8

WORKDIR /app

COPY requirements.txt requirements.txt

RUN pip install -r requirements.txt
#since there is no api endpoint it's just as an example, could be changed in the near future(ex. we need port 2022)
EXPOSE 5005 

COPY . .

CMD python main.py