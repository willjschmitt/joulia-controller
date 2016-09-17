FROM hypriot/rpi-python
MAINTAINER William Schmitt (will@joulia.io)

RUN apt-get update
RUN apt-get install -y build-essential
RUN apt-get install -y python-dev
RUN apt-get install -y libmysqlclient-dev

RUN mkdir /code
ADD . /code/
WORKDIR /code
RUN pip install -r requirements.txt

CMD python main.py

#EXPOSE 8888