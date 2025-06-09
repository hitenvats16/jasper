FROM python:3.9


WORKDIR /code


COPY ./requirements.txt /code/requirements.txt


RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt


COPY . /code

ENV PORT=8000


EXPOSE 8000

CMD ["python", "-m", "main"]