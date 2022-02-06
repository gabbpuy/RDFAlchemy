# -*- encoding: utf-8 -*-
"""
sparql_test.py

Created by Philip Cooper on 2008-02-27.
Copyright (c) 2008 Openvest. All rights reserved.
"""

from rdfalchemy.sparql import SPARQLGraph
from rdfalchemy.sparql.sesame2 import SesameGraph
from rdfalchemy import URIRef
from decimal import Decimal
import unittest


class sparql_test:
    def __init__(self):
        pass


class sparql_testTests(unittest.TestCase):
    def setUp(self):
        pass

    def test_initBindings(self):
        query = 'select * where {?s ?P ?oo.?ss ?p \n?oo}'
        initBindings = dict(oo=URIRef("OHO"), P=Decimal("4.40"))
        processed = SPARQLGraph._processInitBindings(query, initBindings)
        assert processed == \
            'select * where {?s "4.40"^^' + \
            '<http://www.w3.org/2001/XMLSchema#decimal> <OHO>.?ss ?p \n<OHO>}'

    def test_initBindings_2(self):
        query = 'select * where {?s ?P ?oo.?ss ?p \n?oo}'
        initBindings = dict(oo=URIRef("OHO"), P=Decimal("4.40"))
        processed = SesameGraph._processInitBindings(query, initBindings)
        assert processed == \
            'select * where {?s "4.40"^^' + \
            '<http://www.w3.org/2001/XMLSchema#decimal> <OHO>.?ss ?p \n<OHO>}'

    def test_sesame_is_sparql(self):
        url = 'https://dbpedia.org/sparql'
        g1 = SesameGraph(url)
        g2 = SPARQLGraph(url)
        q1 = "select distinct ?Concept where {[] a ?Concept} LIMIT 10"
        r1 = set(list(g1.query(q1, result_method='xml')))
        r2 = set(list(g2.query(q1, result_method='xml')))
        assert r1 == r2
        assert len(r1) == 10, "Ooops, %s, %s" % (len(r1), len(r2))

if __name__ == '__main__':
    unittest.main()
