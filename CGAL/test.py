import skeletron

from cairo import Context, ImageSurface, FORMAT_RGB24
from shapely.wkt import dumps as wkt_dumps, loads as wkt_loads
from shapely.geometry import asPolygon

poly = wkt_loads('POLYGON ((-13625496.4396574757993221 4548638.8825872316956520, -13625496.4395814724266529 4548638.8825104515999556, -13625472.9695814736187458 4548615.1725104516372085, -13625468.6301940716803074 4548604.5436974689364433, -13625473.0774895492941141 4548593.9595814729109406, -13625483.7063025329262018 4548589.6201940709725022, -13625494.2904185280203819 4548594.0674895485863090, -13625517.7603750806301832 4548617.7774456581100821, -13625546.1603425238281488 4548646.4674127679318190, -13625550.4998064786195755 4548657.0961944973096251, -13625546.0525872316211462 4548667.6803425233811140, -13625535.4238055031746626 4548672.0198064781725407, -13625524.8396574761718512 4548667.5725872311741114, -13625496.4396574757993221 4548638.8825872316956520))')
inner, outer, border = skeletron.xray(poly)

xmin, ymin, xmax, ymax = poly.bounds
scale = 480. / max(xmax - xmin, ymax - ymin)

img = ImageSurface(FORMAT_RGB24, 512, 512)
ctx = Context(img)

ctx.move_to(0, 0)
ctx.line_to(512, 0)
ctx.line_to(512, 512)
ctx.line_to(0, 512)
ctx.line_to(0, 0)

ctx.set_source_rgb(0xff, 0xff, 0xff)
ctx.fill()

ctx.translate(16, 16)
ctx.scale(scale, scale)
ctx.translate(-xmin, -ymin)
ctx.set_line_width(2/scale)

def draw_lines(lines, rgb):
    """
    """
    for line in lines:
        coords = iter(line.coords)
        ctx.move_to(*coords.next())
        
        for coord in coords:
            ctx.line_to(*coord)
    
        ctx.set_source_rgb(*rgb)
        ctx.stroke()

draw_lines(border, (.9, .9, .9))
draw_lines(outer, (.8, .8, .8))
draw_lines(inner, (0, 0, 0))

img.write_to_png('out.png')
