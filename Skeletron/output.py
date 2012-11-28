from pickle import dumps as pickleit
from tempfile import mkstemp
from os import write, close

import logging

from shapely.geometry import LineString

from . import multiline_centerline, mercator, _GraphRoutesOvertime

def multilines_geojson(multilines, key_properties, buffer, density, min_length, min_area):
    """
    """
    geojson = dict(type='FeatureCollection', features=[])

    for (key, multiline) in sorted(multilines.items()):
        
        logging.info('%s...' % ', '.join(key).encode('ascii', 'ignore'))
        
        try:
            centerline = multiline_centerline(multiline, buffer, density, min_length, min_area)
        
        except _GraphRoutesOvertime, e:
            #
            # Catch overtimes here because they seem to affect larger networks
            # and therefore most or all of a complex multiline. We'll keep the
            # key and a pickled copy of the offending graph.
            #
            logging.error('Graph routes went overtime')
            
            handle, fname = mkstemp(dir='.', prefix='graph-overtime-', suffix='.txt')
            write(handle, repr(key) + '\n' + pickleit(e.graph))
            close(handle)
            continue
        
        if not centerline:
            continue
        
        for geom in centerline.geoms:
            coords = [mercator(*point, inverse=True) for point in geom.coords]
            geometry = LineString(coords).__geo_interface__
            feature = dict(geometry=geometry, properties=key_properties(key))

            geojson['features'].append(feature)

    return geojson