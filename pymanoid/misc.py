#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2020 Stephane Caron <stephane.caron@normalesup.org>
#
# This file is part of pymanoid <https://github.com/stephane-caron/pymanoid>.
#
# pymanoid is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# pymanoid is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# pymanoid. If not, see <http://www.gnu.org/licenses/>.

from datetime import datetime
from numpy import array, dot, sqrt, tensordot, zeros


class AvgStdEstimator(object):

    """
    Online estimator for the average and standard deviation of a time series of
    scalar values.
    """

    def __init__(self):
        self.reset()

    def reset(self):
        self.last_value = None
        self.n = 0
        self.x = 0.
        self.x2 = 0.
        self.x_max = None
        self.x_min = None

    def add(self, x):
        """
        Add a new value of the time series.

        Parameters
        ----------
        x : scalar
            New value.
        """
        self.last_value = x
        self.n += 1
        self.x += x
        self.x2 += x ** 2
        if self.x_max is None or x > self.x_max:
            self.x_max = x
        if self.x_min is None or x < self.x_min:
            self.x_min = x

    @property
    def avg(self):
        """
        Average of the time series.
        """
        if self.n < 1:
            return None
        return self.x / self.n

    @property
    def std(self):
        """
        Standard deviation of the time series.
        """
        if self.n < 1:
            return None
        elif self.n == 1:
            return 0.
        unbiased = sqrt(self.n * 1. / (self.n - 1))
        return unbiased * sqrt(self.x2 / self.n - self.avg ** 2)

    def __str__(self):
        return "%f +/- %f (max: %f, min: %f) over %d items" % (
            self.avg, self.std, self.x_max, self.x_min, self.n)


class NDPolynomial(object):

    """
    Polynomial class with vector-valued coefficients.

    Parameters
    ----------
    coeffs : list of arrays
        Coefficients of the polynomial from weakest to strongest.
    """

    def __init__(self, coeffs):
        self.coeffs = coeffs
        self.shape = coeffs[0].shape

    @property
    def degree(self):
        """
        Degree of the polynomial.
        """
        return len(self.coeffs) - 1

    def __call__(self, x):
        """
        Evaluate the polynomial at `x`.

        Parameters
        ----------
        x : scalar
            Value to evaluate the polynomial at.

        Returns
        -------
        P(x) : array
            Value of the polynomial at this point.
        """
        value = zeros(self.shape)
        for coeff in reversed(self.coeffs):
            value *= x
            value += coeff
        return value


class PointWrap(object):

    """
    An object with a ``p`` array field.

    Parameters
    ----------
    p : list or array
        Point coordinates.
    """

    def __init__(self, p):
        assert len(p) == 3, "Argument is not a point"
        self.p = array(p)


class PoseWrap(object):

    """
    An object with a ``pose`` array field.

    Parameters
    ----------
    p : list or array
        Pose coordinates.
    """

    def __init__(self, pose):
        assert len(pose) == 7, "Argument is not a pose"
        self.pose = array(pose)


def error(msg):
    """
    Log an error message (in red) to stdout.

    Parameters
    ----------
    msg : str
        Error message.
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]
    print("%c[0;%d;48m%s pymanoid [ERROR] %s%c[m" % (0x1B, 31, now, msg, 0x1B))


def info(msg):
    """
    Log an information message (in green) to stdout.

    Parameters
    ----------
    msg : str
        Information message.
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]
    print("%c[0;%d;48m%s pymanoid [INFO] %s%c[m" % (0x1B, 32, now, msg, 0x1B))


def matplotlib_to_rgb(color):
    """
    Convert matplotlib color string to RGB tuple.

    Parameters
    ----------
    color : string
        Color code in matplotlib convention ('r' for red, 'b' for blue, etc.).

    Returns
    -------
    rgb : tuple
        Red-green-blue tuple with values between 0 and 1.
    """
    acolor = [0., 0., 0.]
    if color == 'k':
        return acolor
    if color == 'w':
        return [1., 1., 1.]
    if color in ['r', 'm', 'y', 'w']:
        acolor[0] += 0.5
    if color in ['g', 'y', 'c', 'w']:
        acolor[1] += 0.5
    if color in ['b', 'c', 'm', 'w']:
        acolor[2] += 0.5
    return acolor


def matplotlib_to_rgba(color, alpha=0.5):
    """
    Convert matplotlib color string to RGBA tuple.

    Parameters
    ----------
    color : string
        Color code in matplotlib convention ('r' for red, 'g' for green, etc.).
    alpha : scalar, optional
        Transparency between 0 and 1.

    Returns
    -------
    rgba : tuple
        Red-green-blue-alpha tuple with values between 0 and 1.
    """
    return matplotlib_to_rgb(color) + [alpha]


def middot(M, T):
    """
    Dot product of a matrix with the mid-coordinate of a 3D tensor.

    Parameters
    ----------
    M : array, shape=(n, m)
        Matrix to multiply.
    T : array, shape=(a, m, b)
        Tensor to multiply.

    Returns
    -------
    U : array, shape=(a, n, b)
        Dot product between `M` and `T`.
    """
    return tensordot(M, T, axes=(1, 1)).transpose([1, 0, 2])


def norm(v):
    """
    Euclidean norm.

    Parameters
    ----------
    v : array
        Any vector.

    Returns
    -------
    n : scalar
        Euclidean norm of `v`.

    Notes
    -----
    This straightforward function is 2x faster than :func:`numpy.linalg.norm`
    on my machine.
    """
    return sqrt(dot(v, v))


def normalize(v):
    """
    Normalize a vector.

    Parameters
    ----------
    v : array
        Any vector.

    Returns
    -------
    nv : array
        Unit vector directing `v`.

    Notes
    -----
    This method doesn't catch ``ZeroDivisionError`` exceptions on purpose.
    """
    return v / norm(v)


def plot_polygon(points, alpha=.4, color='g', linestyle='solid', fill=True,
                 linewidth=None):
    """
    Plot a polygon in matplotlib.

    Parameters
    ----------
    points : list of arrays
        List of poitns.
    alpha : scalar, optional
        Transparency value.
    color : string, optional
        Color in matplotlib format.
    linestyle : scalar, optional
        Line style in matplotlib format.
    fill : bool, optional
        When ``True``, fills the area inside the polygon.
    linewidth : scalar, optional
        Line width in matplotlib format.
    """
    from matplotlib.patches import Polygon
    from pylab import axis, gca
    from scipy.spatial import ConvexHull
    if type(points) is list:
        points = array(points)
    ax = gca()
    hull = ConvexHull(points)
    points = points[hull.vertices, :]
    xmin1, xmax1, ymin1, ymax1 = axis()
    xmin2, ymin2 = 1.5 * points.min(axis=0)
    xmax2, ymax2 = 1.5 * points.max(axis=0)
    axis((min(xmin1, xmin2), max(xmax1, xmax2),
          min(ymin1, ymin2), max(ymax1, ymax2)))
    patch = Polygon(
        points, alpha=alpha, color=color, linestyle=linestyle, fill=fill,
        linewidth=linewidth)
    ax.add_patch(patch)


def warn(msg):
    """
    Log a warning message (in yellow) to stdout.

    Parameters
    ----------
    msg : str
        Warning message.
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]
    print("%c[0;%d;48m%s pymanoid [WARN] %s%c[m" % (0x1B, 33, now, msg, 0x1B))
