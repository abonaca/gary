# coding: utf-8

""" Built-in potentials implemented in Cython """

from __future__ import division, print_function

__author__ = "adrn <adrn@astro.columbia.edu>"

# Standard library
from collections import OrderedDict

# Third-party
from astropy.coordinates.angles import rotation_matrix
from astropy.constants import G
import astropy.units as u
import numpy as np
cimport numpy as np
np.import_array()
import cython
cimport cython

# Project
from .cpotential cimport _CPotential
from .cpotential import CPotential
from .core import CartesianPotential

cdef extern from "math.h":
    double sqrt(double x)
    double atan2(double x, double x)
    double acos(double x)
    double sin(double x)
    double cos(double x)
    double log(double x)
    double fabs(double x)
    double exp(double x)
    double pow(double x, double n)

__all__ = ['HernquistPotential', 'MiyamotoNagaiPotential', 'LeeSutoNFWPotential']

##############################################################################
#    Hernquist Spheroid potential from Hernquist 1990
#    http://adsabs.harvard.edu/abs/1990ApJ...356..359H
#
cdef class _HernquistPotential(_CPotential):

    # here need to cdef all the attributes
    cdef public double G, GM
    cdef public double m, c

    def __init__(self, double G, double m, double c):
        """ Units of everything should be in the system:
                kpc, Myr, radian, M_sun
        """
        # cdef double G = 4.499753324353494927e-12 # kpc^3 / Myr^2 / M_sun
        # have to specify G in the correct units
        self.G = G

        # disk parameters
        self.GM = G*m
        self.m = m
        self.c = c

    @cython.boundscheck(False)
    @cython.cdivision(True)
    @cython.wraparound(False)
    @cython.nonecheck(False)
    cdef public inline void _value(self, double[:,::1] r,
                                   double[::1] pot, int nparticles):

        cdef double R
        for i in range(nparticles):
            R = sqrt(r[i,0]*r[i,0] + r[i,1]*r[i,1] + r[i,2]*r[i,2])
            pot[i] = -self.GM / (R + self.c)

    @cython.boundscheck(False)
    @cython.cdivision(True)
    @cython.wraparound(False)
    @cython.nonecheck(False)
    cdef public inline void _gradient(self, double[:,::1] r,
                                      double[:,::1] grad, int nparticles):

        cdef double x, y, z, R, fac
        for i in range(nparticles):
            x = r[i,0]
            y = r[i,1]
            z = r[i,2]
            R = sqrt(x*x + y*y + z*z)

            fac = self.GM / (pow(R + self.c,2) * R)

            grad[i,0] = fac*x
            grad[i,1] = fac*y
            grad[i,2] = fac*z

    # @cython.boundscheck(False)
    # @cython.cdivision(True)
    # @cython.wraparound(False)
    # @cython.nonecheck(False)
    # cdef public inline void _hessian(self, double[:,::1] r,
    #                                  double[:,:,::1] hess, int nparticles):

    #     cdef double x, y, z
    #     cdef double sqrtz, zd, fac
    #     for i in range(nparticles):
    #         x = r[i,0]
    #         y = r[i,1]
    #         z = r[i,2]

    #         sqrtz = sqrt(z*z + self.b2)
    #         zd = self.a + sqrtz
    #         fac = self.GM*pow(x*x + y*y + zd*zd, -1.5)

    #         grad[i,0] = fac*x
    #         grad[i,1] = fac*y
    #         grad[i,2] = fac*z * (1. + self.a / sqrtz)

class HernquistPotential(CPotential, CartesianPotential):
    r"""
    Hernquist potential for a spheroid.

    .. math::

        \Phi_{spher} = -\frac{GM_{spher}}{r + c}

    Parameters
    ----------
    m : numeric
        Mass.
    c : numeric
        Core concentration.
    usys : iterable
        Unique list of non-reducable units that specify (at minimum) the
        length, mass, time, and angle units.

    """
    def __init__(self, m, c, usys):
        self.usys = usys
        _G = G.decompose(usys).value
        parameters = dict(G=_G, m=m, c=c)
        super(HernquistPotential, self).__init__(_HernquistPotential,
                                                 parameters=parameters)

##############################################################################
#    Miyamoto-Nagai Disk potential from Miyamoto & Nagai 1975
#    http://adsabs.harvard.edu/abs/1975PASJ...27..533M
#
cdef class _MiyamotoNagaiPotential(_CPotential):

    # here need to cdef all the attributes
    cdef public double G, GM
    cdef public double m, a, b, b2

    def __init__(self, double G, double m, double a, double b):
        """ Units of everything should be in the system:
                kpc, Myr, radian, M_sun
        """
        # cdef double G = 4.499753324353494927e-12 # kpc^3 / Myr^2 / M_sun
        # have to specify G in the correct units
        self.G = G

        # disk parameters
        self.GM = G*m
        self.m = m
        self.a = a
        self.b = b
        self.b2 = b*b

    @cython.boundscheck(False)
    @cython.cdivision(True)
    @cython.wraparound(False)
    @cython.nonecheck(False)
    cdef public inline void _value(self, double[:,::1] r,
                                   double[::1] pot, int nparticles):

        cdef double x, y, z
        cdef double zd
        for i in range(nparticles):
            x = r[i,0]
            y = r[i,1]
            z = r[i,2]

            zd = (self.a + sqrt(z*z+self.b2))
            pot[i] = -self.GM / sqrt(x*x + y*y + zd*zd)

    @cython.boundscheck(False)
    @cython.cdivision(True)
    @cython.wraparound(False)
    @cython.nonecheck(False)
    cdef public inline void _gradient(self, double[:,::1] r,
                                      double[:,::1] grad, int nparticles):

        cdef double x, y, z
        cdef double sqrtz, zd, fac
        for i in range(nparticles):
            x = r[i,0]
            y = r[i,1]
            z = r[i,2]

            sqrtz = sqrt(z*z + self.b2)
            zd = self.a + sqrtz
            fac = self.GM*pow(x*x + y*y + zd*zd, -1.5)

            grad[i,0] = fac*x
            grad[i,1] = fac*y
            grad[i,2] = fac*z * (1. + self.a / sqrtz)

    # @cython.boundscheck(False)
    # @cython.cdivision(True)
    # @cython.wraparound(False)
    # @cython.nonecheck(False)
    # cdef public inline void _hessian(self, double[:,::1] r,
    #                                  double[:,:,::1] hess, int nparticles):

    #     cdef double x, y, z
    #     cdef double sqrtz, zd, fac
    #     for i in range(nparticles):
    #         x = r[i,0]
    #         y = r[i,1]
    #         z = r[i,2]

    #         sqrtz = sqrt(z*z + self.b2)
    #         zd = self.a + sqrtz
    #         fac = self.GM*pow(x*x + y*y + zd*zd, -1.5)

    #         grad[i,0] = fac*x
    #         grad[i,1] = fac*y
    #         grad[i,2] = fac*z * (1. + self.a / sqrtz)


class MiyamotoNagaiPotential(CPotential, CartesianPotential):
    r"""
    Miyamoto-Nagai potential for a flattened mass distribution.

    .. math::

        \Phi_{disk} = -\frac{GM_{disk}}{\sqrt{R^2 + (a + \sqrt{z^2 + b^2})^2}}

    Parameters
    ----------
    m : numeric
        Mass.
    a : numeric
    b : numeric
    usys : iterable
        Unique list of non-reducable units that specify (at minimum) the
        length, mass, time, and angle units.

    """
    def __init__(self, m, a, b, usys):
        self.usys = usys
        _G = G.decompose(usys).value
        parameters = dict(G=_G, m=m, a=a, b=b)
        super(MiyamotoNagaiPotential, self).__init__(_MiyamotoNagaiPotential,
                                                     parameters=parameters)

##############################################################################
#    Lee & Suto (2003) triaxial NFW potential
#    http://adsabs.harvard.edu/abs/2003ApJ...585..151L
#
cdef class _LeeSutoNFWPotential(_CPotential):

    # here need to cdef all the attributes
    cdef public double v_h, r_h, a, b, c, e_b2, e_c2
    cdef public double v_h2, r_h2, a2, b2, c2, x0
    cdef public double[:,::1] R, Rinv

    def __init__(self, double v_h, double r_h, double a, double b, double c,
                 double[:,::1] R):
        """ Units of everything should be in the system:
                kpc, Myr, radian, M_sun
        """

        self.v_h = v_h
        self.v_h2 = v_h*v_h
        self.r_h = r_h
        self.r_h2 = r_h*r_h
        self.a = a
        self.a2 = a*a
        self.b = b
        self.b2 = b*b
        self.c = c
        self.c2 = c*c

        self.e_b2 = 1-pow(b/a,2)
        self.e_c2 = 1-pow(c/a,2)

        self.x0 = 1/r_h
        self.R = R
        self.Rinv = np.linalg.inv(R)

    @cython.boundscheck(False)
    @cython.cdivision(True)
    @cython.wraparound(False)
    @cython.nonecheck(False)
    cdef public inline void _value(self, double[:,::1] r,
                                   double[::1] pot, int nparticles):

        cdef double x, y, z, _r, u, _x, _y, _z
        for i in range(nparticles):
            _x = r[i,0]
            _y = r[i,1]
            _z = r[i,2]

            x = self.R[0,0]*_x + self.R[0,1]*_y + self.R[0,2]*_z
            y = self.R[1,0]*_x + self.R[1,1]*_y + self.R[1,2]*_z
            z = self.R[2,0]*_x + self.R[2,1]*_y + self.R[2,2]*_z

            _r = sqrt(x*x + y*y + z*z)
            u = _r / self.r_h
            pot[i] = self.v_h2*((self.e_b2/2 + self.e_c2/2)*((1/u - 1/u**3)*log(u + 1) - 1 + (2*u**2 - 3*u + 6)/(6*u**2)) + (self.e_b2*y**2/(2*_r*_r) + self.e_c2*z*z/(2*_r*_r))*((u*u - 3*u - 6)/(2*u*u*(u + 1)) + 3*log(u + 1)/u/u/u) - log(u + 1)/u)

    @cython.boundscheck(False)
    @cython.cdivision(True)
    @cython.wraparound(False)
    @cython.nonecheck(False)
    cdef public inline void _gradient(self, double[:,::1] r,
                                      double[:,::1] grad, int nparticles):

        cdef:
            double x, y, z, _r, _r2, _x, _y, _z, ax, ay, az
            double x0, x1, x2, x7
            double x10, x11, x13, x15, x16, x17, x18
            double x20, x21, x22

        for i in range(nparticles):
            _x = r[i,0]
            _y = r[i,1]
            _z = r[i,2]

            x = self.R[0,0]*_x + self.R[0,1]*_y + self.R[0,2]*_z
            y = self.R[1,0]*_x + self.R[1,1]*_y + self.R[1,2]*_z
            z = self.R[2,0]*_x + self.R[2,1]*_y + self.R[2,2]*_z

            _r2 = x*x + y*y + z*z
            _r = sqrt(_r2)

            x0 = _r + self.r_h
            x1 = x0*x0
            x2 = self.v_h2/(12.*pow(_r,7)*x1)
            x7 = self.e_b2*y*y + self.e_c2*z*z
            x10 = log(x0/self.r_h)
            x11 = x0*x10
            x13 = _r*3.*self.r_h
            x15 = x13 - _r2
            x16 = x15 + 6.*self.r_h2
            x17 = 6.*self.r_h*x0*(_r*x16 - x11*6.*self.r_h2)
            x18 = x1*x10
            x20 = x0*_r2
            x21 = 2.*_r*x0
            x22 = -12.*pow(_r,5)*self.r_h*x0 + 12.*pow(_r,4)*self.r_h*x18 + 3.*self.r_h*x7*(x16*_r2 - 18.*x18*self.r_h2 + x20*(2.*_r - 3.*self.r_h) + x21*(x15 + 9.*self.r_h2)) - x20*(self.e_b2 + self.e_c2)*(-6.*_r*self.r_h*(_r2 - self.r_h2) + 6.*self.r_h*x11*(_r2 - 3.*self.r_h2) + x20*(-4.*_r + 3.*self.r_h) + x21*(-x13 + 2.*_r2 + 6.*self.r_h2))

            ax = x2*x*(x17*x7 + x22)
            ay = x2*y*(x17*(x7 - _r2*self.e_b2) + x22)
            az = x2*z*(x17*(x7 - _r2*self.e_c2) + x22)

            grad[i,0] = self.Rinv[0,0]*ax + self.Rinv[0,1]*ay + self.Rinv[0,2]*az
            grad[i,1] = self.Rinv[1,0]*ax + self.Rinv[1,1]*ay + self.Rinv[1,2]*az
            grad[i,2] = self.Rinv[2,0]*ax + self.Rinv[2,1]*ay + self.Rinv[2,2]*az



class LeeSutoNFWPotential(CPotential, CartesianPotential):
    r"""
    TODO:

    .. math::

        \Phi() =

    Parameters
    ----------
    phi : numeric (optional)
        Euler angle for rotation about z-axis (using the x-convention
        from Goldstein). Allows for specifying a misalignment between
        the halo and disk potentials.
    theta : numeric (optional)
        Euler angle for rotation about x'-axis (using the x-convention
        from Goldstein). Allows for specifying a misalignment between
        the halo and disk potentials.
    psi : numeric (optional)
        Euler angle for rotation about z'-axis (using the x-convention
        from Goldstein). Allows for specifying a misalignment between
        the halo and disk potentials.
    usys : iterable
        Unique list of non-reducable units that specify (at minimum) the
        length, mass, time, and angle units.

    """
    def __init__(self, v_h, r_h, a, b, c, phi=0., theta=0., psi=0., usys=None):
        self.usys = usys
        parameters = dict(v_h=v_h, r_h=r_h, a=a, b=b, c=c)

        if theta != 0 or phi != 0 or psi != 0:
            D = rotation_matrix(phi, "z", unit=u.radian)
            C = rotation_matrix(theta, "x", unit=u.radian)
            B = rotation_matrix(psi, "z", unit=u.radian)
            R = np.array(B.dot(C).dot(D))

        else:
            R = np.eye(3)

        parameters['R'] = R
        super(LeeSutoNFWPotential, self).__init__(_LeeSutoNFWPotential,
                                                  parameters=parameters)