import logging
import sys
import unittest

from rdflib import ConjunctiveGraph

import rdfalchemy
from rdfalchemy.samples.doap import FOAF
from rdfalchemy.samples.foaf import Person
from rdfalchemy.orm import mapper


class DeleteTest(unittest.TestCase):
    def setUp(self):
        self._stream_handler = logging.StreamHandler(sys.stdout)
        self._logger = logging.getLogger()
        self._logger.addHandler(self._stream_handler)
        Person.db = ConjunctiveGraph()
        Person.knows = rdfalchemy.rdfMultiple(FOAF.knows, range_type=FOAF.Person)

    def tearDown(self):
        self._logger.removeHandler(self._stream_handler)

    def test_start(self):
        assert len(Person.db) == 0
        p = Person(last="Cooper", first="Philip")
        assert len(Person.db) == 3
        del p

    def test_addBNodeKnowsL(self):
        p = Person(last="Cooper", first="Philip")
        Person.knows = rdfalchemy.rdfList(FOAF.knows, range_type=FOAF.Person)
        mapper()
        p1 = Person.get_by(first="Philip")
        p2 = Person(last="Cooper", first="Ben")
        p3 = Person(last="Cooper", first="Matt")
        assert len(Person.db) == 9
        p1.knows = [p2, p3]
        assert len(Person.db) == 14
        del p1.knows
        assert len(Person.db) == 3

    def test_addBNodeKnowsM(self):
        p = Person(last="Cooper", first="Philip")
        Person.knows = rdfalchemy.rdfMultiple(FOAF.knows, range_type=FOAF.Person)
        p1 = Person.get_by(first="Philip")
        p2 = Person(last="Cooper", first="Ben")
        p3 = Person(last="Cooper", first="Matt")
        assert len(Person.db) == 9
        p1.knows = [p2, p3]
        assert len(Person.db) == 11
        del p1.knows
        assert len(Person.db) == 3
