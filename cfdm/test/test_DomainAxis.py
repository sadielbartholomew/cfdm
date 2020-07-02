from __future__ import print_function

import datetime
import inspect
import os
import unittest

import numpy

import cfdm


class DomainTest(unittest.TestCase):
    def setUp(self):
        # Disable log messages to silence expected warnings
        cfdm.log_level('DISABLE')
        # Note: to enable all messages for given methods, lines or
        # calls (those without a 'verbose' option to do the same)
        # e.g. to debug them, wrap them (for methods, start-to-end
        # internally) as follows:
        # cfdm.log_level('DEBUG')
        # < ... test code ... >
        # cfdm.log_level('DISABLE')

        self.filename = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'test_file.nc')
        f = cfdm.read(self.filename)
        self.assertTrue(len(f)==1, 'f={!r}'.format(f))
        self.f = f[0]

        self.test_only = []

    def test_DomainAxis__repr__str_construct_type(self):
        if self.test_only and inspect.stack()[0][3] not in self.test_only:
            return

        f = self.f

        for d in f.domain_axes.values():
            _ = repr(d)
            _ = str(d)
            self.assertTrue(d.construct_type == 'domain_axis')

    def test_DomainAxis_equals(self):
        if self.test_only and inspect.stack()[0][3] not in self.test_only:
            return

        f = self.f

        d = f.construct('key%domainaxis0')
        _ = cfdm.DomainAxis(source=d)

        _ = cfdm.DomainAxis(source=f)
            
    def test_DomainAxis_source(self):
        if self.test_only and inspect.stack()[0][3] not in self.test_only:
            return

        f = self.f

        d = list(f.domain_axes.values())[0]
        e = d.copy()

        self.assertTrue(d.equals(d, verbose=3))
        self.assertTrue(d.equals(e, verbose=3))
        self.assertTrue(e.equals(d, verbose=3))

    def test_DomainAxis_size(self):
        if self.test_only and inspect.stack()[0][3] not in self.test_only:
            return

        f = self.f

        d = f.construct('key%domainaxis0')

        d.set_size(99)

        self.assertTrue(d.has_size())
        self.assertTrue(d.get_size() == 99)
        self.assertTrue(d.del_size() == 99)
        self.assertIsNone(d.get_size(None))
        self.assertIsNone(d.del_size(None))
        self.assertFalse(d.has_size())

    def test_DomainAxis_unlimited(self):
        if self.test_only and inspect.stack()[0][3] not in self.test_only:
            return

        f = self.f.copy()

        for d in f.domain_axes.values():
            self.assertFalse(d.nc_is_unlimited())
            d.nc_set_unlimited(False)
            self.assertFalse(d.nc_is_unlimited())
            d.nc_set_unlimited(True)
            self.assertTrue(d.nc_is_unlimited())
            d.nc_set_unlimited(False)
            self.assertFalse(d.nc_is_unlimited())

#--- End: class

if __name__ == '__main__':
    print('Run date:', datetime.datetime.now())
    cfdm.environment(display=False)
    print()
    unittest.main(verbosity=2)
