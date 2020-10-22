FROM debian:buster-slim
WORKDIR /usr/src/app

RUN apt-get update && apt-get install -y python python-pip python-mysqldb libldap2-dev libsasl2-dev && rm -rf /var/lib/apt/lists/* 

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
EXPOSE 19211
COPY . .
CMD [ "python", "./server.py"]
