# coding: utf-8

""" ...explain... """

from __future__ import division, print_function

__author__ = "adrn <adrn@astro.columbia.edu>"

# Third-party
import numpy as np

__all__ = ['plot_orbits', 'three_panel']

def _get_axes(dim, axes=None, triangle=False, subplots_kwargs=dict()):
    """
    Parameters
    ----------
    dim : int
        Dimensionality of the orbit.
    axes : array_like (optional)
        Array of matplotlib Axes objects.
    triangle : bool (optional)
        Make a triangle plot instead of plotting all projections in a single row.
    subplots_kwargs : dict (optional)
        Dictionary of kwargs passed to the matplotlib `subplots()` call.
    """

    import matplotlib.pyplot as plt

    if dim == 3:
        if triangle and axes is None:
            figsize = subplots_kwargs.pop('figsize', (12,12))
            sharex = subplots_kwargs.pop('sharex', True)
            sharey = subplots_kwargs.pop('sharey', True)
            fig,axes = plt.subplots(2,2,figsize=figsize, sharex=sharex, sharey=sharey,
                                    **subplots_kwargs)
            axes[0,1].set_visible(False)
            axes = axes.flat
            axes = [axes[0],axes[2],axes[3]]

        elif triangle and axes is not None:
            try:
                axes = axes.flat
            except:
                pass

            if len(axes) == 4:
                axes = [axes[0],axes[2],axes[3]]

        elif not triangle and axes is None:
            figsize = subplots_kwargs.pop('figsize', (14,5))
            fig,axes = plt.subplots(1, 3, figsize=figsize, **subplots_kwargs)

    elif dim <= 2:
        if axes is not None:
            try:
                len(axes)
            except TypeError:  # single axes object
                axes = [axes]

        else:
            if dim ==1:
                figsize = subplots_kwargs.pop('figsize', (14,8))
            elif dim == 2:
                figsize = subplots_kwargs.pop('figsize', (8,8))

            fig,axes = plt.subplots(1, 1, figsize=figsize, **subplots_kwargs)
            axes = [axes]

    else:
        raise ValueError("Orbit must have dimensions <= 3.")

    return axes

def plot_orbits(x, t=None, ix=None, axes=None, triangle=False,
                subplots_kwargs=dict(), labels=("$x$", "$y$", "$z$"), **kwargs):
    """
    Given time series of positions, `x`, make nice plots of the orbit in
    cartesian projections.

    Parameters
    ----------
    x : array_like
        Array of positions. The last axis (`axis=-1`) is assumed
        to be the dimensionality, e.g., `x.shape[-1]`. The first axis
        (`axis=0`) is assumed to be the time axis.
    t : array_like (optional)
        Arra of times. Only used if the input orbit is 1 dimensional.
    ix : int, array_like (optional)
        Index or array of indices of orbits to plot. For example, if `x` is an
        array of shape (1024,32,6) -- 1024 timesteps for 32 orbits in 6D
        phase-space -- `ix` would specify which of the 32 orbits to plot.
    axes : array_like (optional)
        Array of matplotlib Axes objects.
    triangle : bool (optional)
        Make a triangle plot instead of plotting all projections in a single row.
    subplots_kwargs : dict (optional)
        Dictionary of kwargs passed to the matplotlib `subplots()` call.
    labels : iterable (optional)
        List or iterable of axis labels as strings. They should correspond to the
        dimensions of the input orbit, for example, if the input orbit has shape
        (1000,1,3), then labels should have length=3.

    Other Parameters
    ----------------
    kwargs
        All other keyword arguments are passed to the matplotlib `plot()` call.
        You can pass in any of the usual style kwargs like `color=...`,
        `marker=...`, etc.
    """

    if x.ndim == 2:
        x = x[:,np.newaxis]

    # dimensionality of input orbit
    dim = x.shape[-1]
    if dim > 3:
        # if orbit has more than 3 dimensions, only use the first 3
        dim = 3

    # hack in some defaults to subplots kwargs so by default share x and y axes
    if 'sharex' not in subplots_kwargs:
        subplots_kwargs['sharex'] = True

    if 'sharey' not in subplots_kwargs:
        subplots_kwargs['sharey'] = True

    axes = _get_axes(dim=dim, axes=axes, triangle=triangle,
                     subplots_kwargs=subplots_kwargs)

    if ix is not None:
        ixs = np.atleast_1d(ix)
    else:
        ixs = range(x.shape[1])

    if dim == 3:
        for ii in ixs:
            axes[0].plot(x[:,ii,0], x[:,ii,1], **kwargs)
            axes[1].plot(x[:,ii,0], x[:,ii,2], **kwargs)
            axes[2].plot(x[:,ii,1], x[:,ii,2], **kwargs)

        if triangle:
            # HACK: until matplotlib 1.4 comes out, need this
            axes[0].set_ylim(axes[0].get_xlim())
            axes[2].set_xlim(axes[0].get_ylim())

            axes[0].set_ylabel(labels[1])
            axes[1].set_xlabel(labels[0])
            axes[1].set_ylabel(labels[2])
            axes[2].set_xlabel(labels[1])

        else:
            axes[0].set_xlabel(labels[0])
            axes[0].set_ylabel(labels[1])

            axes[1].set_xlabel(labels[0])
            axes[1].set_ylabel(labels[2])

            axes[2].set_xlabel(labels[1])
            axes[2].set_ylabel(labels[2])

        if not triangle:
            axes[0].figure.tight_layout()

    elif dim == 2:
        for ii in ixs:
            axes[0].plot(x[:,ii,0], x[:,ii,1], **kwargs)

        axes[0].set_xlabel(labels[0])
        axes[0].set_ylabel(labels[1])
        axes[0].figure.tight_layout()

    elif dim == 1:
        if t is None:
            t = np.arange(len(x))

        for ii in ixs:
            axes[0].plot(t, x[:,ii,0], **kwargs)

        axes[0].set_xlabel("$t$")
        axes[0].set_ylabel(labels[0])
        axes[0].figure.tight_layout()

    return axes[0].figure

def three_panel(q, relative_to=None, symbol=None, autolim=True,
                axes=None, triangle=False, subplots_kwargs=dict(), **kwargs):
    """
    Given 3D quantities, `q`, (not astropy quantities...), make nice three-panel or
    triangle plots of projections of the values.

    Parameters
    ----------
    q : array_like
        Array of values. The last axis (`axis=-1`) is assumed
        to be the dimensionality, e.g., `q.shape[-1]`.
    relative_to : bool (optional)
        Plot the values relative to this value or values.
    symbol : str (optional)
        Symbol to represent the quantity for axis labels. Can be Latex.
    autolim : bool (optional)
        Automatically set the plot limits to be something sensible.
    axes : array_like (optional)
        Array of matplotlib Axes objects.
    triangle : bool (optional)
        Make a triangle plot instead of plotting all projections in a single row.
    subplots_kwargs : dict (optional)
        Dictionary of kwargs passed to the matplotlib `subplots()` call.

    Other Parameters
    ----------------
    kwargs
        All other keyword arguments are passed to the matplotlib `scatter()` call.
        You can pass in any of the usual style kwargs like `color=...`,
        `marker=...`, etc.
    """

    # don't propagate changes back...
    q = q.copy()

    # change default marker
    marker = kwargs.pop('marker', '.')

    # get axes object from arguments
    axes = _get_axes(dim=3, axes=axes, triangle=triangle, subplots_kwargs=subplots_kwargs)

    # if the quantities are relative
    label = None
    if relative_to is not None:
        q -= relative_to

        if symbol is not None:
            label = r"$\Delta {sym}_{{ix}}/{sym}^{{{{(0)}}}}_{{ix}}$".format(sym=symbol)

    else:
        if symbol is not None:
            label = r"${sym}_{{ix}}$".format(sym=symbol)

    axes[0].scatter(q[:,0], q[:,1], marker=marker, **kwargs)
    axes[1].scatter(q[:,0], q[:,2], marker=marker, **kwargs)
    axes[2].scatter(q[:,1], q[:,2], marker=marker, **kwargs)

    if label is not None:
        if triangle:
            axes[0].set_ylabel(label.format(ix=2))
            axes[1].set_xlabel(label.format(ix=1))
            axes[1].set_ylabel(label.format(ix=3))
            axes[2].set_xlabel(label.format(ix=1))

        else:
            axes[0].set_xlabel(label.format(ix=1))
            axes[0].set_ylabel(label.format(ix=2))

            axes[1].set_xlabel(label.format(ix=1))
            axes[1].set_ylabel(label.format(ix=3))

            axes[2].set_xlabel(label.format(ix=2))
            axes[2].set_ylabel(label.format(ix=3))

    if autolim:
        lims = []
        for i in range(3):
            mx,mi = q[:,i].max(), q[:,i].min()
            delta = mx-mi
            lims.append((mi-delta*0.05, mx+delta*0.05))

        axes[0].set_xlim(lims[0])
        axes[0].set_ylim(lims[1])
        axes[1].set_xlim(lims[0])
        axes[1].set_ylim(lims[2])
        axes[2].set_xlim(lims[1])
        axes[2].set_ylim(lims[2])

    if not triangle:
        axes[0].figure.tight_layout()
    return axes[0].figure
