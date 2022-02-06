"""

"""
import cgi
import os
import re
import urllib.parse

from rdflib import ConjunctiveGraph


def create_engine(url='', identifier="", create=False):
    """
    :returns: returns an opened rdflib ConjunctiveGraph

    :param url: a string of the url
    :param identifier: URIRef of the default context for writing e.g.:

      - create_engine('sleepycat://~/working/rdf_db')
      - create_engine('kyotocabinet://~/working/rdf_db')
      - create_engine(
            'sesame://www.example.com:8080/openrdf-sesame/repositories/Test')
      - create_engine('sparql://www.example.com:2020/sparql')

    for sqlalchemy, prepend the string "sqlachemy+" to a valid SQLAlchemy dburi
    form:

      - create_engine('sqlalchemy+sqlite://')
      - create_engine('sqlalchemy+sqlite:////absolute/path/to/foo.db')
      - create_engine('sqlalchemy+mysql://myname@localhost/rdflibdb')
      - create_engine('sqlalchemy+postgresql://myname@localhost/rdflibdb')

    etc.
    :param create: create if missing flag
    """
    if url == '' or url.startswith('IOMemory'):
        db = ConjunctiveGraph('IOMemory')
    elif url.lower().startswith('sleepycat://'):
        db = ConjunctiveGraph('Sleepycat', identifier=identifier)
        openstr = os.path.abspath(os.path.expanduser(url[12:]))
        db.open(openstr, create=create)
    elif url.lower().startswith('kyotocabinet://'):
        db = ConjunctiveGraph('Kyotocabinet', identifier=identifier)
        openstr = os.path.abspath(os.path.expanduser(url[15:]))
        db.open(openstr, create=create)
    elif url.lower().startswith('sqlalchemy+'):
        db = ConjunctiveGraph('SQLAlchemy', identifier=identifier)
        db.open(url[11:], create=create)
    elif url.lower().startswith('sesame://'):
        from rdfalchemy.sparql.sesame2 import SesameGraph
        db = SesameGraph("http://" + url[9:])
    elif url.lower().startswith('sparql://'):
        from rdfalchemy.sparql import SPARQLGraph
        db = SPARQLGraph("http://" + url[9:])
    else:
        raise "Could not parse  string '%s'" % url
    return db


def engine_from_config(configuration, prefix='rdfalchemy.', **kwargs):
    """
    Create a new Engine instance using a configuration dictionary.

    :param configuration: a dictionary, typically produced from a config file
        where keys are prefixed, such as `rdfalchemy.dburi`, etc.
    :param prefix: indicates the prefix to be searched for.
    """
    options = {key[len(prefix):]: configuration[key] for key in configuration if key.startswith(prefix)}
    options.update(kwargs)
    url = options.pop('dburi')
    return create_engine(url, **options)


def _parse_rfc1738_args(name):
    """
    parse url str into options
    code orig from sqlalchemy.engine.url
    """
    pattern = re.compile(r'''
            (\w+)://
            (?:
                ([^:/]*)
                (?::([^/]*))?
            @)?
            (?:
                ([^/:]*)
                (?::([^/]*))?
            )?
            (?:/(.*))?
            ''', re.X)

    m = pattern.match(name)
    if m is not None:
        name, username, password, host, port, database = m.group(1, 2, 3, 4, 5, 6)
        if database is not None:
            tokens = database.split(r"?", 2)
            database = tokens[0]
            query = (
                len(tokens) > 1 and dict(
                    cgi.parse_qsl(tokens[1])) or None)
            if query is not None:
                query = dict([(k.encode('ascii'), query[k]) for k in query])
        else:
            query = None
        opts = {
            'username': username, 'password': password, 'host': host,
            'port': port, 'database': database, 'query': query}
        if opts['password'] is not None:
            opts['password'] = urllib.parse.unquote_plus(opts['password'])
        return name, opts
    else:
        raise ValueError("Could not parse rfc1738 URL from string '%s'" % name)
