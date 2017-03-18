"""Tests for the state_machine module."""

import unittest

from dsp.state_machine import State
from dsp.state_machine import StateMachine
from testing.stub_joulia_webserver_client import StubJouliaHTTPClient
from testing.stub_joulia_webserver_client import StubJouliaWebsocketClient


class TestStateMachine(unittest.TestCase):
    """Tests the StateMachine class."""

    def setUp(self):
        self.state_machine = StateMachine(self, [])

    def test_register_succeeds(self):
        http_client = StubJouliaHTTPClient("fake address")
        ws_client = StubJouliaWebsocketClient("fake address", http_client)
        recipe_instance = 1
        self.state_machine.register(ws_client, recipe_instance)

    def test_add_state(self):
        state = State(self)
        self.state_machine.add_state(state)
        self.assertIn(state, self.state_machine.states)

    def test_add_states(self):
        state1 = State(self)
        state2 = State(self)
        self.state_machine.add_states([state1, state2])
        self.assertIn(state1, self.state_machine.states)
        self.assertIn(state2, self.state_machine.states)

    def test_get_set_id(self):
        state = State(self)
        self.state_machine.add_state(state)
        self.assertIsNone(self.state_machine.id)
        self.state_machine.id = 0
        self.assertEquals(self.state_machine.id, 0)

    def test_set_id_too_high(self):
        with self.assertRaises(AssertionError):
            self.state_machine.id = 10

    def test_get_none_state(self):
        self.assertIsNone(self.state_machine.state)

    def test_get_set_states(self):
        state1 = State(self)
        state2 = State(self)
        self.state_machine.add_states([state1, state2])

        self.state_machine.state = state1
        self.assertIs(self.state_machine.state, state1)
        self.state_machine.state = state2
        self.assertIs(self.state_machine.state, state2)

    def test_bad_state(self):
        state = State(self)
        with self.assertRaises(AssertionError):
            self.state_machine.state = state

    def test_evaluate(self):
        class Foo(State):
            def __call__(self):
                return 12
        foo = Foo(self)
        self.state_machine.add_state(foo)
        self.state_machine.state = foo
        self.assertEquals(self.state_machine.evaluate(), 12)

    def test_evaluate_no_state(self):
        class Foo(State):
            def __call__(self):
                return 12
        foo = Foo(self)
        self.state_machine.add_state(foo)
        self.assertIsNone(self.state_machine.evaluate())


class TestState(unittest.TestCase):
    """Tests the State class."""

    def test_call_unimplemented(self):
        state = State(self)
        with self.assertRaises(NotImplementedError):
            state()
