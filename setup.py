#!/usr/bin/env python

from distutils.core import setup

version = open('VERSION', 'r').read().strip()

setup(name='Skeletron',
      version=version,
      description='Generalizes collections of lines on maps to simpler lines for improved labeling.',
      author='Michal Migurski',
      author_email='mike@stamen.com',
      url='https://github.com/migurski/Skeletron',
      requires=['networkx'],
      packages=['Skeletron'],
      scripts=['skeletron-osm-route-rels.py', 'skeletron-osm-streets.py'],
    # download_url='https://github.com/downloads/migurski' % locals(),
      license='BSD')
