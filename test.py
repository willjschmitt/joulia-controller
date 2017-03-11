"""Runs all test modules. Useful for running through coverage."""

import unittest
import joulia_webserver_client_test
import variables_test


def test():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite((
        loader.loadTestsFromModule(joulia_webserver_client_test),
        loader.loadTestsFromModule(variables_test),))

    runner = unittest.TextTestRunner()
    runner.run(suite)

if __name__ == "__main__":
    test()
