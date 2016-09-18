# joulia-controller
Controller for the electric brewing hardware.

## Quickstart
### Environment Variables
For both methods (Docker or manual), environment variables need to be set.
With docker, this is via command line options (`-e ENVVARNAME="ENVVARVALUE"`).
Otherwise set them normally with `set`:
 * `joulia-webserver-HOST` - The webserver this controller should stream data to (usually `//joulia.io`)
 * `joulia-webserver-AUTHTOKEN` - The authtoken provided in your dashboard on joulia.io, used to authenticate the controller and identify controller information.

### From Docker
This project is meant to be run on a Raspberry PI running Docker. 

Hypriot provides a Docker-ready Raspian image, which can save a big hassle,
since Docker is not built for ARM normally. Read more at:
http://blog.hypriot.com/getting-started-with-docker-on-your-arm-device/

Then download and run the docker image:
`docker -d --device /dev/ttyAMA0:/dev/ttyAMA0 --device /dev/mem:/dev/mem --privileged willjschmitt/joulia-controller`

The image needs to run in privileged mode with devices bound in order to access the GPIO pins.

### From Source
Clone the source:
`git clone https://github.com/willjschmitt/joulia-controller.git`

Install the dependencies:
`pip install -r requirements.txt`

Run the controller:
`python main.py`

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
