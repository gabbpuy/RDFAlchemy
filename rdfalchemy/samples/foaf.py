#!/usr/bin/env python
# encoding: utf-8
"""
foaf.py

Created by Philip Cooper on 2007-11-23.
Copyright (c) 2007 Openvest. All rights reserved.
"""
from rdfalchemy import rdfSingle
from rdfalchemy.namespaces import FOAF
from rdfalchemy.rdf_subject import rdfSubject

non_core = True


class Agent(rdfSubject):
    rdf_type = FOAF.Agent
    name = rdfSingle(FOAF.name)
    mbox = rdfSingle(FOAF.mbox)
    openid = rdfSingle(FOAF.openid)


class Person(Agent):
    rdf_type = FOAF.Person
    first = rdfSingle(FOAF.firstName)
    last = rdfSingle(FOAF.surname)
    givenname = rdfSingle(FOAF.givenname)
    surname = rdfSingle(FOAF.surname)
