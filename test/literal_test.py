from datetime import datetime
from decimal import Decimal
import logging
import sys
import unittest

from rdfalchemy.literal import Literal
from rdfalchemy.literal import str_to_datetime
from rdfalchemy.namespaces import XSD


class LiteralTest(unittest.TestCase):
    def setUp(self):
        self._stream_handler = logging.StreamHandler(sys.stdout)
        self._logger = logging.getLogger()
        self._logger.addHandler(self._stream_handler)

    def tearDown(self):
        self._logger.removeHandler(self._stream_handler)

    def test_just_for_coverage(self):
        x = str_to_datetime('2008-02-09T10:46:29')
        assert type(x) == datetime

    def test_toPython_decimal(self):
        # test a normal iso
        d = Literal('.1', datatype=XSD.decimal).toPython()
        assert isinstance(d, Decimal)
        payments = [Literal(s, datatype=XSD.decimal) for s in '.1 .1 .1 -.3'.split()]
        assert sum([payment.toPython() for payment in payments]) == 0

    def test_toPython_datetime(self):
        # test a normal iso
        d = Literal('2008-02-09T10:46:29', datatype=XSD.dateTime).toPython()
        assert isinstance(d, datetime)
        d = Literal('2008-02-09T10:46:29Z', datatype=XSD.dateTime).toPython()
        assert isinstance(d, datetime)
        d = Literal('2008-02-09T10:46:29-07:00', datatype=XSD.dateTime).toPython()
        assert isinstance(d, datetime)

        d = Literal('2008-02-09T10:46:29.1', datatype=XSD.dateTime).toPython()
        assert isinstance(d, datetime)
        d = Literal('2008-02-09T10:46:29.123', datatype=XSD.dateTime).toPython()
        assert isinstance(d, datetime)
        d = Literal('2008-02-09T10:46:29.123456', datatype=XSD.dateTime).toPython()
        assert isinstance(d, datetime)
        # test a normal iso with fractional seconds

        d = Literal('2008-02-09 10:46:29', datatype=XSD.dateTime).toPython()
        assert isinstance(d, datetime)
        # test an "almost" iso string
