FROM ubuntu:latest
MAINTAINER Ekaterina Pisareva 'hanborina2002@gmail.com'
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Yekaterinburg
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
RUN apt-get clean
RUN apt-get update -y
RUN apt-get install -y libpq-dev python3-pip python3-dev python3 build-essential
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
CMD python3 main.py
