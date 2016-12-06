#!/usr/bin/python2
from __future__ import division, absolute_import, print_function, \
    unicode_literals

import numpy as num
import pyqtgraph as pg
import pyqtgraph.parametertree.parameterTypes as pTypes
from pyqtgraph import dockarea
from .utils_qt import _viridis_data

__all__ = ['QKiteView', 'QKitePlot', 'QKiteToolColormap',
           'QKiteParameterGroup']


class QKiteView(dockarea.DockArea):
    def __init__(self):
        dockarea.DockArea.__init__(self)
        self.tool_docks = []

        dock_main =\
            dockarea.Dock(self.title,
                          autoOrientation=False,
                          widget=self.main_widget)
        dock_colormap =\
            dockarea.Dock('Colormap',
                          autoOrientation=False,
                          widget=QKiteToolColormap(self.main_widget))
        dock_colormap.setStretch(1, None)

        for i, (name, tool) in enumerate(self.tools.iteritems()):
            self.tool_docks.append(
                dockarea.Dock(name,
                              widget=tool,
                              size=(2, 2),
                              autoOrientation=False))
            self.addDock(self.tool_docks[-1], position='bottom')

        self.addDock(dock_main, position='left')
        self.addDock(dock_colormap, position='right')


class QKitePlot(pg.PlotWidget):
    def __init__(self, container):
        pg.PlotWidget.__init__(self)
        self.container = container

        self.image = pg.ImageItem(None)

        self.setAspectLocked(True)
        self.plotItem.getAxis('left').setZValue(100)
        self.plotItem.getAxis('bottom').setZValue(100)
        self.setLabels(bottom={'East', 'm'},
                       left={'North', 'm'},)

        self.hint_text = pg.LabelItem(text='',
                                      justify='right', size='8pt',
                                      parent=self.plotItem)
        self.hint_text.anchor(itemPos=(1., 0.), parentPos=(1., 0.))
        self.hint_text.template =\
            '<span style="font-family: monospace; color: #fff">' \
            'East {east:08.2f} m | North {north:08.2f} m | '\
            '{measure} {z:{spaces}.1f}</span>'

        self.addItem(self.image)
        self.update()

        self.transformToUTM()
        self._move_sig = pg.SignalProxy(self.image.scene().sigMouseMoved,
                                        rateLimit=30, slot=self.mouseMoved)
        # self.addIsocurve()
        # self.scalebar()

    def transformToUTM(self):
        ll_x, ll_y, ur_x, ur_y, dx, dy = \
            (self.container.frame.llE, self.container.frame.llN,
             self.container.frame.urE, self.container.frame.urN,
             self.container.frame.dE, self.container.frame.dN)

        self.image.translate(ll_x, ll_y)
        self.image.scale(dx, dy)
        ur_x, ur_y
        # padding = 100
        # self.setLimits(xMin=ll_x-dx*padding,
        #                xMax=ur_x+dx*padding,
        #                yMin=ll_y-dy*padding,
        #                yMax=ur_y+dy*padding)

    def scalebar(self):
        ''' Not working '''
        self.scale_bar = pg.ScaleBar(10, width=5, suffix='m')
        self.scale_bar.setParentItem(self.plotItem)
        self.scale_bar.anchor((1, 1), (1, 1), offset=(-20, -20))

    @property
    def component(self):
        return self._component

    @component.setter
    def component(self, component):
        if component not in self.components_available.keys():
            raise AttributeError('Invalid component %s' % component)
        self._component = component
        self.update()

    @property
    def data(self):
        _data = self.components_available[self.component][1](self.container)
        return _data  # num.nan_to_num(_data)

    def update(self):
        self.image.updateImage(self.data.T, autoDownsample=True)
        self.mouseMoved()
        # self.addIsocurves()

    def addIsocurve(self, level=0.):
        iso = pg.IsocurveItem(level=level, pen='g')
        iso.setZValue(1000)
        iso.setData(pg.gaussianFilter(self.data, (5, 5)))
        iso.setParentItem(self.image)

        self.iso = iso

    def mouseMoved(self, event=None):
        if event is None:
            self.hint_text.setText('East %d m | North %d m | %s %.3f'
                                   % (0, 0, self.component.title(), 0))
            return
        pos = event[0]
        if self.image.sceneBoundingRect().contains(pos):
            map_pos = self.plotItem.vb.mapSceneToView(pos)
            if map_pos.isNull():
                return
            img_pos = self.image.mapFromScene(event).data
            z = self.image.image[int(img_pos().x()),
                                 int(img_pos().y())]

            self.hint_text.setText(
                self.hint_text.template.format(
                    north=map_pos.x(), east=map_pos.y(),
                    measure=self.component.title(),
                    z=z, spaces='03' if not num.isnan(z) else '03'))
            return


class QKiteToolColormap(pg.HistogramLUTWidget):
    def __init__(self, plot):
        pg.HistogramLUTWidget.__init__(self, image=plot.image)

        self._plot = plot

        _zero_marker = pg.InfiniteLine(pos=0, angle=0, pen='w', movable=False)
        _zero_marker.setValue(0.)
        _zero_marker.setZValue(1000)
        self.vb.addItem(_zero_marker)

        self.axis.setLabel('Displacement / m')
        # self.plot.rotate(-90)
        # self.layout.rotate(90)
        # self.gradient.setOrientation('bottom')
        self.setSymColormap()
        self._plot.image.sigImageChanged.connect(self.imageChanged)
        # self.isoCurveControl()

    def imageChanged(self):
        if self._plot.component == 'weight':
            self.setQualitativeColormap()
        else:
            self.setSymColormap()

    def setSymColormap(self):
        cmap = {'ticks':
                [[0., (0, 0, 0, 255)],
                 [1e-3, (106, 0, 31, 255)],
                 [.5, (255, 255, 255, 255)],
                 [1., (8, 54, 104, 255)]],
                'mode': 'rgb'}
        cmap = {'ticks':
                [[0., (0, 0, 0)],
                 [1e-3, (172, 56, 56)],
                 [.5, (255, 255, 255)],
                 [1., (51, 53, 120)]],
                'mode': 'rgb'}
        lvl_min = num.nanmin(self._plot.data)
        lvl_max = num.nanmax(self._plot.data)
        abs_range = max(abs(lvl_min), abs(lvl_max))

        self.gradient.restoreState(cmap)
        self.setLevels(-abs_range, abs_range)

    def setQualitativeColormap(self):
        l = len(_viridis_data) - 1
        cmap = {'mode': 'rgb'}
        cmap['ticks'] = [[float(i)/l, c] for i, c in enumerate(_viridis_data)]
        self.gradient.restoreState(cmap)
        self.setLevels(num.nanmin(self._plot.data),
                       num.nanmax(self._plot.data))

    def isoCurveControl(self):
        iso_ctrl = pg.InfiniteLine(pos=0, angle=0, pen='g', movable=True)
        iso_ctrl.setValue(0.)
        iso_ctrl.setZValue(1000)

        def isolineChange():
            self._plot.iso.setLevel(iso_ctrl.value())

        iso_ctrl.sigDragged.connect(isolineChange)
        self.vb.addItem(iso_ctrl)


class QKiteParameterGroup(pTypes.GroupParameter):
    def __init__(self, model, **kwargs):
        self.model = model
        if isinstance(self.parameters, list):
            self.parameters = dict.fromkeys(self.parameters)

        pTypes.GroupParameter.__init__(self, **kwargs)
        self.updateValues()

    def updateValues(self):
        if not hasattr(self, 'parameters'):
            return

        for param, f in self.parameters.iteritems():
            try:
                if callable(f):
                    value = f(self.model)
                else:
                    value = getattr(self.model, param)
            except AttributeError:
                value = 'n/a'
            try:
                self.child(param).setValue(value)
            except Exception:
                self.addChild({'name': param,
                               'value': value,
                               'type': 'str',
                               'readonly': True})

    def pushChild(self, child, **kwargs):
        self.insertChild(0, child, **kwargs)