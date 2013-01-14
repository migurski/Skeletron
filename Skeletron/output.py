from pickle import dumps as pickleit
from tempfile import mkstemp
from os import write, close
from json import dumps

import logging

from shapely.geometry import LineString, MultiLineString, asShape

from . import multigeom_centerline, mercator, _GraphRoutesOvertime, projected_multigeometry
from .util import zoom_buffer

def generalize_geojson_feature(feature, width, zoom):
    ''' Run one GeoJSON feature through Skeletron and return it.
    
        If generalization fails, return False.
    '''
    prop = dict([(k.lower(), v) for (k, v) in feature['properties'].items()])
    name = prop.get('name', prop.get('id', prop.get('gid', prop.get('fid', None))))
    geom = asShape(feature['geometry'])

    buffer = zoom_buffer(width, zoom)
    kwargs = dict(buffer=buffer, density=buffer/2, min_length=8*buffer, min_area=(buffer**2)/4)
    
    logging.info('Generalizing %s, %d wkb, %.1f buffer' % (dumps(name), len(geom.wkb), buffer))
    
    multigeom = projected_multigeometry(geom)
    generalized = generalized_multiline(multigeom, **kwargs)
    
    if generalized is None:
        return False
    
    feature['geometry'] = generalized.__geo_interface__
    
    return feature

def generalize_geometry(geometry, width, zoom):
    ''' Run one geometry through Skeletron and return it.
    
        If generalization fails, return False.
    '''
    buffer = zoom_buffer(width, zoom)
    kwargs = dict(buffer=buffer, density=buffer/2, min_length=8*buffer, min_area=(buffer**2)/4)
    
    logging.debug('Generalizing %s, %d wkb, %.1f buffer' % (geometry.type, len(geometry.wkb), buffer))
    
    multigeom = projected_multigeometry(geometry)
    generalized = generalized_multiline(multigeom, **kwargs)
    
    if generalized is None:
        return False
    
    return generalized

def multilines_geojson(multilines, key_properties, buffer, density, min_length, min_area):
    """
    """
    geojson = dict(type='FeatureCollection', features=[])

    for (key, multiline) in sorted(multilines.items()):
        
        logging.info('%s...' % ', '.join([(p or '').encode('ascii', 'ignore') for p in key]))
        
        try:
            centerline = multigeom_centerline(multiline, buffer, density, min_length, min_area)
        
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

def generalized_multiline(multiline, buffer, density, min_length, min_area):
    '''
    '''
    try:
        centerline = multigeom_centerline(multiline, buffer, density, min_length, min_area)
    
    except Exception, e:
        raise
        logging.error(e)
        return None
    
    if not centerline:
        return None
        
    coords = [[mercator(x, y, inverse=True) for (x, y) in line.coords] for line in centerline]
    geographic = MultiLineString(coords)
    
    return geographic
