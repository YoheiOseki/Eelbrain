"""
plot.utsnd
==========

plots for multivariate uniform time series

"""

from __future__ import division

import logging
import math

import numpy as np
import matplotlib.pyplot as plt

from .. import data_obj as _dta
from . import _base


__hide__ = ['plt', 'math']


class _plt_im_array(object):
    def __init__(self, ax, ndvar, overlay, dims=('time', 'sensor'),
                 extent=None, interpolation=None, vlims={}, cmaps={},
                 contours={}):
        im_kwa = _base.find_im_args(ndvar, overlay, vlims, cmaps)
        self._contours = _base.find_ct_args(ndvar, overlay, contours)
        self._meas = ndvar.info.get('meas', _base.default_meas)
        self._dims = dims

        data = self._data_from_ndvar(ndvar)
        if im_kwa is not None:
            self.im = ax.imshow(data, origin='lower', aspect='auto',
                                extent=extent, interpolation=interpolation,
                                **im_kwa)
            self._cmap = im_kwa['cmap']
        else:
            self.im = None

        # store attributes
        self.ax = ax
        self.cont = None
        self._data = data
        self._aspect = 'auto'
        self._extent = extent

        # draw flexible part
        self._draw_contours()

    def _data_from_ndvar(self, ndvar):
        data = ndvar.get_data(self._dims)
        if data.ndim > 2:
            assert data.shape[0] == 1
            data = data[0]
        return data

    def _draw_contours(self):
        if self.cont:
            for c in self.cont.collections:
                c.remove()

        if self._contours:
            levels = sorted(self._contours)
            colors = [self._contours[l] for l in levels]
            self.cont = self.ax.contour(self._data, levels=levels,
                                        colors=colors, aspect=self._aspect,
                                        origin='lower', extent=self._extent)
        else:
            self.cont = None

    def add_contour(self, meas, level, color):
        if self._meas == meas:
            self._contours[level] = color
            self._draw_contours()

    def get_kwargs(self):
        "Get the arguments required for plotting the im"
        if self.im:
            vmin, vmax = self.im.get_clim()
            args = dict(cmap=self._cmap, vmin=vmin, vmax=vmax)
        else:
            args = {}
        return args

    def set_cmap(self, cmap, meas=None):
        if (self.im is not None) and (meas is None or meas == self._meas):
            self.im.set_cmap(cmap)
            self._cmap = cmap

    def set_data(self, ndvar):
        data = self._data_from_ndvar(ndvar)
        if self.im is not None:
            self.im.set_data(data)
        self._data = data
        self._draw_contours()

    def set_vlim(self, vmax, meas, vmin):
        if self.im is None:
            return
        elif (meas is not None) and (self._meas != meas):
            return

        if vmax is None:
            _, vmax = self.im.get_clim()

        vmin, vmax = _base.fix_vlim_for_cmap(vmin, vmax, self._cmap)
        self.im.set_clim(vmin, vmax)


class _ax_im_array(object):
    def __init__(self, ax, layers, x='time', xlabel=True, ylabel=True,
                 title=None, tick_spacing=.3, interpolation=None, vlims={},
                 cmaps={}, contours={}):
        """
        plots segment data as im

        define a colorspace by supplying one of those kwargs: ``colorspace`` OR
        ``p`` OR ``vmax``

        """
        self.ax = ax
        self.data = layers
        self.layers = []
        epoch = layers[0]

        xdim = epoch.get_dim(x)
        if epoch.ndim == 2:
            xdim_i = epoch.dimnames.index(x)
            ydim_i = {1:0, 0:1}[xdim_i]
            y = epoch.dimnames[ydim_i]
        else:
            err = ("Need 2 dimensions, got %i" % epoch.ndim)
            raise ValueError(err)

        ydim = epoch.get_dim(y)
        if y == 'sensor':
            ydim = _dta.Var(np.arange(len(ydim)), y)

        # plot
        overlay = False
        extent = (xdim[0], xdim[-1], ydim[0], ydim[-1])
        for l in layers:
            p = _plt_im_array(ax, l, overlay, (y, x), extent, interpolation,
                              vlims, cmaps, contours)
            self.layers.append(p)
            overlay = True

        if xlabel:
            if xlabel is True:
                xlabel = xdim.name
            ax.set_xlabel(xlabel)

        if ylabel:
            if ylabel is True:
                ylabel = ydim.name
            ax.set_ylabel(ylabel)

        # x-ticks
        tickstart = math.ceil(xdim[0] / tick_spacing) * tick_spacing
        tickend = xdim[-1] + tick_spacing / 1e4
        ticklabels = np.arange(tickstart, tickend, tick_spacing)
        ax.xaxis.set_ticks(ticklabels)
        if xdim.name == 'time':
            ax.x_fmt = "t = %.3f s"

        # y-ticks
        if y == 'sensor':  # make sure y-ticklabels are all integers
            locs = ax.yaxis.get_ticklocs()
            if any(locs != locs.round()):
                idx = np.where(locs == locs.round())[0]
                locs = locs[idx]
                labels = map(lambda x: str(int(x)), locs)
                ax.yaxis.set_ticks(locs)
                ax.yaxis.set_ticklabels(labels)

        # title
        if title is None:
            title = _base.str2tex(epoch.name)
        ax.set_title(title)

    def add_contour(self, meas, level, color):
        for l in self.layers:
            l.add_contour(meas, level, color)

    def set_cmap(self, cmap, meas=None):
        """Change the colormap in the array plot

        Parameters
        ----------
        cmap : str | colormap
            New colormap.
        meas : None | str
            Measurement to which to apply the colormap. With None, it is
            applied to all.
        """
        for l in self.layers:
            l.set_cmap(cmap, meas)

    def set_data(self, layers):
        self.data = layers
        for l, p in zip(layers, self.layers):
            p.set_data(l)

    def set_vlim(self, vmax=None, meas=None, vmin=None):
        for l in self.layers:
            l.set_vlim(vmax, meas, vmin)


class Array(_base.eelfigure):
    def __init__(self, epochs, Xax=None, title=None, xlabel=True, ylabel=True,
                 ds=None, **layout):
        """
        Plot uts data to a rectangular grid.

        Parameters
        ----------
        epochs : NDVar
            If data has only 1 dimension, the x-axis defines epochs.
        Xax : None | categorial
            Create a separate plot for each cell in this model.
        title : None | string
            Figure title.
        xlabel, ylabel : bool | str
            I True, determine from the data.
        ds : None | Dataset
            If a Dataset is provided, ``epochs`` and ``Xax`` can be specified
            as strings.
        """
        epochs = _base.unpack_epochs_arg(epochs, 2, Xax, ds)

        nax = len(epochs)
        _base.eelfigure.__init__(self, "Array Plot", nax, layout,
                                 figtitle=title)

        self.plots = []
        vlims = _base.find_fig_vlims(epochs)
        for i, ax, layers in zip(xrange(nax), self._axes, epochs):
            _ylabel = ylabel if i == 1 else None
            _xlabel = xlabel if i == nax - 1 else None
            p = _ax_im_array(ax, layers, xlabel=_xlabel, ylabel=ylabel,
                             vlims=vlims)
            self.plots.append(p)

        self._show()

    def add_contour(self, meas, level, color='k'):
        """Add a contour line

        Parameters
        ----------
        meas : str
            The measurement for which to add a contour line.
        level : scalar
            The value at which to draw the contour.
        color : matplotlib color
            The color of the contour line.
        """
        for p in self.plots:
            p.add_contour(meas, level, color)
        self.draw()

    def set_cmap(self, cmap, meas=None):
        """Change the colormap in the array plots

        Parameters
        ----------
        cmap : str | colormap
            New colormap.
        meas : None | str
            Measurement to which to apply the colormap. With None, it is
            applied to all.
        """
        for p in self.plots:
            p.set_cmap(cmap, meas)
        self.draw()

    def set_vlim(self, vmax=None, meas=None, vmin=None):
        for p in self.plots:
            p.set_vlim(vmax, meas, vmin)
        self.draw()


def _t_axes(rect, xmin=-.5, xmax=1., vmax=1.5, vbar=1., markevery=.5, ticks=False):
    """
    creates and returns a new t-axes using rect

    vbar: extent of the vertical bar at the origin (+vbar to -vbar)

    """
    ax = plt.axes(rect, frameon=False)
    ax.set_axis_off()

    # vertical bar
    plt.plot([0, 0], [-vbar, vbar], 'k',
           marker='_', mec='k', mew=1, mfc='k')

    # horizontal bar
    xdata = np.arange(-markevery, xmax + 1e-5, markevery)
    xdata[0] = xmin
    plt.plot(xdata, xdata * 0, 'k', marker='|', mec='k', mew=1, mfc='k')
    logging.debug("xdata: %s" % str(xdata))

    # labels
    if ticks:
        ax.text(xmax, vbar * .1, r"$%s s$" % xmax, verticalalignment='bottom', horizontalalignment='center')
        ax.text(-vbar * .05, vbar, r"$%s \mu V$" % vbar, verticalalignment='center', horizontalalignment='right')
        ax.text(-vbar * .05, -vbar, r"$-%s \mu V$" % vbar, verticalalignment='center', horizontalalignment='right')
    ax.set_ylim(-vmax, vmax)
    ax.set_xlim(xmin, xmax)
    return ax



def _axgrid_sensors(sensorLocs2d, figsize=(8, 8),
                    spacing=.2, frame=.01, figvstretch=1,
                    header=0, footer=0,  # in inches
                    axes_legend_loc='lower left', **axkwargs):
    """
    creates topographocally distributed t-axes

     returns
        - list of t-axes
        - axes-legend (indicating t and V) (or None if axes_legend_loc == False)
    """
    # determine figure size and create figure
    sensorLocs2d[:, 1] *= figvstretch
    x, y = sensorLocs2d.max(axis=0) - sensorLocs2d.min(axis=0)
    ratio = (x + spacing) / (y + spacing)
    x_size, y_size = figsize
    if x_size == -1:
        x_size = y_size * ratio
    elif y_size == -1:
        y_size = x_size / ratio
    # take into account footer & header
    y_size += footer + header
    relative_footer = footer / float(y_size)
    relative_header = header / float(y_size)
    logging.debug(" _axgrid_sensors determined figsize %s x %s" % (x_size, y_size))
    fig = plt.figure(figsize=(x_size, y_size))
    # determine axes locations
    locs = sensorLocs2d
    # normalize range to 0--1
    locs -= locs.min(0)
    locs /= locs.max(0)
    # locs--> lower left points of axes
    locs[:, 0] *= (1 - spacing - 2 * frame)
    locs[:, 0] += frame
    locs[:, 1] *= (1 - spacing - 2 * frame - relative_header - relative_footer)
    locs[:, 1] += frame + relative_footer
    # print locs
    # add axes
    axes = [ _t_axes([x, y, spacing, spacing], **axkwargs) for x, y in locs ]
    if axes_legend_loc:
        x, y = _base._loc(axes_legend_loc, size=(1.1 * spacing, spacing), frame=frame)
        axes_legend = _t_axes([x, y, spacing, spacing], ticks=True, **axkwargs)
    else:
        axes_legend = None
    return axes, axes_legend


def _plt_uts(ax, epoch,
             sensors=None,  # sensors (ID) to plot
             lp=None,  # line-properties
             test_epoch=False, p=.05, softStats=False,  # testWindowFreq='max',
             sem=None,  # 'sem' (float multiplier)
             plotLabel=False,
             **plot_kwargs):
    """
    uts plot for a single epoch

    Parameters
    ----------
    ax : matplotlib axes
        Target axes.
    epoch : NDVar (sensor by time)
        Epoch to plot.
    sensors : None | True | numpy index
        The sensors to plot (None or True -> all sensors).
    lp: dictionary (line-properties)
        any keyword-arguments for matplotlib plot
    sem: = None or float
        plot standard error of the mean (e.g., ``sem=2`` plots the mean +/- 2
        sem)
    test_epoch:
        submit a test_epoch to add to plot (efficient because usually
        _ax_utsStats is called more than once for several epochs
    """
    if sensors not in [None, True]:
        epoch = epoch.subdata(sensor=sensors)

    Y = epoch.get_data(('time', 'sensor'))
    T = epoch.time  # .x[...,None]
    handles = ax.plot(T, Y, label=epoch.name, **plot_kwargs)

    for y, kwa in _base.find_uts_hlines(epoch):
        ax.axhline(y, **kwa)

    if plotLabel:
        Ymax = np.max(Y)
        ax.text(T[0] / 2, Ymax / 2, plotLabel, horizontalalignment='center')

    return handles



def _plt_extrema(ax, epoch, **plot_kwargs):
    data = epoch.get_data(('time', 'sensor'))
    Ymin = data.min(1)
    Ymax = data.max(1)
    T = epoch.time

    handle = ax.fill_between(T, Ymin, Ymax, **plot_kwargs)
    ax.set_xlim(T[0], T[-1])

    return handle


class _ax_butterfly(object):
    def __init__(self, ax, layers, sensors=None, extrema=False, title='{name}',
                xlabel=True, ylabel=True, color=None, vlims={}):
        """
        Parameters
        ----------
        vmin, vmax: None | scalar
            Y axis limits.
        """
        self.ax = ax
        self.data = layers
        self.layers = []
        self._meas = None

        vmin, vmax = _base.find_uts_ax_vlim(layers, vlims)

        xmin = []
        xmax = []
        name = ''
        overlay = False
        for l in layers:
            uts_args = _base.find_uts_args(l, overlay, color)
            if uts_args is None:
                continue
            overlay = True

            # plot
            if extrema:
                h = _plt_extrema(ax, l, **uts_args)
            else:
                h = _plt_uts(ax, l, sensors=sensors, **uts_args)

            self.layers.append(h)
            xmin.append(l.time[0])
            xmax.append(l.time[-1])

            if not name:
                name = getattr(l, 'name', '')

        # axes decoration
        l = layers[0]
        if xlabel is True:
            xlabel = 'Time [s]'
        if ylabel is True:
            ylabel = l.info.get('unit', None)

        ax.set_xlim(min(xmin), max(xmax))

        if xlabel not in [False, None]:
            ax.set_xlabel(xlabel)
        if ylabel not in [False, None]:
            ax.set_ylabel(ylabel)

    #    ax.yaxis.set_offset_position('right')
        ax.yaxis.offsetText.set_va('top')

        ax.x_fmt = "t = %.3f s"
        if isinstance(title, str):
            ax.set_title(title.format(name=name))

        self.set_vlim(vmax, vmin)

    def set_vlim(self, vmax=None, vmin=None):
        if vmin is None and vmax is not None:
            vmin = -vmax
        self.ax.set_ylim(vmin, vmax)
        vmin, vmax = self.ax.get_ylim()
        self.vmin = vmin
        self.vmax = vmax


class Butterfly(_base.eelfigure):
    "Plot data in a butterfly plot."
    def __init__(self, epochs, Xax=None, sensors=None, title=None,
                 axtitle='{name}', xlabel=True, ylabel=True, color=None,
                 ds=None, **layout):
        """
        Parameters
        ----------
        epochs : (list of) NDVar
            Data to plot.
        Xax : None | categorial
            Create a separate plot for each cell in this model.
        sensors: None or list of sensor IDs
            sensors to plot (``None`` = all)
        title : None | string
            Figure title.
        color : matplotlib color
            default (``None``): use segment color if available, otherwise
            black; ``True``: alternate colors (mpl default)
        """
        epochs = _base.unpack_epochs_arg(epochs, 2, Xax, ds)
        super(Butterfly, self).__init__('Butterfly Plot', len(epochs), layout,
                                        figtitle=title)

        self.plots = []
        vlims = _base.find_fig_vlims(epochs, True)
        for ax, layers in zip(self._axes, epochs):
            h = _ax_butterfly(ax, layers, sensors=sensors, vlims=vlims,
                              title=axtitle, xlabel=xlabel, ylabel=ylabel,
                              color=color)
            self.plots.append(h)
            xlabel = None

        self._show()

    def set_vlim(self, vmax=None, vmin=None):
        for p in self.plots:
            p.set_vlim(vmax, vmin)
        self.draw()


class _ax_bfly_epoch:
    def __init__(self, ax, epoch, xlabel=True, ylabel=True, ylim=None,
                 plot_range=True, plot_traces=False, state=True):
        """Specific plot for showing a single sensor by time epoch

        Parameters
        ----------
        epoch : NDVar
            Sensor by time epoch.
        """
        self.ax = ax
        self.epoch = epoch
        self._traces = None
        self._range = None
        self._state_h = []

        self._tmin = epoch.time[0]
        self._tmax = epoch.time[-1]
        self._ylim = ylim or epoch.info.get('ylim', None)

        self.ax.x_fmt = "t = %.3f s"

        # ax decoration
        if xlabel is True:
            xlabel = 'Time [s]'
        if ylabel is True:
            ylabel = epoch.info.get('unit', None)

        if xlabel not in [False, None]:
            self.ax.set_xlabel(xlabel)
        if ylabel not in [False, None]:
            self.ax.set_ylabel(ylabel)
            self.ax.yaxis.offsetText.set_va('top')

        # create initial plots
        if plot_range and (plot_traces is not True):
            self.plot_range()
        if plot_traces:
            self.plot_traces(plot_traces)

        self.set_state(state)

    def plot_range(self, color='k', alpha=0.5):
        "plot the range between sensors"
        self.rm_range()
        self._range = _plt_extrema(self.ax, self.epoch, color=color,
                                   alpha=alpha, antialiased=False)
        self.set_ax_lim()

    def plot_traces(self, ROI=None, color='b'):
        "Plot traces for individual sensors"
        self.rm_traces()
        self._traces = _plt_uts(self.ax, self.epoch, color=color, sensors=ROI,
                                antialiased=False)
        self.set_ax_lim()

    def rm_range(self):
        "Remove the range from the plot"
        if self._range:
            self._range.remove()
        self._range = None

    def rm_traces(self):
        "Remove the traces from the plot"
        while self._traces:
            trace = self._traces.pop()
            trace.remove()
        self._traces = None

    def set_ax_lim(self):
        self.ax.set_xlim(self._tmin, self._tmax)
        ylim = self._ylim
        if ylim:
            if np.isscalar(ylim):
                self.ax.set_ylim(-ylim, ylim)
            else:
                y_min, y_max = ylim
                self.ax.set_ylim(y_min, y_max)

    def set_state(self, state):
        "Set the state (True=accept / False=reject)"
        if state:
            while self._state_h:
                h = self._state_h.pop()
                h.remove()
        else:
            if not self._state_h:
                h1 = self.ax.plot([0, 1], [0, 1], color='r', linewidth=1,
                                  transform=self.ax.transAxes)
                h2 = self.ax.plot([0, 1], [1, 0], color='r', linewidth=1,
                                  transform=self.ax.transAxes)
                self._state_h.extend(h1 + h2)

    def update_data(self, epoch):
        self.epoch = epoch
        if self._range:
            self.plot_range()
        if self._traces:
            self.plot_traces()