FROM acencini/rpi-python-serial-wiringpi
MAINTAINER William Schmitt (will@joulia.io)

RUN apt-get update
RUN apt-get install -y build-essential
RUN apt-get install -y python-dev
RUN apt-get install -y libmysqlclient-dev
RUN apt-get install -y i2c-tools
RUN apt-get install -y python-smbus

RUN mkdir /code
ADD . /code/
WORKDIR /code
RUN pip install -r requirements.txt

CMD sudo -E python main.py
