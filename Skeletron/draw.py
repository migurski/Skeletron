from math import pi

from cairo import Context, ImageSurface, FORMAT_RGB24, LINE_CAP_ROUND

class Canvas:

    def __init__(self, width, height):
        self.xform = lambda x, y: (x, y)
    
        self.img = ImageSurface(FORMAT_RGB24, width, height)
        self.ctx = Context(self.img)
        
        self.ctx.move_to(0, 0)
        self.ctx.line_to(width, 0)
        self.ctx.line_to(width, height)
        self.ctx.line_to(0, height)
        self.ctx.line_to(0, 0)
        
        self.ctx.set_source_rgb(1, 1, 1)
        self.ctx.fill()
        
        self.width = width
        self.height = height
    
    def fit(self, left, top, right, bottom):
        xoff = left
        yoff = top
        
        xscale = self.width / float(right - left)
        yscale = self.height / float(bottom - top)
        
        if abs(xscale) > abs(yscale):
            xscale *= abs(yscale) / abs(xscale)
        
        elif abs(xscale) < abs(yscale):
            yscale *= abs(xscale) / abs(yscale)

        self.xform = lambda x, y: ((x - xoff) * xscale, (y - yoff) * yscale)
    
    def dot(self, x, y, size=4, fill=(.5, .5, .5)):
        x, y = self.xform(x, y)

        self.ctx.arc(x, y, size/2., 0, 2*pi)
        self.ctx.set_source_rgb(*fill)
        self.ctx.fill()
    
    def line(self, points, stroke=(.5, .5, .5), width=1):
        self.ctx.move_to(*self.xform(*points[0]))
        
        for (x, y) in points[1:]:
            self.ctx.line_to(*self.xform(x, y))
        
        self.ctx.set_source_rgb(*stroke)
        self.ctx.set_line_cap(LINE_CAP_ROUND)
        self.ctx.set_line_width(width)
        self.ctx.stroke()
    
    def save(self, filename):
        self.img.write_to_png(filename)
