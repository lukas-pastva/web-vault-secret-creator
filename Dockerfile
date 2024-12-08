FROM python:3.8-slim

WORKDIR /app

COPY . /app

# Install Vim and other dependencies
RUN apt-get update && \
    apt-get install -y curl jq vim && \
    rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir flask

EXPOSE 5000

ENV FLASK_APP=app.py

CMD ["flask", "run", "--host=0.0.0.0"]
