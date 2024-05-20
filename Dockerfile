FROM ubuntu:18.04

RUN apt-get update

RUN apt-get install -y python3.7
RUN apt-get install -y python3-pip
RUN apt-get install -y curl
RUN useradd -m -s /bin/bash GahyunServer


COPY gahyun /gahyun

RUN chown -R GahyunServer:root gahyun

WORKDIR /gahyun/

RUN chmod 644 ./main.db
RUN pip3 install --upgrade pip
RUN pip3 install Flask

EXPOSE 8000

USER GahyunServer

WORKDIR /gahyun/

CMD ["python3", "app.py"]
