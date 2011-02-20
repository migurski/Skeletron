from math import hypot, atan2, sin, cos
from itertools import combinations
    
from shapely.geometry import LineString

import _skeletron

BORDER = 0
OUTER = 1
INNER = 2

def xray(polygon):
    """
    """
    if hasattr(polygon, "__geo_interface__"):
        geometry = polygon.__geo_interface__
        edges = list(geometry["coordinates"])

        if geometry["type"] != "Polygon":
            raise TypeError('Geometry object must be of polygon type, not "%s"' % geometry["type"])

    elif hasattr(polygon, "__iter__"):
        edges = list(polygon)

    else:
        raise TypeError("Geometry must be iterable or provide a __geo_interface__ method")

    #
    # Fix coordinate winding.
    #
    for (i, coords) in enumerate(edges):
        winding = _coord_winding(coords)
        
        if i == 0 and winding != 'exterior' or i >= 1 and winding != 'interior':
            edges[i] = [coord for coord in reversed(coords)]
    
    #
    # Calculate the straight skeleton.
    #
    edges = _skeletron.skeleton(edges)
    inner, outer, border = [], [], []
    
    for start, end, edge_type in edges:
        if edge_type == INNER:
            inner.append(LineString((start, end)))
        elif edge_type == OUTER:
            outer.append(LineString((start, end)))
        elif edge_type == BORDER:
            border.append(LineString((start, end)))
    
    #
    # Postprocess and return.
    #
    inner = _merge_lines(inner)
    return inner, outer, border

def _turn(x1, y1, x2, y2, x3, y3):
    """ Calculate theta from segment (1-2) to segment (2-3), return radians.
    """
    theta = atan2(y2 - y1, x2 - x1)
    c, s = cos(-theta), sin(-theta)
    
    x = c * (x3 - x2) - s * (y3 - y2)
    y = s * (x3 - x2) + c * (y3 - y2)
    
    theta = atan2(y, x)
    
    return theta

def _coord_winding(coords):
    """ Return 'interior' or 'exterior' depending on the winding of the coordinate list.
    """
    count = len(coords) - 1
    turns = 0
    
    for i in range(count):
        x1, y1 = coords[i]
        x2, y2 = coords[(i + 1) % count]
        x3, y3 = coords[(i + 2) % count]
        
        turns += _turn(x1, y1, x2, y2, x3, y3)
    
    return (turns > 0) and 'exterior' or 'interior'

def _stitch_lines(line1, line2):
    """ Stitch together two line strings if possible, return new line or false.
    """
    coords1 = list(line1.coords)
    coords2 = list(line2.coords)
    intersect = line1.intersection(line2)
    
    #
    # Skeleton seems to often include numerous repeated lines.
    #
    if intersect.type == 'LineString' and intersect.length == line1.length:
        return LineString(coords1[:])
    
    #
    # Check whether the ends match, in any combination.
    #
    if coords1[0] == coords2[0]:
        return LineString(list(reversed(coords1)) + coords2[1:])

    elif coords1[0] == coords2[-1]:
        return LineString(coords2 + coords1[1:])

    elif coords1[-1] == coords2[0]:
        return LineString(coords1 + coords2[1:])

    elif coords1[-1] == coords2[-1]:
        return LineString(coords1 + list(reversed(coords2))[1:])
    
    #
    # Unstitchable.
    #
    return False

def _merge_lines(lines):
    """ Reduce a collection of lines to the minimum number of stitched lines.
    """
    lines = [line for line in lines if line.length]
    merge = True
    
    while merge:
        old_len = len(lines)
        touched = set()
        
        for (line1, line2) in combinations(lines[:], 2):
            if line1 in touched or line2 in touched:
                continue
            
            merged = _stitch_lines(line1, line2)
            
            if merged:
                lines.append(merged)
                lines.remove(line1)
                lines.remove(line2)
                touched.add(line1)
                touched.add(line2)
        
        merge = len(lines) < old_len
    
    return lines

class InteriorSkeleton(object):
    """
    >>> shape = (((-1.0,-1.0), (0.0,-12.0), (1.0,-1.0), (12.0,0.0), \
                  (1.0,1.0), (0.0,12.0), (-1.0,1.0), (-12.0,0.0)),)
    >>> skel = InteriorSkeleton(shape)
    >>> len(skel.outer_bisectors)
    16
    >>> len(skel.inner_bisectors)
    2
    >>> len(skel.bisectors)
    18
    >>> len(skel.boundary) == len(shape[0]) * 2
    True
    >>> lines = skel.lines()
    >>> type(lines) 
    <class 'shapely.geometry.linestring.LineString'>
    """

    def __init__(self, polygon):
        if hasattr(polygon, "__geo_interface__"):
            geometry = polygon.__geo_interface__
            if geometry["type"] != "Polygon":
                raise TypeError("Geometry object must be of polygon type")
            edges = geometry["coordinates"]
        elif hasattr(polygon, "__iter__"):
            edges = polygon
        else:
            raise TypeError("Geometry must be iterable or provide a __geo_interface__ method")
        self.edges, self.inner, self.outer = [], [], []
        for start, end, edge_type in _skeletron.skeleton(edges):
            (self.edges, self.outer, self.inner)[edge_type].append((start, end))
        
    @property
    def bisectors(self):
        return self.inner + self.outer

    @property
    def inner_bisectors(self):
        return self.inner

    @property
    def outer_bisectors(self):
        return self.outer

    @property
    def boundary(self):
        return self.edges

    def lines(self):
        if linemerge is None:
            raise ImportError("linestrings() method requires Shapely support")
        return linemerge(self.inner_bisectors)

if __name__ == "__main__":
    import doctest
    doctest.testmod()
