import doctest
import unittest


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocFileSuite('README.txt',
                                       optionflags=doctest.ELLIPSIS))
    return suite
