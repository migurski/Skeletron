from sys import stderr

from shapely.geometry import LineString

from . import multiline_centerline, mercator

def multilines_geojson(multilines, key_properties, buffer, density, min_length, min_area):
    """
    """
    geojson = dict(type='FeatureCollection', features=[])

    for (key, multiline) in sorted(multilines.items()):
        print >> stderr, ', '.join(key), '...'
        
        centerline = multiline_centerline(multiline, buffer, density, min_length, min_area)
        
        if not centerline:
            continue
        
        for geom in centerline.geoms:
            coords = [mercator(*point, inverse=True) for point in geom.coords]
            geometry = LineString(coords).__geo_interface__
            feature = dict(geometry=geometry, properties=key_properties(key))

            geojson['features'].append(feature)

    return geojson