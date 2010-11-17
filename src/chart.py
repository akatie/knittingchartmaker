
import sys
from xml.dom import minidom

import gtk
import gtk.gdk
import gobject
import libxml2
import libxslt

import stitch
import yarn


class Chart:
    def __init__(self, w=10, h=10, y=None):
        self.w = w
        self.h = h
        
        self.yarn = y
        if y is None:
            self.yarn = yarn.Yarn("Background Colour")
        self.yarns = { self.yarn.label: self.yarn }
        self.defaultYarn = self.yarn
        
        self.stitch = stitch.knit(self.yarn)
        self.defaultStitch = self.stitch
        
        self.setup()
    
    def setup(self):
        self.grid = []
        for i in range(self.h):
            row = []
            for j in range(self.w):
                row.append(stitch.knit(self.yarn))
            self.grid.append(row)
    
    def clear(self):
        for i in range(self.h):
            for j in range(self.w):
                self.grid[i][j] = stitch.knit(self.yarn)
    
    def setYarn(self, x, y, yn):
        yn = self.addYarn(yn)
        self.grid[y][x].setYarn(yn)
        
    def getYarn(self, x, y):
        return self.grid[y][x].getYarn()
        
    def setStitch(self, x, y, st):
        self.grid[y][x] = st.copy()
        
    def getStitch(self, x, y):
        return self.grid[y][x]
        
    def addYarn(self, yarn=None, label=None, switch=False):
        # add any new yarn
        if yarn is not None and not self.yarns.has_key(yarn.label):
            self.yarns[yarn.label] = yarn
        
        # set current yarn
        if switch:
            if label is not None and self.yarns.has_key(label):
                self.yarn = self.yarns[label]
            if yarn is not None and self.yarns.has_key(yarn.label):
                self.yarn = self.yarns[yarn.label]
            
        # return yarn
        if yarn is not None:
            return self.yarns[yarn.label]
        if label is not None:
            return self.yarns[label]
        
    def toKnitML(self):
        knitml = minidom.Document()
        
        pattern = knitml.createElement("pattern")
        pattern.setAttribute("xmlns", "http://www.knitml.com/schema/pattern")
        knitml.appendChild(pattern)
        
        supplies = knitml.createElement("supplies")
        pattern.appendChild(supplies)
        
        yarns = knitml.createElement("yarns")
        supplies.appendChild(yarns)
        for y in self.yarns.values():
            yarn = knitml.createElement("yarn")
            yarn.setAttribute("id", y.label)
            col = knitml.createElement("color")
            col.setAttribute("name", y.col)
            yarn.appendChild(col)
            yarns.appendChild(yarn)
        
        directions = knitml.createElement("directions")
        directions.setAttribute("width", str(self.w))
        directions.setAttribute("height", str(self.h))
        pattern.appendChild(directions)
        
        group = knitml.createElement("instruction-group")
        group.setAttribute("id", "cm")
        directions.appendChild(group)
        
        section = knitml.createElement("section")
        group.appendChild(section)
        
        for r in self.grid:
            row = knitml.createElement("row")
            for st in r:
                stitch = knitml.createElement(st.name)
                stitch.setAttribute("yarn-ref", st.yarn.label)
                stitch.appendChild(knitml.createTextNode("1"))
                row.appendChild(stitch)
            section.appendChild(row)
        
        return knitml
    
    def fromKnitML(self, filename):
        knitml = minidom.parse(filename)
        
        # grab all yarns
        yarns = knitml.getElementsByTagName("yarn")
        self.yarns = {}
        for yn in yarns:
            y = yarn.Yarn(yn.getAttribute("id"), yn.getElementsByTagName("color")[0].getAttribute("name"))
            self.yarns[y.label] = y
        
        # set size and setup grid
        directions = knitml.getElementsByTagName("directions")[0]
        self.w = int(directions.getAttribute("width"))
        self.h = int(directions.getAttribute("height"))
        self.setup()
        
        # set all stitches
        rows = knitml.getElementsByTagName("row")
        for y, r in enumerate(rows):
            x = 0
            for st in r.childNodes:
                if st.nodeType != st.TEXT_NODE:
                    self.setYarn(x, y, self.yarns[st.getAttribute("yarn-ref")])
                    self.setStitch(x, y, stitch.createStitch(st.tagName, self.yarns[st.getAttribute("yarn-ref")]))
                    x += 1
        
    def toSVG(self, filename, knitmlfile, numbers="", sqw=40, sqh=40, grid=True):
        sd = libxml2.parseFile("misc/knitml2svg.xsl")
        s = libxslt.parseStylesheetDoc(sd)
        d = libxml2.parseFile(knitmlfile)
        r = s.applyStylesheet(d, {"sqw":"'" + str(sqw) + "'", "sqh":"'" + str(sqh) + "'", "grid":"'" + str(int(grid)) + "'", "numbers":"'%s'" % numbers})
        s.saveResultToFilename(filename, r, 0)
        s.freeStylesheet()
        d.freeDoc()
        r.freeDoc()

        
    # pos 0 top-left
    #     1 top-right
    #     2 bottom-right
    #     3 bottom-right
    def resize(self, w, h, pos):
        if 0 <= pos and pos <= 3 and (w != self.w or h != self.h):
            # copy old grid
            w_old = self.w
            h_old = self.h
            grid = []
            for i in range(h_old):
                row = []
                for j in range(w_old):
                    row.append(self.grid[i][j])
                grid.append(row)
            
            self.w = w
            self.h = h
            self.setup()
    
            if pos == 0:
                i = 0
                while i < h_old and i < self.h:
                    j = 0
                    while j < w_old and j < self.w:
                        self.grid[i][j] = grid[i][j]
                        j += 1
                    i += 1
            elif pos == 1:
                i = 0
                while i < h_old and i < self.h:
                    j = w_old - 1
                    k = self.w - 1
                    while j >= 0 and k >= 0:
                        self.grid[i][k] = grid[i][j]
                        j -= 1
                        k -= 1
                    i += 1
            elif pos == 2:
                i = h_old - 1
                h = self.h - 1
                while i >= 0 and h >= 0:
                    j = w_old - 1
                    k = self.w - 1
                    while j >= 0 and k >= 0:
                        self.grid[h][k] = grid[i][j]
                        j -= 1
                        k -= 1
                    i -= 1
                    h -= 1
            elif pos == 3:
                i = h_old - 1
                h = self.h - 1
                while i >= 0 and h >= 0:
                    j = 0
                    while j < w_old and j < self.w:
                        self.grid[h][j] = grid[i][j]
                        j += 1
                    i -= 1
                    h -= 1
    
    def __str__(self):
        s = ""
        for r in self.grid:
            for st in r:
                s += "%s\t" % st
            s += "\n"
        return s

class DrawableChart(Chart, gobject.GObject):
    def __init__(self, w=10, h=10, y=None, readOnly=False):
        gobject.GObject.__init__(self)
        Chart.__init__(self, w, h, y)
        self.stw = 20
        self.sth = 20
        
        self.tw = w * (self.stw + 1)
        self.th = h * (self.sth + 1)
        
        self.da = gtk.DrawingArea()
        self.da.set_size_request(self.tw, self.th)
        
        self.read_only = readOnly
        
        # Signals used to handle backing pixmap
        self.pixmap = None
        self.da.connect("expose_event", self.expose_event)
        self.da.connect("configure_event", self.configure_event)
        if not self.read_only:
            self.da.connect("button_press_event", self.button_press_event)
        self.da.set_events(gtk.gdk.EXPOSURE_MASK | gtk.gdk.BUTTON_PRESS_MASK)
        
        # dirty flag to keep track of changes
        self.dirty = False
        
        # select vars to allow selection of multiple cells
        self.selectionRange = [self.w + 1, self.h + 1, -1, -1]
        
        # setup colours list
        self.colours = {
            "grid": None
        }
    
    # adjust the colour of the grid lines
    def setGridColour(self, colour=None):
        if colour:
            gtkcol = gtk.gdk.color_parse(colour)
            if gtkcol:
                self.colours["grid"] = gtkcol
        else:
            self.colours["grid"] = self.da.get_style().black_gc
    
    # get the colour of the grid lines
    def getGridColour(self):
        return self.colours["grid"]
    
    # configure the drawing area, i.e. set up a backing pixmap
    def configure_event(self, widget, event):
        self.refresh()
        return True
    
    # redraw the screen from the backing pixmap
    def expose_event(self, widget, event):
        self.refresh()
        return False
        
    def button_press_event(self, widget, event):
        # get cell position
        x, y = int(event.x / (self.stw + 1)), int(event.y / (self.sth + 1))
        
        if x < 0 or self.w < x or y < 0 or self.h < y:
            return
        
        # CTRL+click: individual addition/subtraction to selection
        if event.state & gtk.gdk.CONTROL_MASK and not(event.state & gtk.gdk.SHIFT_MASK):
            stitch = self.getStitch(x, y)
            stitch.selected = not stitch.selected
        
        # SHIFT+click: multiple addition/subtraction to selection
        elif event.state & gtk.gdk.SHIFT_MASK and not(event.state & gtk.gdk.CONTROL_MASK):
            # extend selection range
            if x < self.selectionRange[0]:    self.selectionRange[0] = x
            if y < self.selectionRange[1]:    self.selectionRange[1] = y
            if x > self.selectionRange[2]:    self.selectionRange[2] = x
            if y > self.selectionRange[3]:    self.selectionRange[3] = y
            
            # make sure everything in range is selected
            for i in range(self.selectionRange[0], self.selectionRange[2] + 1):
                for j in range(self.selectionRange[1], self.selectionRange[3] + 1):
                    self.getStitch(i, j).selected = True
        
        # set stitches and yarns on selection
        else:
            stitch = self.getStitch(x, y)
            
            # if stitch in selection, set all
            if stitch.selected:
                for stitch_info in self.selectedStitches():
                    if event.button == 1:
                        self.setStitch(stitch_info["x"], stitch_info["y"], self.stitch)
                        self.setYarn(stitch_info["x"], stitch_info["y"], self.yarn)
                    elif event.button == 3:
                        self.setStitch(stitch_info["x"], stitch_info["y"], self.defaultStitch)
                        self.setYarn(stitch_info["x"], stitch_info["y"], self.defaultYarn)
            
            # otherwise, set chosen cell
            else:
                if event.button == 1:
                    self.setStitch(x, y, self.stitch)
                    self.setYarn(x, y, self.yarn)
                elif event.button == 3:
                    self.setStitch(x, y, self.defaultStitch)
                    self.setYarn(x, y, self.defaultYarn)
                
                # clear selection
                self.deselectAll()
                self.selectionRange = [self.w + 1, self.h + 1, -1, -1]
        
        # redraw the char
        self.refresh()
        
        return True
        
    def refresh(self):
        # make sure we have a grid colour
        grid_col = self.getGridColour()
        if not grid_col:
            self.setGridColour()
            grid_col = self.getGridColour()
            
        # reset size
        self.da.set_size_request(self.tw, self.th)
        
        # draw stitches
        for i in range(self.h):
            for j in range(self.w):
                st = self.getStitch(j, i)
                st.render_to_drawable(self.da.window, self.da.get_style().black_gc, j * (self.stw + 1) + 1, i * (self.sth + 1) + 1, self.stw, self.sth)
        
        # add vertical lines
        for i in range(0, self.tw, self.stw + 1):
            self.da.window.draw_line(grid_col, i, 0, i, self.th)
        
        # add horizontal lines
        for i in range(0, self.th, self.sth + 1):
            self.da.window.draw_line(grid_col, 0, i, self.tw, i)
        
        # draw a border
        self.da.window.draw_rectangle(grid_col, False, 0, 0, self.tw, self.th)
        
        # redraw the whole thing
        self.da.queue_draw()
        
    def drawing_area(self):
        return self.da
    
    def setStitchSize(self, w, h=None):
        if h is None:
            h = w 
        self.stw = w
        self.sth = h
        
        # adjust size
        self.tw = self.w * (self.stw + 1)
        self.th = self.h * (self.sth + 1)
        
    def resize(self, w, h, pos):
        Chart.resize(self, w, h, pos)
        
        # adjust size
        self.tw = self.w * (self.stw + 1)
        self.th = self.h * (self.sth + 1)
    
    def selectAll(self):
        for r in self.grid:
            for st in r:
                st.selected = True
    
    def deselectAll(self):
        for r in self.grid:
            for st in r:
                st.selected = False
                
    def selectedStitches(self):
        stitches = []
        for x, r in enumerate(self.grid):
            for y, st in enumerate(r):
                if st.selected:
                    stitches.append({"stitch": st, "x": y, "y": x})
        return stitches
    
    def setYarn(self, x, y, yn):
        Chart.setYarn(self, x, y, yn)
        self.dirty = True
        self.emit("chart_changed")
        
    def setStitch(self, x, y, st):
        Chart.setStitch(self, x, y, st)
        self.dirty = True
        self.emit("chart_changed")
        
# setup some new signals for tracking chart changes
gobject.type_register(DrawableChart)
gobject.signal_new("chart_changed", DrawableChart, gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ())


if __name__ == "__main__":
    c = DrawableChart(10, 10)
    
    w = gtk.Window()
    w.set_name("Chart")
    w.connect("destroy", lambda w: gtk.main_quit())
    
    vbox = gtk.VBox(False, 0)
    w.add(vbox)
    vbox.add(c.drawing_area())
    
    w.show_all()
    
    c.addYarn(yarn.Yarn("Yarn 1", "#FF00FF"), switch=True)
    c.refresh()
    
    gtk.main()