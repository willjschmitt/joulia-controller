# joulia-controller
[![Build Status](https://travis-ci.org/willjschmitt/joulia-controller.svg?branch=develop)](https://travis-ci.org/willjschmitt/joulia-controller) [![Coverage Status](https://coveralls.io/repos/github/willjschmitt/joulia-controller/badge.svg?branch=develop)](https://coveralls.io/github/willjschmitt/joulia-controller?branch=develop)

Controller for the electric brewing hardware.

## Quickstart
Install Raspbian on a fresh SD card, and boot your Raspberry Pi.

Enable SSH (optional), for installing remotely. Make sure the password for the
main account is changed to a secure password. Enable I2C and SPI.

Install Anaconda (Miniconda), using the default options (installing to
`/home/pi/miniconda`):
```
wget http://repo.continuum.io/miniconda/Miniconda3-latest-Linux-armv7l.sh
bash Miniconda3-latest-Linux-arm71.sh
```
Answer all questions posed.

Clone the source:
```git clone https://github.com/willjschmitt/joulia-controller.git```

Create a conda environment and install the dependencies:
```
cd joulia-controller
/home/pi/miniconda3/bin/conda create --name joulia-controller python=3
source /home/pi/miniconda3/bin/activate joulia-controller
pip install -r requirements.txt
```

Create a log directory for joulia and change the owner to pi:
```
sudo mkdir /var/log/joulia
sudo chown pi:pi /var/log/joulia
```

### Automatic Startup
To automatically, launch the software on startup, install the contents from
`crontab` into the root cron table using:
```
sudo crontab -e
```

In the crontab, you must update the environment variables in angle brackets per
the definitions:
 * `JOULIA_WEBSERVER_HOST` - The webserver this controller should stream data to
   (usually `joulia.io`)
 * `JOULIA_WEBSERVER_AUTHTOKEN` - The authtoken provided in your dashboard on
   joulia.io, used to authenticate the controller and identify controller
   information.

### Manual Startup
Run the controller:
```
cd joulia-controller
source /home/pi/miniconda3/bin/activate joulia-controller
export JOULIA_WEBSERVER_HOST=joulia.io
export JOULIA_WEBSERVER_AUTHTOKEN=<insert token>
python main.py
```

## Connections to Hardware
This project is meant to be run on a Raspberry Pi and makes use of the GPIO pins.

### Analog Measurement
Make sure I2C is appropriately turned on on the Raspberry Pi. Install the Arduino I2C Analog Reader software onto the Arduino, so it can communicate the temperature measurements to the Raspberry Pi.

### Digital Control
Connect the Solid State Relay input gate for the Boil Kettle to Pin 0 on the Raspberry Pi.
Connect the Solid State Relay input gate for the Main Pump to Pin 1 on the Raspberry Pi.

## Related Projects
This project is part of the series of projects for the Joulia Brewing System:
* [joulia-webserver](https://github.com/willjschmitt/joulia-webserver) - Remote webserver to log data and allow for livestreaming of data to other clients and receive commands from other clients.
* [joulia-controller](https://github.com/willjschmitt/joula-controller) - This project.
* joulia-fermentation - Planned project to control the fementation operations.

## Licensing
Copyright 2016 William Schmitt. All Rights Reserved.

The intention is to make this project open-sourced, but at this moment is maintained under personal copyright until a few things can be worked through.
