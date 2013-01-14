from sys import stdin, stdout
from math import hypot, ceil, sqrt, pi
from base64 import b64encode, b64decode
from json import loads as json_decode
from json import dumps as json_encode
from cPickle import loads as unpickle
from cPickle import dumps as pickle
from os.path import splitext
from gzip import GzipFile
from bz2 import BZ2File

from shapely.geometry import Polygon
from shapely.wkb import loads as wkb_decode

def zoom_buffer(width_px, zoom):
    '''
    '''
    zoom_pixels = 2**(zoom + 8)
    earth_width_meters = 2 * pi * 6378137
    meters_per_pixel = earth_width_meters / zoom_pixels
    buffer_meters = meters_per_pixel * width_px / 2
    
    return buffer_meters

def cascaded_union(polys):
    '''
    '''
    if len(polys) == 2:
        return polys[0].union(polys[1])

    if len(polys) == 1:
        return polys[0]
    
    if len(polys) == 0:
        return None
    
    half = len(polys) / 2
    poly1 = cascaded_union(polys[:half])
    poly2 = cascaded_union(polys[half:])
    
    return poly1.union(poly2)

def point_distance(a, b):
    '''
    '''
    try:
        return a.distance(b)

    except ValueError, e:
        if str(e) != 'Prepared geometries cannot be operated on':
            raise
        
        # Shapely sometimes throws this exception, for reasons unclear to me.
        return hypot(a.x - b.x, a.y - b.y)
    
def simplify_line_vw(points, small_area=100):
    """ Simplify a line of points using V-W down to the given area.
    """
    while len(points) > 3:
        
        # For each coordinate that forms the apex of a two-segment
        # triangle, find the area of that triangle and put it into a list
        # along with the index, ordered from smallest to largest.
    
        popped, preserved = set(), set()
        
        triples = zip(points[:-2], points[1:-1], points[2:])
        triangles = [Polygon((p1, p2, p3)) for (p1, p2, p3) in triples]
        areas = [(triangle.area, index) for (index, triangle) in enumerate(triangles)]
        
        # Reduce any segments that makes a triangle whose area is below
        # the minimum threshold, starting with the smallest and working up.
        # Mark segments to be preserved until the next iteration.

        for (area, index) in sorted(areas):
            if area > small_area:
                # nothing more can be removed on this iteration
                break
            
            if (index + 1) in preserved:
                # current index is too close to a previously-preserved one
                continue
            
            preserved.add(index)
            popped.add(index + 1)
            preserved.add(index + 2)
        
        if not popped:
            # nothing was removed so we are done
            break
        
        # reduce the line, then try again
        points = [point for (index, point) in enumerate(points) if index not in popped]
    
    return list(points)

def simplify_line_dp(pts, tolerance):
    """ Pure-Python Douglas-Peucker line simplification/generalization
        
        this code was written by Schuyler Erle <schuyler@nocat.net> and is
          made available in the public domain.
        
        the code was ported from a freely-licensed example at
          http://www.3dsoftware.com/Cartography/Programming/PolyLineReduction/
        
        the original page is no longer available, but is mirrored at
          http://www.mappinghacks.com/code/PolyLineReduction/
    """
    anchor  = 0
    floater = len(pts) - 1
    stack   = []
    keep    = set()

    stack.append((anchor, floater))  
    while stack:
        anchor, floater = stack.pop()
      
        # initialize line segment
        if pts[floater] != pts[anchor]:
            anchorX = float(pts[floater][0] - pts[anchor][0])
            anchorY = float(pts[floater][1] - pts[anchor][1])
            seg_len = sqrt(anchorX ** 2 + anchorY ** 2)
            # get the unit vector
            anchorX /= seg_len
            anchorY /= seg_len
        else:
            anchorX = anchorY = seg_len = 0.0
    
        # inner loop:
        max_dist = 0.0
        farthest = anchor + 1
        for i in range(anchor + 1, floater):
            dist_to_seg = 0.0
            # compare to anchor
            vecX = float(pts[i][0] - pts[anchor][0])
            vecY = float(pts[i][1] - pts[anchor][1])
            seg_len = sqrt( vecX ** 2 + vecY ** 2 )
            # dot product:
            proj = vecX * anchorX + vecY * anchorY
            if proj < 0.0:
                dist_to_seg = seg_len
            else: 
                # compare to floater
                vecX = float(pts[i][0] - pts[floater][0])
                vecY = float(pts[i][1] - pts[floater][1])
                seg_len = sqrt( vecX ** 2 + vecY ** 2 )
                # dot product:
                proj = vecX * (-anchorX) + vecY * (-anchorY)
                if proj < 0.0:
                    dist_to_seg = seg_len
                else:  # calculate perpendicular distance to line (pythagorean theorem):
                    dist_to_seg = sqrt(abs(seg_len ** 2 - proj ** 2))
                if max_dist < dist_to_seg:
                    max_dist = dist_to_seg
                    farthest = i

        if max_dist <= tolerance: # use line segment
            keep.add(anchor)
            keep.add(floater)
        else:
            stack.append((anchor, farthest))
            stack.append((farthest, floater))

    keep = list(keep)
    keep.sort()
    return [pts[i] for i in keep]

def densify_line(points, distance):
    """ Densify a line of points using the given distance.
    """
    coords = [points[0]]
    
    for curr_coord in list(points)[1:]:
        prev_coord = coords[-1]
    
        dx, dy = curr_coord[0] - prev_coord[0], curr_coord[1] - prev_coord[1]
        steps = ceil(hypot(dx, dy) / distance)
        count = int(steps)
        
        while count:
            prev_coord = prev_coord[0] + dx/steps, prev_coord[1] + dy/steps
            coords.append(prev_coord)
            count -= 1
    
    return coords

def polygon_rings(polygon):
    """ Given a buffer polygon, return a series of point rings.
    
        Return a list of interiors and exteriors all together.
    """
    if polygon.type == 'Polygon':
        return [polygon.exterior] + list(polygon.interiors)
    
    rings = []
    
    for geom in polygon.geoms:
        rings.append(geom.exterior)
        rings.extend(list(geom.interiors))
    
    return rings

def open_file(name, mode='r'):
    """
    """
    if name == '-' and mode == 'r':
        return stdin

    if name == '-' and mode == 'w':
        return stdout
    
    base, ext = splitext(name)
    
    if ext == '.bz2':
        return BZ2File(name, mode)

    if ext == '.gz':
        return GzipFile(name, mode)

    return open(name, mode)

def hadoop_feature_line(id, properties, geometry):
    ''' Convert portions of a GeoJSON feature to a single line of text.
    
        Allows Hadoop to stream features from the mapper to the reducer.
        See also skeletron-hadoop-mapper.py and skeletron-hadoop-reducer.py.
    '''
    line = [
        json_encode(id),
        ' ',
        b64encode(pickle(sorted(list(properties.items())))),
        '\t',
        b64encode(geometry.wkb)
        ]
    
    return ''.join(line)

def hadoop_line_feature(line):
    ''' Convert a correctly-formatted line of text to a GeoJSON feature.
    
        Allows Hadoop to stream features from the mapper to the reducer.
        See also skeletron-hadoop-mapper.py and skeletron-hadoop-reducer.py.
    '''
    id, prop, geom = line.split()
    
    id = json_decode(id)
    properties = dict(unpickle(b64decode(prop)))
    geometry = wkb_decode(b64decode(geom))
    
    return dict(type='Feature', id=id,
                properties=properties,
                geometry=geometry.__geo_interface__)
