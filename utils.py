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
from weakref import WeakKeyDictionary

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

class subscribable_variable(object):
    '''
    classdocs
    '''
    dataIdentifyService = "http:" + host + "/live/timeseries/identify/"

    def __init__(self, sensor_name):
        '''
        Constructor
        '''
        self.sensor_name = sensor_name
        
        self.data = WeakKeyDictionary()
        self.callback = WeakKeyDictionary()
        
    def subscribe(self,instance,recipe_instance,callback=None):
        self.callback[instance] = instance
        self.recipe_instance = recipe_instance
        self._subscribe(self,instance,self.sensor_name,recipe_instance,'value')
    
    def __get__(self,obj,objtype):
        if obj is None:
            return self
        return self.data.get(obj)
    
    def __set__(self,obj,value):
        self.data[obj] = value
    
    @gen.coroutine #allows the websocket to be yielded    
    def _subscribe(self,instance,sensor_name,recipe_instance,var_type='value'):
        #make sure we have a websocket established
        if self.websocket is None:
            websocket_address = "ws:" + host + "/live/timeseries/socket/"
            logger.info('No websocket established. Establishing at {}'.format(websocket_address))
            self.websocket = yield websocket_connect(websocket_address,on_message_callback=subscribable_variable.on_message)        
        
        #if we dont have a subscription setup yet, sent a subscribe request through the websocket
        if ((sensor_name,recipe_instance)) not in self.subscribers:
            logger.info('Subscribing to {}'.format(sensor_name))
            r = requests.post(self.dataIdentifyService,data={'recipe_instance':recipe_instance,'sensor_name':sensor_name})
            idSensor = r.json()['sensor']
            
            self.idSensor = idSensor
            self.recipeInstance = recipe_instance
            self.subscribers[(idSensor,recipe_instance)] = {'descriptor':self,'instance':instance,'var_type':var_type}
            
            logger.debug('Id is {}'.format(idSensor))
            
            logger.debug("Subscribing with {}".format(self.websocket))
            self.websocket.write_message(json.dumps({'recipe_instance':self.recipeInstance,'sensor':self.idSensor,'subscribe':True}))
                        
            logger.debug('Subscribed')
    
    @classmethod        
    def on_message(cls,response,*args,**kwargs):
        if response is not None:
            data = json.loads(response)
            logger.debug('websocket sent: {}'.format(data))
            subscriber = subscribable_variable.subscribers[(data['sensor'],data['recipe_instance'])]
            if subscriber['var_type'] == 'value':
                current_value = subscriber['descriptor'].data[subscriber['instance']]
                current_type = type(current_value)
                subscriber['descriptor'].data[subscriber['instance']] = current_type(data['value'])
                if subscriber['instance'] in subscriber['descriptor'].callback and subscriber['descriptor'].callback[subscriber['instance']] is not None:
                    callback = subscriber['descriptor'].callback[subscriber['instance']]
                    callback(data['value'])
            elif subscriber['var_type'] == 'override':
                subscriber['descriptor'].override[subscriber['instance']] = bool(data['value'])
        else:
            logger.debug('websocket closed')

    websocket = None
    subscribers = {}

class overridable_variable(subscribable_variable):
    def __init__(self, sensor_name):
        '''
        Constructor
        '''
        super(overridable_variable,self).__init__(sensor_name)
        self.overridden = WeakKeyDictionary()
    
    #override the subscribe method so we can add another subscription to the override time series
    def subscribe(self,instance,recipe_instance):
        super(overridable_variable,self).subscribe(self,instance,recipe_instance)
        self._subscribe(self,instance,self.sensor_name + "Override",recipe_instance,'value')
    
    #override the __set__ function to check if an override is not in place on the variable before allowing to go to the normal __set__
    def __set__(self,obj,value):
        if not self.overridden.get(obj): 
            super(overridable_variable,self).__set__(obj,value)
                
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
                    if value is None: value = 0. #TODO: make server accept None
                    if value is True: value = 'true'
                    if value is False: value = 'false'
                    r = requests.post(self.dataPostService,
                        data={'time':sampleTime,'recipe_instance':self.recipeInstance,
                            'value': value,
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
    