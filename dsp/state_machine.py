"""State Machine library for implementing conditional state machines that
operate on an object.
"""

import time

from variables import BidirectionalVariable


class StateMachine(object):
    """A state machine implementation with a storage of states as
    methods.

    Attributes:
        state: The current state method the state machine is on.
        id: The current state index id the state machine is on.
        state_time_change: The time the state was changed to the current state.
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
    _id = BidirectionalVariable('state')

    def __init__(self, parent):
        self.parent = parent
        self.states = []

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
        """Adds a single state to the end of the states list. Should be called
        by the State upon initialization.

        Args:
            state: A State to add to the state array.
        """
        assert isinstance(state, State)
        self.states.append(state)

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value):
        assert value is None or value < len(self.states)

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
            return self.state(self.parent)
        else:
            return None

    def _time(self):
        return self.clock.time()

    def next_state(self):
        """Advances the current state to the next state in the state machine.

        If the current state is the last state, sets the current state to None.

        If the current state is None, advances to the first state.
        """
        if self.id is None:
            self.id = 0
        elif self.id == len(self.states) - 1:
            self.id = None
        else:
            self.id += 1

    def previous_state(self):
        """Moves the current state to the previous state in the state machine.

        If the current state is the first state, sets the current state to None.

        If the current state is None, keeps state set to None.
        """
        if self.id is None:
            self.id = None
        elif self.id == 0:
            self.id = None
        else:
            self.id -= 1

    def set_state_by_name(self, class_name):
        """Sets the state by the class name of the state."""
        for state in self.states:
            if state.__class__.__name__ == class_name:
                self.state = state


class State(object):
    """A State that can be held by the StateMachine.

    Attributes:
        state_machine: The StateMachine the State is registered with. The
    """

    def __init__(self, state_machine):
        self.state_machine = state_machine
        self.state_machine.add_state(self)

    def __call__(self, instance):
        """Code to be executed when this state should be evaluated."""
        raise NotImplementedError()
