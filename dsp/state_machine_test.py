"""Tests for the state_machine module."""
# pylint: disable=missing-docstring,too-many-public-methods,too-many-locals,too-many-instance-attributes,blacklisted-name

import unittest

from dsp.state_machine import State
from dsp.state_machine import StateMachine
from testing.stub_joulia_webserver_client import StubJouliaHTTPClient
from testing.stub_joulia_webserver_client import StubJouliaWebsocketClient


class TestStateMachine(unittest.TestCase):
    """Tests the StateMachine class."""

    def setUp(self):
        http_client = StubJouliaHTTPClient("fake address")
        self.ws_client = StubJouliaWebsocketClient("fake address", http_client)
        self.recipe_instance = 0
        self.state_machine = StateMachine(self, self.ws_client,
                                          self.recipe_instance)

    def test_add_state(self):
        # add_state is called by the creation of State
        state = State(self.state_machine)
        self.assertIn(state, self.state_machine.states)

    def test_get_set_id(self):
        State(self.state_machine)
        self.assertIsNone(self.state_machine.index)
        self.state_machine.index = 0
        self.assertEqual(self.state_machine.index, 0)

    def test_set_id_too_high(self):
        with self.assertRaises(AssertionError):
            self.state_machine.index = 10

    def test_get_none_state(self):
        self.assertIsNone(self.state_machine.state)

    def test_get_set_states(self):
        state1 = State(self.state_machine)
        state2 = State(self.state_machine)

        self.state_machine.state = state1
        self.assertIs(self.state_machine.state, state1)
        self.state_machine.state = state2
        self.assertIs(self.state_machine.state, state2)

    def test_bad_state(self):
        other_state_machine = StateMachine(self, self.ws_client,
                                           self.recipe_instance)
        state = State(other_state_machine)
        with self.assertRaises(AssertionError):
            self.state_machine.state = state

    def test_evaluate(self):
        class Foo(State):
            def __call__(self, instance):
                return 12
        foo = Foo(self.state_machine)
        self.state_machine.state = foo
        self.assertEqual(self.state_machine.evaluate(), 12)

    def test_evaluate_no_state(self):
        class Foo(State):
            def __call__(self, instance):
                pass  # pragma: no cover
        Foo(self.state_machine)
        self.assertIsNone(self.state_machine.evaluate())

    def test_next_state(self):
        class Foo(State):
            def __call__(self, instance):
                pass  # pragma: no cover

        class Bar(State):
            def __call__(self, instance):
                pass  # pragma: no cover

        foo = Foo(self.state_machine)
        bar = Bar(self.state_machine)

        self.state_machine.index = None
        self.assertIsNone(self.state_machine.state)
        self.state_machine.next_state()
        self.assertIs(self.state_machine.state, foo)
        self.state_machine.next_state()
        self.assertIs(self.state_machine.state, bar)

    def test_next_state_at_end(self):
        class Foo(State):
            def __call__(self, instance):
                pass  # pragma: no cover

        foo = Foo(self.state_machine)

        self.state_machine.index = 0
        self.assertIs(self.state_machine.state, foo)
        self.state_machine.next_state()
        self.assertIsNone(self.state_machine.state)

    def test_previous_state(self):
        class Foo(State):
            def __call__(self, instance):
                pass  # pragma: no cover

        class Bar(State):
            def __call__(self, instance):
                pass  # pragma: no cover

        foo = Foo(self.state_machine)
        bar = Bar(self.state_machine)

        self.state_machine.index = 1
        self.assertIs(self.state_machine.state, bar)
        self.state_machine.previous_state()
        self.assertIs(self.state_machine.state, foo)
        self.state_machine.previous_state()
        self.assertIsNone(self.state_machine.state)

    def test_previous_state_at_start(self):
        class Foo(State):
            def __call__(self, instance):
                pass  # pragma: no cover

        foo = Foo(self.state_machine)

        self.state_machine.index = 0
        self.assertIs(self.state_machine.state, foo)
        self.state_machine.previous_state()
        self.assertIsNone(self.state_machine.state)
        self.state_machine.previous_state()
        self.assertIsNone(self.state_machine.state)

    def test_set_state_by_name(self):
        class Foo(State):
            def __call__(self, instance):
                pass  # pragma: no cover

        class Bar(State):
            def __call__(self, instance):
                pass  # pragma: no cover

        foo = Foo(self.state_machine)
        bar = Bar(self.state_machine)

        self.state_machine.set_state_by_name("Foo")
        self.assertIs(self.state_machine.state, foo)
        self.state_machine.set_state_by_name("Bar")
        self.assertIs(self.state_machine.state, bar)


class TestState(unittest.TestCase):
    """Tests the State class."""

    def test_call_unimplemented(self):
        http_client = StubJouliaHTTPClient("fake address")
        ws_client = StubJouliaWebsocketClient("fake address", http_client)
        recipe_instance = 0
        state_machine = StateMachine(self, ws_client, recipe_instance)
        state = State(state_machine)
        with self.assertRaises(NotImplementedError):
            state(self)
