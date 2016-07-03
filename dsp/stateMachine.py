'''
Created on Apr 8, 2016

@author: William
'''

import time

from utils import subscribable_variable

class stateMachine(object):
    
    _id = subscribable_variable('state')
    
    '''
    classdocs
    '''
    def __init__(self, parent):
        '''
        Constructor
        '''
        self.states = []
        self.parent = parent
        
        self._id = 0
        
    def register(self,recipe_instance):
        stateMachine._id.subscribe(self,recipe_instance,callback=None)
    
    def evaluate(self):
        if self.state is not None: self.state(self.parent)
    
    def addState(self,state):
        self.states.append(state)
        
    def changeState(self,stateRequested):
        self.parent.state_t0 = time.time()
        if stateRequested is None:
            self.id = 0
        else:
            for i,state in enumerate(self.states):
                if ((isinstance(stateRequested, basestring) and state.__name__ == stateRequested)
                    or ( state == stateRequested )):
                    self.id = i
                    break
    
    @property
    def state(self): return self.states[self.id]
    @state.setter
    def state(self,val): self.id = self.states.index(val)
    
    
    @property
    def id(self): return self._id
    @id.setter
    def id(self,value):
        if self.id != value:
            self.parent.requestPermission = False
            self.parent.grantPermission = False
        self._id = value