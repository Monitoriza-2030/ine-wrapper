FROM python:3.9.4-slim

# install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# set work directory
WORKDIR /

# Copy app
COPY ./app /app/

CMD python3 -u server.py