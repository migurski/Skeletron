from json import load, dump
from math import pi

from shapely.geometry import asShape

from Skeletron import projected_multigeometry
from Skeletron.output import generalized_multiline

earth_radius = 6378137

def generalize(feature, width, zoom):
    '''
    '''
    buffer = width / 2
    buffer *= (2 * pi * earth_radius) / (2**(zoom + 8))
    
    kwargs = dict(buffer=buffer, density=buffer/2, min_length=8*buffer, min_area=(buffer**2)/4)
    
    geom = asShape(feature['geometry'])
    multigeom = projected_multigeometry(geom)
    generalized = generalized_multiline(multigeom, **kwargs)
    
    if generalized is None:
        return False
    
    feature['geometry'] = generalized.__geo_interface__
    
    return feature

if __name__ == '__main__':

    geojson = load(open('oakland-sample.json'))
    
    features = [generalize(feature, 15, 15) for feature in geojson['features']]
    geojson['features'] = filter(None, features)
    
    dump(geojson, open('output.json', 'w'))