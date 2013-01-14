#!/usr/bin/env python

from distutils.core import setup
from Skeletron import __version__

setup(name='Skeletron',
      version=__version__,
      description='Generalizes collections of lines on maps to simpler lines for improved labeling.',
      author='Michal Migurski',
      author_email='mike@stamen.com',
      url='https://github.com/migurski/Skeletron',
      requires=['networkx', 'StreetNames'],
      packages=['Skeletron'],
      scripts=['skeletron-generalize.py',
               'skeletron-hadoop-mapper.py',
               'skeletron-hadoop-reducer.py',
               'skeletron-osm-route-rels.py',
               'skeletron-osm-streets.py'],
    # download_url='https://github.com/downloads/migurski' % locals(),
      license='BSD')
