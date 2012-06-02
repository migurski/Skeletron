Skeletron
=========

Skeletron generalizes collections of lines to a specific spherical mercator
zoom level and pixel precision, using a polygon buffer and voronoi diagram as
described in a 1996 paper by Alnoor Ladak and Roberto B. Martinez, "Automated
Derivation of High Accuracy Road Centrelines Thiessen Polygons Technique"
(http://proceedings.esri.com/library/userconf/proc96/TO400/PAP370/P370.HTM).

Required dependencies:
  - qhull binary (http://www.qhull.org)
  - shapely 1.2+ (http://pypi.python.org/pypi/Shapely)
  - pyproj (http://code.google.com/p/pyproj)
  - networkx 1.5+ (http://networkx.lanl.gov)
  - StreetNames 0.1+ (https://github.com/nvkelso/map-label-style-manual/tree/master/tools/street_names)

You'd typically use it via one of the provided utility scripts, currently
just these two:

skeletron-osm-streets.py

  Accepts OpenStreetMap XML input and generates GeoJSON output for streets
  using the "name" and "highway" tags to group collections of ways.

skeletron-osm-route-rels.py

  Accepts OpenStreetMap XML input and generates GeoJSON output for routes
  using the "network", "ref" and "modifier" tags to group relations.
  More on route relations: http://wiki.openstreetmap.org/wiki/Relation:route

The Name
--------

The first two implementations of Skeletron used the "straight skeleton" of
a polygon to find a generalized center, and ultimately didn't work very well.

The straight skeleton:
    http://twak.blogspot.com/2009/01/that-straight-skeleton-again.html

How it's useful for maps:
    http://aci.ign.fr/Leicester/paper/Haunert-v2-ICAWorkshop.pdf
