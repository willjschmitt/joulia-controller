"""State Machine library for implementing conditional state machines that
operate on an object.
"""

import time

from variables import SubscribableVariable


class StateMachine(object):
    """A state machine implementation with a storage of states as
    methods.

    Attributes:
        state: The current state method the state machine is on.
        id: The current state index id the state machine is on.
        state_time_change: The time the state was changed to the current state.
    """
    _id = SubscribableVariable('state')

    def __init__(self, parent, states):
        """Creates a state machine initialized at the first state.

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
        """
        self.states = states
        self.parent = parent

        self._id = None

        self.clock = time
        self.state_time_change = self._time()

    def register(self, client, recipe_instance):
        """Registers all `ManagedVariable`'s.

        Args:
            client: websocket client to register for ManagedVariables
            recipe_instance: The recipe instance to watch the
                `ManagedVariable`'s on.
        """
        StateMachine._id.register(client, self, recipe_instance, callback=None)

    def add_state(self, state):
        """Adds a single state to the end of the states list.

        Args:
            state: A State to add to the state array.
        """
        assert isinstance(state, State)
        self.states.append(state)

    def add_states(self, states):
        """Adds all of the states to the end of the states list

        Args:
            states: A list of methods to add to the state array
        """
        for state in states:
            self.add_state(state)

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value):
        assert value < len(self.states)

        if self._id != value:
            self.parent.request_permission = False
            self.parent.grant_permission = False
        self._id = value

        self.state_time_change = self._time()

    @property
    def state(self):
        if self.id is None:
            return None
        return self.states[self.id]

    @state.setter
    def state(self, state):
        assert state in self.states
        self.id = self.states.index(state)

    def evaluate(self):
        """Executes the current state, which is a method, passing
        the parent to the state method.
        """
        if self.state is not None:
            return self.state()
        else:
            return None

    def _time(self):
        return self.clock.time()


class State(object):
    """A State that can be held by the StateMachine.

    Attributes:
        instance: The object the state operates on.
    """
    def __init__(self, instance):
        self.instance = instance

    def __call__(self):
        """Code to be executed when this state should be evaluated."""
        raise NotImplementedError()
