from _skeletron import skeleton
try:
    from shapely.ops import linemerge
except ImportError:
    linemerge = None
    

class InteriorSkeleton(object):
    def __init__(self, polygon):
	if hasattr(polygon, "__geo_interface__"):
	    geometry = polygon.__geo_interface__()
	    if geometry["type"] != "Polygon":
		raise TypeError("Geometry object must be of polygon type")
	    edges = geometry["coordinates"]
	elif hasattr(polygon, "__iter__"):
	    edges = polygon
	else:
	    raise TypeError("Geometry must be iterable or provide a __geo_interface__ method")
	self.edges, self.inner, self.outer = [], [], []
	for start, end, edge_type in _skeletron.skeleton(edges):
	    (self.edges, self.inner, self.outer)[edge_type].append((start, end))
	
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
