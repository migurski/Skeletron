from sys import exc_info
from urlparse import parse_qs

from shapely.geos import ReadingError
from shapely.wkt import dumps as wkt_dumps, loads as wkt_loads
from shapely.wkb import dumps as wkb_dumps, loads as wkb_loads

from Skeletron import polygon_spine

def app(environ, start_response):
    """
    """
    if environ['PATH_INFO'] == '/':
        start_response('200 OK', {})
        return form()

    elif environ['PATH_INFO'] == '/spine':
        try:
            query = parse_qs(environ['wsgi.input'].read())
            
            if 'polygon' not in query:
                raise Exception('Missing required "polygon"')

            try:
                polygon = wkb_loads(query['polygon'][0])
            except ReadingError:
                try:
                    polygon = wkt_loads(query['polygon'][0])
                except ReadingError:
                    raise Exception("Couldn't parse the polygon after trying wkt and wkb")

            threshold = int(query.get('threshold', ['0'])[0])
            format = query.get('format', ['wkt'])[0]

            spine = polygon_spine(polygon, threshold)
            
            if format == 'wkt':
                content_type = 'text/plain'
                response = wkt_dumps(spine)

            elif format == 'wkb':
                content_type = 'application/octet-stream'
                response = wkb_dumps(spine)
            
            else:
                raise Exception('wah?')
    
        except Exception, e:
            start_response('400 WTF', {}, exc_info())
            return repr(e)
        
        else:
            headers = [('Content-Type', content_type), ('Content-Length', len(response))]
            start_response('200 OK', headers)
            return response

    else:
        start_response('200 OK', {})
        return 'Hello world.\n'

def form():
    """
    """
    return """<!DOCTYPE html>
<html lang="en">
<head>
	<meta http-equiv="content-type" content="text/html; charset=utf-8">
	<title>Skeletron</title>
</head>
<body>

    <p>
        Find me <a href="https://github.com/migurski/Skeletron">on Github</a>.
    </p>

    <form action="/spine" method="POST">
        <label>
            <input checked type="radio" name="polygon" value="POLYGON ((180.7106781186547551 190.0000000000000000, 250.0000000000000000 190.0000000000000000, 278.2842712474619020 178.2842712474618736, 290.0000000000000000 150.0000000000000000, 278.2842712474619020 121.7157287525381264, 250.0000000000000000 110.0000000000000000, 174.1421356237309794 110.0000000000000000, 161.2132034355963981 104.6446609406725941, 78.2842712474619020 21.7157287525381015, 49.9999999999999787 10.0000000000000000, 21.7157287525381015 21.7157287525380980, 10.0000000000000000 49.9999999999999574, 21.7157287525381015 78.2842712474619020, 86.3603896932107205 142.9289321881345245, 24.6446609406726225 204.6446609406726225, 10.0000000000000000 240.0000000000000568, 24.6446609406726296 275.3553390593273775, 59.9999999999999574 290.0000000000000000, 95.3553390593273775 275.3553390593273775, 180.7106781186547551 190.0000000000000000))">
            Y-shape
        </label>
        
        <select name="threshold">
            <option label="70" selected value="70"></option>
            <option label="0" value="0"></option>
        </select>
        
        <select name="format">
            <option label="well-known text" selected value="wkt"></option>
            <option label="well-known binary" value="wkb"></option>
        </select>
        
        <input type="submit">
    </form>

</body>
</html>
"""
