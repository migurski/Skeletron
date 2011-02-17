# totally swiped from http://www.python.org/doc/2.5.2/ext/building.html
from distutils.core import setup, Extension

skeletron = Extension('_skeletron', sources=['skeletron.cpp'], libraries=['CGAL', 'core++'])

setup(name = 'Skeletron',
      version = '0.9.0',
      # description = 'A small package that detects and categorizes blobs in images.',
      # author = 'Michal Migurski',
      # author_email = 'mike@stamen.com',
      # url = 'https://github.com/migurski/Blobdetector',
      packages = ['skeletron'],
      ext_modules = [skeletron],
      #download_url = 'https://github.com/downloads/migurski/Blobdetector/BlobDetector-0.9.0.tar.gz',
      license = 'QPL')
