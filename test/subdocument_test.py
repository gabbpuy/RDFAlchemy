# -*- coding: utf-8 -*
import unittest

from rdfalchemy import rdfSingle, rdfMultiple
from rdfalchemy.namespaces import DC, BIBO, FOAF, SKOS
from rdfalchemy.rdfs_subject import rdfsSubject


class Document(rdfsSubject):
    rdf_type = BIBO.Document
    title = rdfSingle(DC['title'])
    alt_titles = rdfMultiple(DC.alt)
    date = rdfSingle(DC.date)
    issued = rdfSingle(DC.issued)
    modified = rdfSingle(DC.modified)
    creators = rdfMultiple(DC.creator)
    authorList = rdfMultiple(BIBO.authorList)
    subjects = rdfMultiple(DC.subject, range_type=SKOS.Concept)


class Book(Document):
    rdf_type = BIBO.Book
    publisher = rdfSingle(DC.publisher, range_type=FOAF.Organization)
    series = rdfSingle(DC.isPartOf, range_type=BIBO.Series)


class SubdocumentTest(unittest.TestCase):

    def test_subcocument(self):
        x = Book(title="Some Title")
        y = Document(title="Another Title")
        assert len(list(Document.ClassInstances())) == 2, "wanted 2 ... one book and one document"
        for document in Document.ClassInstances():
            print(document.title)
