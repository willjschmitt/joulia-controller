'''
Created on Apr 8, 2016

@author: William
'''

import time

class stateMachine(object):
    '''
    classdocs
    '''
    def __init__(self, parent):
        '''
        Constructor
        '''
        self.states = []
        self.state = None
        self.parent = parent
    
    def evaluate(self):
        if self.state is not None: self.state(self.parent)
    
    def addState(self,state):
        self.states.append(state)
        
    def changeState(self,stateRequested):
        self.parent.state_t0 = time.time()
        if stateRequested is None:
            self.state = None
        else:
            for state in self.states:
                if isinstance(stateRequested, basestring):
                    if state.__name__ == stateRequested: self.state = state
                else:
                    if state == stateRequested: self.state = state
    
    @property
    def id(self): return self.states.index(self.state)
    @id.setter
    def id(self,value): self.state = self.states[value]