# -*- encoding: utf-8 -*-
import logging
import sys
import unittest

import rdfalchemy
from rdfalchemy.rdf_subject import rdfSubject
from rdfalchemy.descriptors import rdfLocale
from rdfalchemy.samples.doap import Project
from rdfalchemy.namespaces import DOAP


class TestLocale(unittest.TestCase):
    def setUp(self):
        self._stream_handler = logging.StreamHandler(sys.stdout)
        self._logger = logging.getLogger()
        self._logger.addHandler(self._stream_handler)

        rdfSubject.db.parse('rdfalchemy/samples/schema/doap.rdf')

        Project.ls = rdfalchemy.rdfSingle(rdfalchemy.RDFS.label, cacheName='ls')
        Project.lm = rdfalchemy.rdfMultiple(rdfalchemy.RDFS.label, cacheName='lm')
        Project.len = rdfLocale(rdfalchemy.RDFS.label, 'en')
        Project.les = rdfLocale(rdfalchemy.RDFS.label, 'es')
        Project.lfr = rdfLocale(rdfalchemy.RDFS.label, 'fr')

    def tearDown(self):
        self._logger.removeHandler(self._stream_handler)

    def test_en_es(self):
        p = Project(DOAP.SVNRepository)
        assert p.len == 'Subversion Repository', p.len
        assert p.les == 'Repositorio Subversion', p.les
        assert p.lfr == 'D\xe9p\xf4t Subversion', p.lfr
