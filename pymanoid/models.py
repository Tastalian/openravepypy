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

from numpy import cosh, dot, sinh, sqrt

from .body import Point
from .gui import draw_line, draw_point
from .misc import warn
from .sim import Process, gravity


class InvertedPendulum(Process):

    """
    Inverted pendulum model.

    Parameters
    ----------
    pos : (3,) array
        Initial position in the world frame.
    vel : (3,) array
        Initial velocity in the world frame.
    contact : pymanoid.Contact
        Contact surface specification.
    lambda_min : scalar
        Minimum virtual leg stiffness.
    lambda_max : scalar
        Maximum virtual leg stiffness.
    clamp : bool, optional
        Clamp inputs (e.g. CoP) if they exceed constraints (e.g. support area)?
    visible : bool, optional
        Draw the pendulum model in GUI?
    color : char, optional
        Color code in matplotlib convention ('r' for red, 'b' for blue, etc.).
    size : scalar, optional
        Half-length of a side of the CoM cube handle, in [m].
    """

    def __init__(self, pos, vel, contact, lambda_min=1e-5, lambda_max=None,
                 clamp=True, visible=True, color='b', size=0.02):
        super(InvertedPendulum, self).__init__()
        com = Point(pos, vel, size=size, color=color)
        self.clamp = clamp
        self.color = color
        self.com = com
        self.contact = contact
        self.cop = contact.p
        self.handles = None
        self.is_visible = visible
        self.lambda_ = -gravity[2] / (com.z - contact.z)
        self.lambda_max = lambda_max
        self.lambda_min = lambda_min
        if visible:
            self.show()
        else:  # not visible
            self.hide()

    def copy(self, visible=True):
        """
        Copy constructor.

        Parameters
        ----------
        visible : bool, optional
            Should the copy be visible?
        """
        return InvertedPendulum(
            self.com.p, self.com.pd, self.contact, visible=visible)

    def draw(self):
        """Draw inverted pendulum."""
        fulcrum = draw_point(self.cop, pointsize=0.01, color=self.color)
        leg = draw_line(self.com.p, self.cop, linewidth=4, color=self.color)
        self.handles = [fulcrum, leg]

    def hide(self):
        """Hide pendulum from the GUI."""
        self.com.hide()
        if self.handles:
            for handle in self.handles:
                handle.Close()
        self.is_visible = False

    def show(self):
        """Show pendulum in the GUI."""
        self.com.show()
        self.draw()
        self.is_visible = True

    def set_contact(self, contact):
        """
        Update the contact the pendulum rests upon.

        Parameters
        ----------
        contact : pymanoid.Contact
            New contact where CoPs can be realized.
        """
        self.contact = contact

    def set_cop(self, cop, clamp=None):
        """
        Update the CoP location on the contact surface.

        Parameters
        ----------
        cop : (3,) array
            New CoP location in the world frame.
        clamp : bool, optional
            Clamp CoP within the contact area if it lies outside. Overrides
            ``self.clamp``.
        """
        if (self.clamp if clamp is None else clamp):
            cop_local = dot(self.contact.R.T, cop - self.contact.p)
            if cop_local[0] >= self.contact.shape[0]:
                cop_local[0] = self.contact.shape[0] - 1e-5
            elif cop_local[0] <= -self.contact.shape[0]:
                cop_local[0] = -self.contact.shape[0] + 1e-5
            if cop_local[1] >= self.contact.shape[1]:
                cop_local[1] = self.contact.shape[1] - 1e-5
            elif cop_local[1] <= -self.contact.shape[1]:
                cop_local[1] = -self.contact.shape[1] + 1e-5
            cop = self.contact.p + dot(self.contact.R, cop_local)
        elif __debug__:
            cop_check = dot(self.contact.R.T, cop - self.contact.p)
            if abs(cop_check[0]) > 1.05 * self.contact.shape[0]:
                warn("CoP crosses contact area along sagittal axis")
            if abs(cop_check[1]) > 1.05 * self.contact.shape[1]:
                warn("CoP crosses contact area along lateral axis")
            if abs(cop_check[2]) > 0.01:
                warn("CoP does not lie on contact area")
        self.cop = cop

    def set_lambda(self, lambda_, clamp=None):
        """
        Update the leg stiffness coefficient.

        Parameters
        ----------
        lambda_ : scalar
            Leg stiffness coefficient (positive).
        clamp : bool, optional
            Clamp value if it exits the [lambda_min, lambda_max] interval.
            Overrides ``self.clamp``.
        """
        if (self.clamp if clamp is None else clamp):
            if self.lambda_min is not None and lambda_ < self.lambda_min:
                lambda_ = self.lambda_min
            if self.lambda_max is not None and lambda_ > self.lambda_max:
                lambda_ = self.lambda_max
        elif __debug__:
            if self.lambda_min is not None and lambda_ < self.lambda_min:
                warn("Stiffness %f below %f" % (lambda_, self.lambda_min))
            if self.lambda_max is not None and lambda_ > self.lambda_max:
                warn("Stiffness %f above %f" % (lambda_, self.lambda_max))
        self.lambda_ = lambda_

    def integrate(self, duration):
        """
        Integrate dynamics forward for a given duration.

        Parameters
        ----------
        duration : scalar
            Duration of forward integration.
        """
        omega = sqrt(self.lambda_)
        p0 = self.com.p
        pd0 = self.com.pd
        ch, sh = cosh(omega * duration), sinh(omega * duration)
        vrp = self.cop - gravity / self.lambda_
        p = p0 * ch + pd0 * sh / omega - vrp * (ch - 1.)
        pd = pd0 * ch + omega * (p0 - vrp) * sh
        self.com.set_pos(p)
        self.com.set_vel(pd)

    def on_tick(self, sim):
        """
        Integrate dynamics for one simulation step.

        Parameters
        ----------
        sim : pymanoid.Simulation
            Simulation instance.
        """
        self.integrate(sim.dt)
        if self.is_visible:
            self.draw()
