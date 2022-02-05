# -*- coding: utf-8 -*-
"""
subclass.py

Created by Philip Cooper on 2008-05-14.
Copyright (c) 2008 Openvest. All rights reserved.
"""
import logging
import sys
import unittest

from rdfalchemy.rdf_subject import rdfSubject
from rdflib import Namespace
from rdfalchemy.rdfs_subject import rdfsSubject

NS = Namespace('http://example.com/project123/')


class A(rdfSubject):
    rdf_type = NS.A


class B(rdfSubject):
    rdf_type = NS.B


class C(B):
    rdf_type = NS.C


class D(C):
    rdf_type = NS.D


class E(A, C):
    rdf_type = NS.D


class As(rdfsSubject):
    rdf_type = NS.As


class Bs(rdfsSubject):
    rdf_type = NS.Bs


class Cs(Bs):
    rdf_type = NS.Cs


class Ds(Cs):
    rdf_type = NS.Ds


class SubclassTest(unittest.TestCase):
    def setUp(self):
        self._stream_handler = logging.StreamHandler(sys.stdout)
        self._logger = logging.getLogger()
        self._logger.addHandler(self._stream_handler)

        a1 = A()
        a2 = A()
        b1 = B()
        b2 = B()
        c1 = C()
        d1 = D()
        d2 = D()
        d3 = D()

    def tearDown(self):
        self._logger.removeHandler(self._stream_handler)

    def test_subclass_1(self):
        """
        Test these things that are just rdfSubject ... no inferencing
        """
        assert len(list(A.ClassInstances())) == 2
        assert len(list(B.ClassInstances())) == 2
        assert len(list(C.ClassInstances())) == 1
        assert len(list(D.ClassInstances())) == 3


class SubclassInferenceTest(unittest.TestCase):

    def setUp(self):
        self._stream_handler = logging.StreamHandler(sys.stdout)
        self._logger = logging.getLogger()
        self._logger.addHandler(self._stream_handler)

        a1 = As()
        a2 = As()
        b1 = Bs()
        b2 = Bs()
        c1 = Cs()
        d1 = Ds()
        d2 = Ds()
        d3 = Ds()

    def tearDown(self):
        self._logger.removeHandler(self._stream_handler)

    def test_subclass_1(self):
        """
        Test these things that are rdfSSubject ... with inferencing
        """
        assert len(list(As.ClassInstances())) == 2, len(list(As.ClassInstances()))
        assert len(list(Bs.ClassInstances())) == 6, len(list(Bs.ClassInstances()))
        assert len(list(Cs.ClassInstances())) == 4, len(list(Cs.ClassInstances()))
        assert len(list(Ds.ClassInstances())) == 3, len(list(Ds.ClassInstances()))
