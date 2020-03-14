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

"""
This example applies an external force at the right hand of the JVRC-1 humanoid
while the robot is standing on its two feet. It illustrates how to use managed
contacts (external force provided by an independent process, here SoftContact)
in addition to the default supporting contacts.
"""

import IPython

import pymanoid

from pymanoid import Contact, PointMass, Stance
from pymanoid.gui import draw_polygon
from pymanoid.gui import RobotWrenchDrawer


class SoftContact(pymanoid.Process):

    """
    Model a simple elastic contact with a vertical surface.

    Parameters
    ----------
    contact : Contact
        Contact frame of the robot's end-effector.
    stiffness : scalar, optional
        Stiffness of the elastic surface.

    Attributes
    ----------
    contact : Contact
        Contact frame of the robot's end-effector.
    handle : openravepy.GraphHandle
        Polygon drawing to represent the elastic surface.
    init_y : scalar
        Position of the wall in the world frame.
    stiffness : scalar
        Stiffness of the elastic surface.
    """

    def __init__(self, contact, stiffness=2000.):
        super(SoftContact, self).__init__()
        x, y, z = contact.x, contact.y, contact.z
        polygon = [
            (x + 0.5, y, z - 0.5),
            (x + 0.5, y, z + 0.5),
            (x - 0.5, y, z + 0.5),
            (x - 0.5, y, z - 0.5)]
        self.contact = contact
        self.handle = draw_polygon(polygon, [0, 1, 0], color='k')
        self.init_y = y + 0.01
        self.stiffness = stiffness

    def on_tick(self, sim):
        """
        Update function run at every simulation tick.

        Parameters
        ----------
        sim : Simulation
            Instance of the current simulation.
        """
        F_z = max(0., self.stiffness * (self.init_y - self.contact.y))
        self.contact.set_wrench([0., 0., F_z, 0., 0., 0.])


if __name__ == "__main__":
    sim = pymanoid.Simulation(dt=0.03)
    robot = pymanoid.robots.JVRC1('JVRC-1.dae', download_if_needed=True)
    sim.set_viewer()
    sim.viewer.SetCamera([
        [0.2753152, 0.29704774, -0.91431077, 2.89042521],
        [0.96034717, -0.04146411, 0.27570643, -0.59789598],
        [0.04398688, -0.95396193, -0.29668466, 1.65848958],
        [0., 0., 0., 1.]])
    robot.set_transparency(0.25)

    stance = Stance(
        com=PointMass(
            pos=[0.1, 0.2, 0.9],
            mass=robot.mass),
        left_foot=Contact(
            shape=robot.sole_shape,
            friction=0.7,
            pos=[0.3, 0.39, 0.10],
            link=robot.left_foot,
            rpy=[0.15, 0., -0.02]),
        right_foot=Contact(
            shape=robot.sole_shape,
            friction=0.7,
            pos=[0., -0.15, 0.02],
            link=robot.right_foot,
            rpy=[-0.3, 0., 0.]),
        right_hand=Contact(
            shape=(0.04, 0.04),
            friction=0.5,
            pos=[0.1, -0.5, 1.2],
            rpy=[-1.57, 0., 0.]))
    stance.bind(robot)
    robot.ik.solve()

    soft_contact = SoftContact(stance.right_hand)
    wrench_drawer = RobotWrenchDrawer(robot)

    sim.schedule(robot.ik)
    sim.schedule(soft_contact)
    sim.schedule(robot.wrench_distributor, log_comp_times=True)
    sim.schedule_extra(wrench_drawer)
    sim.start()

    if IPython.get_ipython() is None:
        IPython.embed()
