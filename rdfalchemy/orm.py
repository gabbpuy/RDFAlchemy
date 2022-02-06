# -*- coding: utf-8 -*-
"""
orm.py

Created by Philip Cooper on 2007-11-23.
Copyright (c) 2007 Openvest. All rights reserved.
"""

import logging
import warnings

from rdfalchemy.rdf_subject import rdfSubject
from rdfalchemy.descriptors import rdfAbstract

log = logging.getLogger(__name__)


def all_sub(cl, been_there=None):
    """
    return all subclasses of the given class
    """
    if been_there is None:
        been_there = set()
    sub = set(cl.__subclasses__()) | been_there
    new_subs = set(cl.__subclasses__()) - been_there
    for one_sub in new_subs:
        sub |= all_sub(one_sub, sub)
    return sub


def mapper(*classes):
    """
    Maps the classes given to allow descriptors with ranges to the
    proper Class of that type

    The default, if no args are provided, is to map recursively all subclasses
    of :class:`~rdfalchemy.rdfSubject.rdfSubject`

    Returns a dict of {rdf_type: mapped_class} for further processing
    """
    if not classes:
        classes = all_sub(rdfSubject)
    class_dict = {str(cl.rdf_type): cl for cl in classes}
    for cl in classes:  # for each class
        for v in cl.__dict__.values():  # for each descriptor
            # if it's a descriptor with a range
            if isinstance(v, rdfAbstract) and v.range_type:
                try:
                    v._mappedClass = class_dict[str(v.range_type)]
                except KeyError:
                    warnings.warn(f"No Class Found\nFailed to map {v} range of {v.range_type}")
    return class_dict

# def mapBase(baseclass):
#    """
#    This maps all classes below baseclass as in mapper()
#    AND puts the dict of {rdf_type: mapped_class}  in
#    an baseclass._type2class attribute
#    """
#    baseclass._type2class = mapper(*all_sub(baseclass))
