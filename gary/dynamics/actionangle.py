# coding: utf-8

from __future__ import division, print_function

"""
Utilities for estimating actions and angles for an arbitrary orbit in an
arbitrary potential.
"""

__author__ = "adrn <adrn@astro.columbia.edu>"

# Standard library
import time

# Third-party
import numpy as np
from astropy import log as logger
from scipy.linalg import solve
from scipy.optimize import leastsq

# Project
from .core import classify_orbit, align_circulation_with_z
from ..potential import HarmonicOscillatorPotential, IsochronePotential

__all__ = ['generate_n_vectors', 'unwrap_angles', 'fit_isochrone',
           'fit_harmonic_oscillator', 'fit_toy_potential', 'check_angle_sampling',
           'find_actions']

def generate_n_vectors(N_max, dx=1, dy=1, dz=1, half_lattice=True):
    """
    Generate integer vectors with |n| < N_max.

    If `half_lattice=True`, only return half of the three-dimensional lattice.
    If the set N = {(i,j,k)} defines the lattice, we restrict to the cases
    such that (k > 0), (k = 0, j > 0), and (k = 0, j = 0, i > 0).

    Parameters
    ----------
    N_max : int
        Maximum norm of the integer vector.
    dx : int
        Step size in x direction. Set to 1 for odd and even terms, set
        to 2 for just even terms.
    dy : int
        Step size in y direction. Set to 1 for odd and even terms, set
        to 2 for just even terms.
    dz : int
        Step size in z direction. Set to 1 for odd and even terms, set
        to 2 for just even terms.
    half_lattice : bool (optional)
        Only return half of the 3D lattice.

    Returns
    -------
    vecs : :class:`numpy.ndarray`
        A 2D array of integers with |n| < N_max with shape (N,3).

    """
    vecs = np.meshgrid(np.arange(-N_max, N_max+1, dx),
                       np.arange(-N_max, N_max+1, dy),
                       np.arange(-N_max, N_max+1, dz))
    vecs = np.vstack(map(np.ravel,vecs)).T
    vecs = vecs[np.linalg.norm(vecs,axis=1) <= N_max]

    if half_lattice:
        ix = ((vecs[:,2] > 0) | ((vecs[:,2] == 0) & (vecs[:,1] > 0)) | ((vecs[:,2] == 0) & (vecs[:,1] == 0) & (vecs[:,0] > 0)))
        vecs = vecs[ix]

    vecs = np.array(sorted(vecs, key=lambda x: (x[0],x[1],x[2])))
    return vecs

def unwrap_angles(angles, sign=1.):
    """
    Unwraps the angles so they increase continuously instead of wrapping at 2π.

    .. warning::

        This function does not properly handle negative angles.

    Parameters
    ----------
    angles : array_like
        Array of angles, (ntimes,3).
    sign : numeric (optional)
        Vector that defines direction of circulation about the axes.

    Returns
    -------
    unwrapped_angles : :class:`numpy.ndarray`
        Array of unbounded angles.

    """

    # set the initial angles
    unwrapped_angles = np.zeros_like(angles)
    unwrapped_angles[0] = angles[0]

    n = np.cumsum(((angles[1:] - angles[:-1] + 0.5*sign*np.pi)*sign < 0) * 2.*np.pi, axis=0)
    unwrapped_angles[1:] = angles[1:] + sign*n
    return unwrapped_angles

def fit_isochrone(w, units, m0=2E11, b0=1.):
    r"""
    Fit the toy Isochrone potential to the sum of the energy residuals relative
    to the mean energy by minimizing the function

    .. math::

        f(m,b) = \sum_i (\frac{1}{2}v_i^2 + \Phi_{\rm iso}(x_i\,|\,m,b) - <E>)^2

    Parameters
    ----------
    w : array_like
        Array of phase-space positions.
    units : iterable
        Unique list of non-reducable units that specify (at minimum) the
        length, mass, time, and angle units. For example,
        (u.kpc, u.Myr, u.Msun).
    m0 : numeric (optional)
        Initial mass guess.
    b0 : numeric (optional)
        Initial b guess.

    Returns
    -------
    m : float
        Best-fit scale mass for the Isochrone potential.
    b : float
        Best-fit core radius for the Isochrone potential.

    """
    # initialize with any values, will be set by m0 and b0 passed in
    potential = IsochronePotential(m=m0, b=b0, units=units)

    def f(p,w):
        logm,b = p
        potential.parameters['m'] = np.exp(logm)
        potential.parameters['b'] = b
        H = potential.total_energy(w[...,:3], w[...,3:])
        return np.squeeze(H - np.mean(H))

    logm0 = np.log(m0)
    p,ier = leastsq(f, np.array([logm0, b0]), args=(w,))
    if ier < 1 or ier > 4:
        raise ValueError("Failed to fit toy potential to orbit.")

    logm,b = np.abs(p)
    m = np.exp(logm)

    return IsochronePotential(m=m, b=b, units=units)

def fit_harmonic_oscillator(w, units, omega0=[1.,1.,1.]):
    r"""
    Fit the toy harmonic oscillator potential to the sum of the energy
    residuals relative to the mean energy by minimizing the function

    .. math::

        f(\boldsymbol{\omega}) = \sum_i (\frac{1}{2}v_i^2 + \Phi_{\rm sho}(x_i\,|\,\boldsymbol{\omega}) - <E>)^2


    Parameters
    ----------
    w : array_like
        Array of phase-space positions.
    units : iterable
        Unique list of non-reducable units that specify (at minimum) the
        length, mass, time, and angle units. For example,
        (u.kpc, u.Myr, u.Msun).
    omega0 : array_like (optional)
        Initial frequency guess.

    Returns
    -------
    omegas : float
        Best-fit harmonic oscillator frequencies.

    """
    omega0 = np.atleast_1d(omega0)

    # initialize potential object
    potential = HarmonicOscillatorPotential(omega=omega0)

    def f(omega,w):
        potential.parameters['omega'] = omega
        H = potential.total_energy(w[...,:3], w[...,3:])
        return np.squeeze(H - np.mean(H))

    p,ier = leastsq(f, np.array(omega0), args=(w,))
    if ier < 1 or ier > 4:
        raise ValueError("Failed to fit toy potential to orbit.")

    best_omega = np.abs(p)
    return HarmonicOscillatorPotential(omega=best_omega)

def fit_toy_potential(w, units, force_harmonic_oscillator=False):
    """
    Fit a best fitting toy potential to the orbit provided. If the orbit is a
    tube (loop) orbit, use the Isochrone potential. If the orbit is a box
    potential, use the harmonic oscillator potential. An option is available to
    force using the harmonic oscillator (`force_harmonic_oscillator`).

    See the docstrings for ~`gary.dynamics.fit_isochrone()` and
    ~`gary.dynamics.fit_harmonic_oscillator()` for more information.

    Parameters
    ----------
    w : array_like
        Phase-space orbit at times, `t`. Should have shape (ntimes,6).
    units : iterable
        Unique list of non-reducable units that specify (at minimum) the
        length, mass, time, and angle units. For example,
        (u.kpc, u.Myr, u.Msun).
    force_harmonic_oscillator : bool (optional)
        Force using the harmonic oscillator potential as the toy potential.

    Returns
    -------
    potential : :class:`~gary.potential.IsochronePotential` or :class:`~gary.potential.HarmonicOscillatorPotential`
        The best-fit potential object.

    """
    orbit_class = classify_orbit(w)
    if np.any(orbit_class == 1) and not force_harmonic_oscillator:  # tube orbit
        logger.debug("===== Tube orbit =====")
        logger.debug("Using Isochrone toy potential")

        toy_potential = fit_isochrone(w, units=units)
        logger.debug("Best m={}, b={}".format(toy_potential.parameters['m'],
                                              toy_potential.parameters['b']))

    else:  # box orbit
        logger.debug("===== Box orbit =====")
        logger.debug("Using triaxial harmonic oscillator toy potential")

        toy_potential = fit_harmonic_oscillator(w, units=units)
        logger.debug("Best omegas ({})".format(toy_potential.parameters['omega']))

    return toy_potential

def check_angle_sampling(nvecs, angles):
    """
    Returns a list of the index of elements of n which do not have adequate
    toy angle coverage. The criterion is that we must have at least one sample
    in each Nyquist box when we project the toy angles along the vector n.

    Parameters
    ----------
    nvecs : array_like
        Array of integer vectors.
    angles : array_like
        Array of angles.

    Returns
    -------
    failed_nvecs : :class:`numpy.ndarray`
        Array of all integer vectors that failed checks. Has shape (N,3).
    failures : :class:`numpy.ndarray`
        Array of flags that designate whether this failed needing a longer
        integration window (0) or finer sampling (1).

    """

    failed_nvecs = []
    failures = []

    logger.debug("Checking modes:")
    for i,vec in enumerate(nvecs):
        # N = np.linalg.norm(vec)
        X = np.dot(angles,vec)
        diff = float(np.abs(X.max() - X.min()))

        if diff < (2.*np.pi):
            logger.warning("Need a longer integration window for mode " + str(vec))
            failed_nvecs.append(vec.tolist())
            # P.append(2.*np.pi - diff)
            failures.append(0)

        elif (diff/len(X)) > np.pi:
            logger.warning("Need a finer sampling for mode " + str(vec))
            failed_nvecs.append(vec.tolist())
            # P.append(np.pi - diff/len(X))
            failures.append(1)

    return np.array(failed_nvecs), np.array(failures)

def _action_prepare(aa, N_max, dx, dy, dz, sign=1., throw_out_modes=False):
    """
    Given toy actions and angles, `aa`, compute the matrix `A` and
    vector `b` to solve for the vector of "true" actions and generating
    function values, `x` (see Equations 12-14 in Sanders & Binney (2014)).

    Parameters
    ----------
    aa : array_like
        Shape (ntimes,6) array of toy actions and angles.
    N_max : int
        Maximum norm of the integer vector.
    dx : int
        Step size in x direction. Set to 1 for odd and even terms, set
        to 2 for just even terms.
    dy : int
        Step size in y direction. Set to 1 for odd and even terms, set
        to 2 for just even terms.
    dz : int
        Step size in z direction. Set to 1 for odd and even terms, set
        to 2 for just even terms.
    sign : numeric (optional)
        Vector that defines direction of circulation about the axes.
    """

    # unroll the angles so they increase continuously instead of wrap
    angles = unwrap_angles(aa[:,3:], sign=sign)

    # generate integer vectors for fourier modes
    nvecs = generate_n_vectors(N_max, dx, dy, dz)

    # make sure we have enough angle coverage
    modes,P = check_angle_sampling(nvecs, angles)

    # throw out modes?
    # if throw_out_modes:
    #     nvecs = np.delete(nvecs, (modes,P), axis=0)

    n = len(nvecs) + 3
    b = np.zeros(shape=(n, ))
    A = np.zeros(shape=(n,n))

    # top left block matrix: identity matrix summed over timesteps
    A[:3,:3] = len(aa)*np.identity(3)

    actions = aa[:,:3]
    angles = aa[:,3:]

    # top right block matrix: transpose of C_nk matrix (Eq. 12)
    C_T = 2.*nvecs.T * np.sum(np.cos(np.dot(nvecs,angles.T)), axis=-1)
    A[:3,3:] = C_T
    A[3:,:3] = C_T.T

    # lower right block matrix: C_nk dotted with C_nk^T
    cosv = np.cos(np.dot(nvecs,angles.T))
    A[3:,3:] = 4.*np.dot(nvecs,nvecs.T)*np.einsum('it,jt->ij', cosv, cosv)

    # b vector first three is just sum of toy actions
    b[:3] = np.sum(actions, axis=0)

    # rest of the vector is C dotted with actions
    b[3:] = 2*np.sum(np.dot(nvecs,actions.T)*np.cos(np.dot(nvecs,angles.T)), axis=1)

    return A,b,nvecs

def _angle_prepare(aa, t, N_max, dx, dy, dz, sign=1.):
    """
    Given toy actions and angles, `aa`, compute the matrix `A` and
    vector `b` to solve for the vector of "true" angles, frequencies, and
    generating function derivatives, `x` (see Appendix of
    Sanders & Binney (2014)).

    Parameters
    ----------
    aa : array_like
        Shape (ntimes,6) array of toy actions and angles.
    t : array_like
        Array of times.
    N_max : int
        Maximum norm of the integer vector.
    dx : int
        Step size in x direction. Set to 1 for odd and even terms, set
        to 2 for just even terms.
    dy : int
        Step size in y direction. Set to 1 for odd and even terms, set
        to 2 for just even terms.
    dz : int
        Step size in z direction. Set to 1 for odd and even terms, set
        to 2 for just even terms.
    sign : numeric (optional)
        Vector that defines direction of circulation about the axes.
    """

    # unroll the angles so they increase continuously instead of wrap
    angles = unwrap_angles(aa[:,3:], sign=sign)

    # generate integer vectors for fourier modes
    nvecs = generate_n_vectors(N_max, dx, dy, dz)

    # make sure we have enough angle coverage
    modes,P = check_angle_sampling(nvecs, angles)

    # TODO: throw out modes?
    # if(throw_out_modes):
    #     n_vectors = np.delete(n_vectors,check_each_direction(n_vectors,angs),axis=0)

    nv = len(nvecs)
    n = 3 + 3 + 3*nv # angle(0)'s, freqs, 3 derivatives of Sn

    b = np.zeros(shape=(n,))
    A = np.zeros(shape=(n,n))

    # top left block matrix: identity matrix summed over timesteps
    A[:3,:3] = len(aa)*np.identity(3)

    # identity matrices summed over times
    A[:3,3:6] = A[3:6,:3] = np.sum(t)*np.identity(3)
    A[3:6,3:6] = np.sum(t*t)*np.identity(3)

    # S1,2,3
    A[6:6+nv,0] = -2.*np.sum(np.sin(np.dot(nvecs,angles.T)),axis=1)
    A[6+nv:6+2*nv,1] = A[6:6+nv,0]
    A[6+2*nv:6+3*nv,2] = A[6:6+nv,0]

    # t*S1,2,3
    A[6:6+nv,3] = -2.*np.sum(t[None,:]*np.sin(np.dot(nvecs,angles.T)),axis=1)
    A[6+nv:6+2*nv,4] = A[6:6+nv,3]
    A[6+2*nv:6+3*nv,5] = A[6:6+nv,3]

    # lower right block structure: S dot S^T
    sinv = np.sin(np.dot(nvecs,angles.T))
    SdotST = np.einsum('it,jt->ij', sinv, sinv)
    A[6:6+nv,6:6+nv] = A[6+nv:6+2*nv,6+nv:6+2*nv] = \
        A[6+2*nv:6+3*nv,6+2*nv:6+3*nv] = 4*SdotST

    # top rectangle
    A[:6,:] = A[:,:6].T

    b[:3] = np.sum(angles, axis=0)
    b[3:6] = np.sum(t[:,None]*angles, axis=0)
    b[6:6+nv] = -2.*np.sum(angles[:,0]*np.sin(np.dot(nvecs,angles.T)), axis=1)
    b[6+nv:6+2*nv] = -2.*np.sum(angles[:,1]*np.sin(np.dot(nvecs,angles.T)), axis=1)
    b[6+2*nv:6+3*nv] = -2.*np.sum(angles[:,2]*np.sin(np.dot(nvecs,angles.T)), axis=1)

    return A,b,nvecs

def _single_orbit_find_actions(t, w, N_max, units, toy_potential=None,
                               force_harmonic_oscillator=False):
    """
    Find approximate actions and angles for samples of a phase-space orbit,
    `w`, at times `t`. Uses toy potentials with known, analytic action-angle
    transformations to approximate the true coordinates as a Fourier sum.

    This code is adapted from Jason Sanders'
    `genfunc <https://github.com/jlsanders/genfunc>`_

    Parameters
    ----------
    t : array_like
        Array of times with shape (ntimes,).
    w : array_like
        Phase-space orbit at times, `t`. Should have shape (ntimes,6).
    N_max : int
        Maximum integer Fourier mode vector length, |n|.
    units : iterable
        Unique list of non-reducable units that specify (at minimum) the
        length, mass, time, and angle units. For example,
        (u.kpc, u.Myr, u.Msun).
    toy_potential : Potential (optional)
        Fix the toy potential class.
    force_harmonic_oscillator : bool (optional)
        Force using the harmonic oscillator potential as the toy potential.
    """

    if w.ndim > 2:
        raise ValueError("w must be a single orbit")

    if toy_potential is None:
        toy_potential = fit_toy_potential(w, units=units,
                                          force_harmonic_oscillator=force_harmonic_oscillator)

    else:
        logger.debug("Using *fixed* toy potential: {}".format(toy_potential.parameters))

    if isinstance(toy_potential, IsochronePotential):
        loop = classify_orbit(w)
        w = align_circulation_with_z(w, loop[0])

        dxyz = (1,2,2)
        circ = np.sign(w[0,0]*w[0,4]-w[0,1]*w[0,3])
        sign = np.array([1.,circ,1.])
    elif isinstance(toy_potential, HarmonicOscillatorPotential):
        dxyz = (2,2,2)
        sign = 1.
    else:
        raise ValueError("Invalid toy potential.")

    # Now find toy actions and angles
    aa = np.hstack(toy_potential.action_angle(w[:,:3], w[:,3:]))
    if np.any(np.isnan(aa)):
        ix = ~np.any(np.isnan(aa),axis=1)
        aa = aa[ix]
        t = t[ix]
        logger.warning("NaN value in toy actions or angles!")
        if sum(ix) > 1:
            raise ValueError("Too many NaN value in toy actions or angles!")

    t1 = time.time()
    A,b,nvecs = _action_prepare(aa, N_max, dx=dxyz[0], dy=dxyz[1], dz=dxyz[2])
    actions = np.array(solve(A,b))
    logger.debug("Action solution found for N_max={}, size {} symmetric"
                 " matrix in {} seconds"
                 .format(N_max,len(actions),time.time()-t1))

    t1 = time.time()
    A,b,nvecs = _angle_prepare(aa, t, N_max, dx=dxyz[0], dy=dxyz[1], dz=dxyz[2], sign=sign)
    angles = np.array(solve(A,b))
    logger.debug("Angle solution found for N_max={}, size {} symmetric"
                 " matrix in {} seconds"
                 .format(N_max,len(angles),time.time()-t1))

    # Just some checks
    if len(angles) > len(aa):
        logger.warning("More unknowns than equations!")

    J = actions[:3]  # * sign
    theta = angles[:3]
    freqs = angles[3:6]  # * sign

    return dict(actions=J, angles=theta, freqs=freqs,
                Sn=actions[3:], dSn_dJ=angles[6:], nvecs=nvecs)

def find_actions(t, w, N_max, units, force_harmonic_oscillator=False, toy_potential=None):
    """
    Find approximate actions and angles for samples of a phase-space orbit,
    `w`, at times `t`. Uses toy potentials with known, analytic action-angle
    transformations to approximate the true coordinates as a Fourier sum.

    This code is adapted from Jason Sanders'
    `genfunc <https://github.com/jlsanders/genfunc>`_

    Parameters
    ----------
    t : array_like
        Array of times with shape (ntimes,).
    w : array_like
        Phase-space orbit at times, `t`. Should have shape (ntimes,norbits,6).
    N_max : int
        Maximum integer Fourier mode vector length, |n|.
    units : iterable
        Unique list of non-reducable units that specify (at minimum) the
        length, mass, time, and angle units. For example,
        (u.kpc, u.Myr, u.Msun).
    force_harmonic_oscillator : bool (optional)
        Force using the harmonic oscillator potential as the toy potential.
    toy_potential : Potential (optional)
        Fix the toy potential class.
    return_Sn : bool (optional)
        Return the Sn and dSn/dJ's. Default is False.

    Returns
    -------
    aaf : dict
        A Python dictionary containing the actions, angles, frequencies, and
        value of the generating function and derivatives for each integer
        vector. Each value of the dictionary is a :class:`numpy.ndarray`.

    """

    if w.ndim == 2 or w.shape[1] == 1:
        w = np.squeeze(w)
        return _single_orbit_find_actions(t, w, N_max, units,
                                          force_harmonic_oscillator=force_harmonic_oscillator,
                                          toy_potential=toy_potential)

    elif w.ndim == 3:
        ntime,norbits,ndim = w.shape
        actions = np.zeros((norbits,3))
        angles = np.zeros((norbits,3))
        freqs = np.zeros((norbits,3))
        for n in range(norbits):
            aaf = _single_orbit_find_actions(t, w[:,n], N_max, units,
                                             force_harmonic_oscillator=force_harmonic_oscillator,
                                             toy_potential=toy_potential)
            actions[n] = aaf['actions']
            angles[n] = aaf['angles']
            freqs[n] = aaf['freqs']

    else:
        raise ValueError("Invalid shape for orbit array: {}".format(w.shape))

    # TODO: this is broken -- what to return and how to pre-determine shape?
    return dict(actions=actions, angles=angles, freqs=freqs,
                Sn=actions[3:], dSn=angles[6:], nvecs=nvecs)

# def solve_hessian(relative_actions, relative_freqs):
#     """ Use ordinary least squares to solve for the Hessian, given a
#         set of actions and frequencies relative to the parent orbit.
#     """

# def compute_hessian(t, w, actions_kwargs={}):
#     """ Compute the Hessian (in action-space) of the given orbit

#     """

#     N = dJ.shape[0]

#     Y = np.ravel(dF)
#     A = np.zeros((3*N,9))
#     A[::3,:3] = dJ
#     A[1::3,3:6] = dJ
#     A[2::3,6:9] = dJ

#     # Solve for 'parameters' - the Hessian elements
#     X,res,rank,s = np.linalg.lstsq(A, Y)

#     # Symmetrize
#     D0 = X.reshape(3,3)
#     D0[0,1] = D0[1,0] = (D0[0,1] + D0[1,0])/2.
#     D0[0,2] = D0[2,0] = (D0[0,2] + D0[2,0])/2.
#     D0[1,2] = D0[2,1] = (D0[1,2] + D0[2,1])/2.

#     print("Residual: " + str(res[0]))

#     return D0,np.linalg.eigh(D0) # symmetric matrix
