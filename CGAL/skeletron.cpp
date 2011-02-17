#include <Python.h>

#include<boost/shared_ptr.hpp>

#include<CGAL/Exact_predicates_inexact_constructions_kernel.h>
#include<CGAL/Polygon_with_holes_2.h>
#include<CGAL/create_straight_skeleton_from_polygon_with_holes_2.h>

typedef CGAL::Exact_predicates_inexact_constructions_kernel K ;
typedef K::Point_2                   Point ;
typedef CGAL::Polygon_2<K>           Polygon ;
typedef CGAL::Polygon_with_holes_2<K> Polygon_with_holes;
typedef CGAL::Straight_skeleton_2<K> Ss ;
typedef Ss::Halfedge_const_iterator Halfedge_const_iterator ;

typedef boost::shared_ptr<Ss> SsPtr ;

static Polygon *get_polygon(PyObject *coords) {
    PyObject *iterator = PyObject_GetIter(coords);
    PyObject *coord;
    Polygon *poly = new Polygon();
    while ((coord = PyIter_Next(iterator))) {
	PyObject *x = PySequence_GetItem(coord, 0),
	         *y = PySequence_GetItem(coord, 1);
	poly->push_back(Point(PyFloat_AsDouble(x), PyFloat_AsDouble(y)));
	Py_DECREF(coord);
	Py_DECREF(x);
	Py_DECREF(y);
    }
    Py_DECREF(iterator);
    return poly;
}

static PyObject *skeleton(PyObject *self, PyObject *args) {
    PyObject *obj;
    if(!PyArg_ParseTuple(args, "O", &obj)) {
        /* fail unless I got an object */
        return NULL;
    }

    PyObject *iterator = PyObject_GetIter(obj);
    PyObject *coords;

    if (iterator == NULL) {
	/* propagate error */
	return NULL;
    }

    Polygon *ring = NULL;
    Polygon_with_holes *poly = NULL;

    while ((coords = PyIter_Next(iterator))) {
	ring = get_polygon(coords);
	if (poly == NULL) {
	    poly = new Polygon_with_holes(*ring);
	} else {
	    poly->add_hole(*ring);
	}
	delete ring;
	Py_DECREF(coords);
    }

    Py_DECREF(iterator);

    if (PyErr_Occurred()) {
	return NULL;
    }

    SsPtr ss = CGAL::create_interior_straight_skeleton_2(*poly);
    PyObject *edges = PyList_New(0);
    for ( Halfedge_const_iterator i = ss->halfedges_begin(); i != ss->halfedges_end(); ++i ) {
	PyObject *start = PyList_New(2),
		 *end = PyList_New(2);
	Point v1 = i->opposite()->vertex()->point(),
	      v2 = i->vertex()->point();
	long typecode = (i->is_inner_bisector() ? 2 : (i->is_bisector() ? 1 : 0));
	PyList_SetItem(start, 0, PyFloat_FromDouble(v1.x()));
	PyList_SetItem(start, 1, PyFloat_FromDouble(v1.y()));
	PyList_SetItem(end, 0, PyFloat_FromDouble(v2.x()));
	PyList_SetItem(end, 1, PyFloat_FromDouble(v2.y()));
	PyObject *line = PyList_New(3);
	PyList_SetItem(line, 0, start);
	PyList_SetItem(line, 1, end);
	PyList_SetItem(line, 2, PyInt_FromLong(typecode));
	PyList_Append(edges, line);
    }
    delete poly;
    return edges;
}

/* map between python function name and C function pointer */
static PyMethodDef SkeletronMethods[] = {
    {"skeleton", skeleton, METH_VARARGS, "Dump a skeleton."},
    {NULL, NULL, 0, NULL}
};

/* bootstrap function, called automatically when you 'import _blobs' */
PyMODINIT_FUNC init_skeletron(void) {
    (void)Py_InitModule("_skeletron", SkeletronMethods);
}
