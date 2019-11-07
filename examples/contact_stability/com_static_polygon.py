#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2019 Stephane Caron <stephane.caron@lirmm.fr>
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
This example computes the static-equilibrium CoM polygon, i.e. the set of CoM
positions that can be sustained usingf a given set of contacts. See [Caron16]_
for details.
"""

import IPython
import sys

import pymanoid

from pymanoid.gui import StaticEquilibriumWrenchDrawer
from pymanoid.gui import draw_polygon
from pymanoid.misc import norm


class SupportPolygonDrawer(pymanoid.Process):

    """
    Draw the static-equilibrium polygon of a contact set.

    Parameters
    ----------
    stance : pymanoid.Stance
        Contacts and COM position of the robot.
    method : string
        Method to compute the static equilibrium polygon. Choices are: 'bretl',
        'cdd' and 'hull'.
    z_polygon : scalar
        Height where to draw the CoM static-equilibrium polygon.
    color : tuple or string, optional
        Area color.
    """

    def __init__(self, stance, method, z_polygon, color='g'):
        if color is None:
            color = (0., 0.5, 0., 0.5)
        if type(color) is str:
            from pymanoid.misc import matplotlib_to_rgb
            color = matplotlib_to_rgb(color) + [0.5]
        super(SupportPolygonDrawer, self).__init__()
        self.color = color
        self.contact_poses = {}
        self.handle = None
        self.method = method
        self.stance = stance
        self.z = z_polygon
        #
        self.update_contact_poses()
        self.update_polygon()

    def clear(self):
        self.handle = None

    def on_tick(self, sim):
        if self.handle is None:
            self.update_polygon()
        for contact in self.stance.contacts:
            if norm(contact.pose - self.contact_poses[contact.name]) > 1e-10:
                self.update_contact_poses()
                self.update_polygon()
                break

    def update_contact_poses(self):
        for contact in self.stance.contacts:
            self.contact_poses[contact.name] = contact.pose

    def update_polygon(self):
        self.handle = None
        try:
            vertices = self.stance.compute_static_equilibrium_polygon(
                method=self.method)
            self.handle = draw_polygon(
                [(x[0], x[1], self.z) for x in vertices],
                normal=[0, 0, 1], color=self.color)
        except Exception as e:
            print("SupportPolygonDrawer: {}".format(e))

    def update_z(self, z):
        self.z = z
        self.update_polygon()


class COMSync(pymanoid.Process):

    """
    Update stance CoM from the GUI handle in polygon above the robot.

    Parameters
    ----------
    stance : pymanoid.Stance
        Contacts and COM position of the robot.
    com_above : pymanoid.Cube
        CoM handle in static-equilibrium polygon.
    """

    def __init__(self, stance, com_above):
        super(COMSync, self).__init__()
        self.com_above = com_above
        self.stance = stance

    def on_tick(self, sim):
        self.stance.com.set_x(self.com_above.x)
        self.stance.com.set_y(self.com_above.y)


if __name__ == "__main__":
    sim = pymanoid.Simulation(dt=0.03)
    robot = pymanoid.robots.JVRC1('JVRC-1.dae', download_if_needed=True)
    sim.set_viewer()
    sim.set_camera_top(x=0., y=0., z=3.)
    robot.set_transparency(0.25)

    z_polygon = 2.  # [m], height where to draw CoM polygon
    com_above = pymanoid.Cube(0.02, [0.05, 0.04, z_polygon], color='b')

    stance = pymanoid.Stance.from_json('stances/double.json')
    stance.com.hide()
    stance.bind(robot)
    robot.ik.solve()

    method = "hull"
    if "bretl" in sys.argv:
        method = "bretl"
    elif "cdd" in sys.argv:
        method = "cdd"

    com_sync = COMSync(stance, com_above)
    polygon_drawer = SupportPolygonDrawer(stance, method, z_polygon)
    wrench_drawer = StaticEquilibriumWrenchDrawer(stance)

    sim.schedule(robot.ik)
    sim.schedule_extra(com_sync)
    sim.schedule_extra(polygon_drawer)
    sim.schedule_extra(wrench_drawer)
    sim.start()

    print("""
COM static-equilibrium polygon
==============================

Method: %s

Ready to go! The GUI displays the COM static-equilibrium polygon in green. You
can move the blue box (in the plane above the robot) around to make the robot
move its center of mass. Contact wrenches are displayed at each contact (green
dot is COP location, arrow is resultant force). When the COM exits the
static-equilibrium polygon, you should see the background turn red as no
feasible contact wrenches can be found.

Enjoy :)
""" % method)

    if IPython.get_ipython() is None:
        IPython.embed()
