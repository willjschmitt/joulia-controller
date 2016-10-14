'''
Created on Apr 8, 2016

@author: William
'''

import time

from utils import SubscribableVariable

class StateMachine(object):
    '''A state machine implementation with a storage of states as
    methods.

    Attributes:
        state: The current state method the state machine is on.
        id: The current state index id the state machine is on.
    '''
    _id = SubscribableVariable('state')

    def __init__(self, parent,states):
        '''Creates a state machine initialized at the first state

        Args:
            parent: The object the state machine is a part of. This
                allows for the states to have access to the variables
                in the parent for evaluation. This also allows for
                permission requests and state machine advancement locks.
            states: The states to initialize with. Should be a
                list-like object with several functions. Order matters,
                and the states should be loaded chronologically, if
                they state machine is to be evaluated in a serial
                manner.
        '''
        self.states = states
        self.parent = parent

        self._id = 0

    def register(self,recipe_instance):
        '''Registers all `SubscribableVariable`'s.

        Args:
            recipe_instance: The recipe instance to watch the
                `SubscribableVariable`'s on.
        '''
        StateMachine._id.subscribe(self,recipe_instance,callback=None)

    def evaluate(self):
        '''Executes the current state, which is a method, passing
        the parent to the state method'''
        if self.state is not None:
            self.state(self.parent)

    def add_state(self,state):
        '''Adds a single state to the end of the states list

        Args:
            state: A method to add to the state array
        '''
        self.states.append(state)

    def add_states(self,states):
        '''Adds all of the states to the end of the states list

        Args:
            state: A list of methods to add to the state array
        '''
        self.states += states

    def change_state(self,state_requested):
        '''Adjusts the current state of the state machine to the
        state requested.

        Args:
            state_requested: The state to change to. Can be the
                actual method or the string `__name__` of the method.
        '''
        self.parent.state_t0 = time.time()
        if state_requested is None:
            self.id = 0
        else:
            for i,state in enumerate(self.states):
                if ((isinstance(state_requested, basestring)
                     and state.__name__ == state_requested)
                    or ( state == state_requested )):
                    self.id = i
                    break

    @property
    def state(self):
        return self.states[min(self.id,len(self.states)-1)]
    @state.setter
    def state(self,val):
        self.id = self.states.index(val)

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self,value):
        if self.id != value:
            self.parent.request_permission = False
            self.parent.grant_permission = False
        self._id = value
