import _skeletron

from shapely.geometry import LineString

try:
    # shapely.ops.linemerge was introduced in 1.2
    from shapely.ops import linemerge
except ImportError:
    try:
        # you can still get to the underlying GEOSLineMerge in 1.0
        from shapely.geos import lgeos
    except ImportError:
        # throw an ImportError later on
        linemerge = None
    else:
        #
        # define our own, just like in
        # https://github.com/sgillies/shapely/blob/rel-1.2.8/shapely/ops.py
        #
        from shapely.geometry.base import geom_factory
        from shapely.geometry import asMultiLineString
        
        def linemerge(lines): 
            """Merges all connected lines from a source
            
            The source may be a MultiLineString, a sequence of LineString objects,
            or a sequence of objects than can be adapted to LineStrings.  Returns a
            LineString or MultiLineString when lines are not contiguous. 
            """ 
            source = None 
            if hasattr(lines, 'type') and lines.type == 'MultiLineString': 
                source = lines 
            elif hasattr(lines, '__iter__'): 
                try: 
                    source = asMultiLineString([ls.coords for ls in lines]) 
                except AttributeError: 
                    source = asMultiLineString(lines) 
            if source is None: 
                raise ValueError("Cannot linemerge %s" % lines)
            result = lgeos.GEOSLineMerge(source._geom) 
            return geom_factory(result)   

BORDER = 0
OUTER = 1
INNER = 2

def xray(polygon):
    """
    """

    if hasattr(polygon, "__geo_interface__"):
        geometry = polygon.__geo_interface__
        edges = geometry["coordinates"]

        if geometry["type"] != "Polygon":
            raise TypeError('Geometry object must be of polygon type, not "%s"' % geometry["type"])

    elif hasattr(polygon, "__iter__"):
        edges = polygon

    else:
        raise TypeError("Geometry must be iterable or provide a __geo_interface__ method")

    inner, outer, border = [], [], []

    for start, end, edge_type in _skeletron.skeleton(edges):
        if edge_type == INNER:
            list = inner
        elif edge_type == OUTER:
            list = outer
        elif edge_type == BORDER:
            list = border
        
        list.append(LineString((start, end)))
    
    return inner, outer, border

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
