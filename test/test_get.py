import logging
import sys
import unittest

from rdflib import ConjunctiveGraph

import rdfalchemy
from rdfalchemy.orm import mapper
from rdfalchemy.samples.doap import FOAF
from rdfalchemy.samples.foaf import Person


class TestGet(unittest.TestCase):

    def setUp(self):
        self._stream_handler = logging.StreamHandler(sys.stdout)
        self._logger = logging.getLogger()
        self._logger.addHandler(self._stream_handler)
        Person.db = ConjunctiveGraph()

    def tearDown(self):
        self._logger.removeHandler(self._stream_handler)

    def test_addBNodeKnowsL(self):
        Person.knows = rdfalchemy.rdfList(FOAF.knowsL, range_type=FOAF.Person)
        p1 = Person(first="PhilipL")
        p2 = Person(last="Cooper", first="Ben")
        p3 = Person(last="Cooper", first="Matt")
        p1.knows = [p2, p3]
        p1 = Person.get_by(first="PhilipL")
        assert len(p1.knows) == 2
        del p1

    def test_addBNodeKnowsC(self):
        Person.knows = rdfalchemy.rdfContainer(FOAF.knowsC, range_type=FOAF.Person)
        mapper()
        p1 = Person(first="PhilipC")
        p2 = Person(last="Cooper", first="Ben")
        p3 = Person(last="Cooper", first="Matt")
        p1.knows = [p2, p3]
        p1 = Person.get_by(first="PhilipC")
        assert len(p1.knows) == 2
        del p1

    def test_addBNodeKnowsM(self):
        Person.knows = rdfalchemy.rdfMultiple(FOAF.knowsM, range_type=FOAF.Person)
        mapper()
        p1 = Person(first="PhilipM")
        p2 = Person(last="Cooper", first="Ben")
        p3 = Person(last="Cooper", first="Matt")
        p1.knows = [p2, p3]
        p1 = Person.get_by(first="PhilipM")
        assert len(p1.knows) == 2
        del p1
