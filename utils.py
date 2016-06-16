'''
Created on Apr 14, 2016

@author: William
'''

from tornado.websocket import websocket_connect
from tornado import gen
from tornado import ioloop

import json
import requests
import datetime
import functools
import pytz

import gpiocrust

import logging
logger = logging.getLogger(__name__)

from settings import host
from settings import datastream_frequency

def rsetattr(obj, attr, val):
    pre, _, post = attr.rpartition('__')
    return setattr(rgetattr(obj, pre) if pre else obj, post, val)

def rgetattr(obj, attr):
    return functools.reduce(getattr, [obj]+attr.split('__'))

class subscribableVariable(object):
    '''
    classdocs
    '''
    dataIdentifyService = "http:" + host + "/live/timeseries/identify/"

    def __init__(self, instance, varName, sensorName,recipeInstance):
        '''
        Constructor
        '''
        self.instance = instance
        self.varName = varName
        
        #add new subscription to class vars
        self.subscribe(sensorName, recipeInstance, 'value')
        
    @property
    def value(self): return getattr(self.instance,self.varName)
    @value.setter
    def value(self,value):
        setattr(self.instance,self.varName,value)
    
    @gen.coroutine #allows the websocket to be yielded    
    def subscribe(self,name,recipeInstance,var_type='value'):
        if self.websocket is None:
            websocket_address = "ws:" + host + "/live/timeseries/socket/"
            logger.info('No websocket established. Establishing at {}'.format(websocket_address))
            self.websocket = yield websocket_connect(websocket_address,on_message_callback=subscribableVariable.on_message)        
        
        if ((name,recipeInstance)) not in self.subscribers:
            logger.info('Subscribing to {}'.format(name))
            r = requests.post(self.dataIdentifyService,data={'recipe_instance':recipeInstance,'name':name})
            idSensor = r.json()['sensor']
            
            self.idSensor = idSensor
            self.recipeInstance = recipeInstance
            self.subscribers[(idSensor,recipeInstance)] = (self,var_type)
            
            logger.debug('Id is {}'.format(idSensor))
            
            logger.debug("Subscribing with {}".format(self.websocket))
            self.websocket.write_message(json.dumps({'recipe_instance':self.recipeInstance,'sensor':self.idSensor,'subscribe':True}))
                        
            logger.debug('Subscribed')
    
    @classmethod        
    def on_message(cls,response,*args,**kwargs):
        if response is not None:
            data = json.loads(response)
            logger.debug('websocket sent: {}'.format(data))
            subscriber = subscribableVariable.subscribers[(data['sensor'],data['recipe_instance'])]
            subscriber[0].value = type(subscriber[0].value)(data['value'])            
        else:
            logger.debug('websocket closed')

    websocket = None
    subscribers = {}

# @gen.coroutine #allows the websocket to be yielded
# class overridableVariable(object):
#     '''
#     classdocs
#     '''
#     dataIdentifyService = "http:" + host + "/live/timeseries/identify/"
#     def __init__(self, sensorName,recipeInstance):
#         '''
#         Constructor
#         '''
#         self.value = None
#         self.overridden = False
#         
#         #add new subscription to class vars
#         self.subscribe(sensorName, recipeInstance, 'value')
#         self.subscribe(sensorName+"Override", recipeInstance, 'override')
#     
#     def subscribe(self,name,recipeInstance,type='value'):
#         if ((name,recipeInstance)) not in self.subscribers:
#             r = requests.post(self.dataIdentifyService,data={'recipe_instance':recipeInstance,'name':name})
#             idSensor = r.json()['sensor']
#             self.subscribers[(idSensor,recipeInstance)] = (self,type)
#             self.websocket.write_message(json.dumps({'recipe_instance':recipeInstance,'sensor':idSensor,'subscribe':True}))
#         
#     @classmethod
#     def on_message(cls,response):
#         data = json.loads(response)
#         logger.debug('websocket sent: {}'.format(data))
#         subscriber = cls.subscribers((data['sensor'],data['recipeInstance']))
#         if subscriber[1] == 'value':
#             subscriber[0].value = data['value']
#         elif subscriber[1] == 'override':
#             subscriber[0].overridden = data['value']
#     websocket = websocket_connect("ws:" + host + "/live/timeseries/socket/",on_message_callback=on_message)
#     
#     subscribers = {}
#     
class dataStreamer(object):
    timeOutWait = 10
    
    dataPostService = "http:" + host + "/live/timeseries/new/"
    dataIdentifyService = "http:" + host + "/live/timeseries/identify/"
    
    def __init__(self,streamingClass,recipeInstance):
        self.streamingClass = streamingClass
        self.recipeInstance = recipeInstance
        
        self.sensorMap = {}
        self.timeOutCounter = 0
        
        ioloop.PeriodicCallback(self.postData,datastream_frequency).start()
        
    def register(self,attr,name=None):
        if name is None: name=attr #default to attribute as the name
        if name in self.sensorMap: raise AttributeError('{} already exists in streaming service.'.format(name)) #this makes sure we arent overwriting anything
        self.sensorMap[name] = {'attr':attr} #map the attribute to the server var name
    
    def postData(self):
        if self.timeOutCounter > 0:
            self.timeOutCounter -= 1
        else:
            logger.debug('Data streamer {} sending data.'.format(self))
            
            #post temperature updates to server        
            sampleTime = datetime.datetime.now(tz=pytz.utc).isoformat()
            
            for sensorName,sensor in self.sensorMap.iteritems():
                #get the sensor ID if we dont have it already
                if 'id' not in sensor:
                    try:
                        r = requests.post(self.dataIdentifyService,data={'recipe_instance':self.recipeInstance,'name':sensorName})
                        r.raise_for_status()
                    except requests.exceptions.ConnectionError:
                        logger.info("Server not there. Will retry later.")
                        self.timeOutCounter = self.timeOutWait
                        break
                    except requests.exceptions.HTTPError:
                        logger.info("Server returned error status. Will retry later.")
                        self.timeOutCounter = self.timeOutWait
                        break
                    
                    sensor['id'] = r.json()['sensor']
                    
                #send the data
                try:
                    value = rgetattr(self.streamingClass,sensor['attr'])
                    r = requests.post(self.dataPostService,
                        data={'time':sampleTime,'recipe_instance':self.recipeInstance,
                            'value': value if value is not None else 0., #TODO: make server accept None
                            'sensor':sensor['id']
                        }
                    )
                    r.raise_for_status()
                except requests.exceptions.ConnectionError:
                    logger.info("Server not there. Will retry later.")
                    self.timeOutCounter = self.timeOutWait
                    break
                except requests.exceptions.HTTPError:
                    logger.info("Server returned error status. Will retry later.")
                    self.timeOutCounter = self.timeOutWait
                    break
                    
                
gpio_mock_api_active = 'gpio_mock' in dir(gpiocrust)
    