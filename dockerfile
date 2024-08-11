FROM python:3.12-slim

WORKDIR /home/bernardo/Desktop/test/

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8080

CMD ["python", "main.py"]