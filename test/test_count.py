import logging
import sys
import unittest

from rdflib import ConjunctiveGraph

import rdfalchemy
from rdfalchemy.samples.doap import FOAF
from rdfalchemy.samples.foaf import Person


class CountTest(unittest.TestCase):

    def setUp(self):
        self._stream_handler = logging.StreamHandler(sys.stdout)
        self._logger = logging.getLogger()
        self._logger.addHandler(self._stream_handler)
        Person.db = ConjunctiveGraph()

    def tearDown(self):
        self._logger.removeHandler(self._stream_handler)

    def test_start(self):
        assert len(Person.db) == 0
        Person(last="Cooper")
        assert len(Person.db) == 2

    def test_multi(self):
        Person(last="Cooper")
        Person.m = rdfalchemy.rdfMultiple(FOAF.multi)
        Person.l = rdfalchemy.rdfList(FOAF.list)
        Person.c = rdfalchemy.rdfContainer(FOAF.seq)

        p = next(Person.ClassInstances())
        p.m = [1, 2.2, 0, 'a', '', 'c']
        assert len(Person.db) == 8

        p.m = ['a', 'b', 'c']
        assert len(Person.db) == 5

    def test_list(self):
        Person(last="Cooper")
        Person.m = rdfalchemy.rdfMultiple(FOAF.multi)
        Person.l = rdfalchemy.rdfList(FOAF.list)
        Person.c = rdfalchemy.rdfContainer(FOAF.seq)

        # set and reset a items
        p = next(Person.ClassInstances())
        p.m = ['a', 'b', 'c']
        p.l = [10, 2.3, 0, 'A', '', 'C']
        assert len(Person.db) == 18, len(Person.db)

        p.l = [10, 2.3, 0]
        assert len(Person.db) == 12, len(Person.db)

    def test_seq(self):
        Person(last="Cooper")
        Person.m = rdfalchemy.rdfMultiple(FOAF.multi)
        Person.l = rdfalchemy.rdfList(FOAF.list)
        Person.c = rdfalchemy.rdfContainer(FOAF.seq)

        p = next(Person.ClassInstances())
        p.m = ['a', 'b', 'c']
        p.l = [10, 2.3, 0]
        p.c = list(range(10))
        assert len(Person.db) == 24, len(Person.db)

        p.c = ['things', 44]
        assert len(Person.db) == 16, len(Person.db)
