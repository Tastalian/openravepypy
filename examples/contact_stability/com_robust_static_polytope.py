#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2017 Hervé Audren <herve.audren@lirmm.fr>
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
This example computes the robust static-equilibrium CoM polyhedron. See
[Audren18]_ for details. Running this example requires the `StabiliPy
<https://github.com/haudren/stabilipy>`_ library.
"""

import IPython
import pymanoid
import sys

try:
    import stabilipy
except Exception:
    pymanoid.error("Running this example requires the StabiliPy library")
    print("You can get it from: https://github.com/haudren/stabilipy\n")
    sys.exit(-1)

from numpy import array, zeros
from pymanoid import Stance
from pymanoid.gui import PointMassWrenchDrawer
from pymanoid.gui import draw_polytope
from pymanoid.misc import matplotlib_to_rgb, norm
from openravepy import matrixFromPose


class SupportPolyhedronDrawer(pymanoid.Process):

    """
    Draw the robust static-equilibrium polyhedron of a contact set.

    Parameters
    ----------
    stance : Stance
        Contacts and COM position of the robot.
    color : tuple or string, optional
        Area color.
    method: string, optional
        Method to compute the static equilibrium polygon.
        Choices are cdd, qhull (default) and parma
    """

    def __init__(self, stance, z=0., color=None, method='qhull'):
        if color is None:
            color = (0., 0.5, 0., 0.5)
        if type(color) is str:
            color = matplotlib_to_rgb(color) + [0.5]
        super(SupportPolyhedronDrawer, self).__init__()
        self.color = color
        self.contact_poses = {}
        self.handle = None
        self.max_iter = 50
        self.method = method
        self.nr_iter = 0
        self.polyhedron = None
        self.stance = stance
        self.z = z
        #
        self.update_contacts()
        self.create_polyhedron(self.stance.contacts)

    def clear(self):
        self.handle = None

    def on_tick(self, sim):
        if self.handle is None:
            self.create_polyhedron(self.stance.contacts)
            return
        for contact in self.stance.contacts:
            if norm(contact.pose - self.contact_poses[contact.name]) > 1e-10:
                self.update_contacts()
                self.create_polyhedron(self.stance.contacts)
                return
        if self.nr_iter < self.max_iter:
            self.refine_polyhedron()
            self.nr_iter += 1

    def update_contacts(self):
        for contact in self.stance.contacts:
            self.contact_poses[contact.name] = contact.pose

    def create_polyhedron(self, contacts):
        self.handle = None
        self.nr_iter = 0
        try:
            self.polyhedron = stabilipy.StabilityPolygon(
                robot.mass, dimension=3, radius=1.5)
            stabilipy_contacts = []
            for contact in contacts:
                hmatrix = matrixFromPose(contact.pose)
                X, Y = contact.shape
                displacements = [array([[X, Y, 0]]).T,
                                 array([[-X, Y, 0]]).T,
                                 array([[-X, -Y, 0]]).T,
                                 array([[X, -Y, 0]]).T]
                for disp in displacements:
                    stabilipy_contacts.append(
                        stabilipy.Contact(
                            contact.friction,
                            hmatrix[:3, 3:] + hmatrix[:3, :3].dot(disp),
                            hmatrix[:3, 2:3]))
            self.polyhedron.contacts = stabilipy_contacts
            self.polyhedron.select_solver(self.method)
            self.polyhedron.make_problem()
            self.polyhedron.init_algo()
            self.polyhedron.build_polys()
            vertices = self.polyhedron.polyhedron()
            self.handle = draw_polytope(
                [(x[0], x[1], x[2]) for x in vertices])
        except Exception as e:
            print("SupportPolyhedronDrawer: {}".format(e))

    def refine_polyhedron(self):
        try:
            self.polyhedron.next_edge()
            vertices = self.polyhedron.polyhedron()
            self.handle = draw_polytope(
                [(x[0], x[1], x[2]) for x in vertices])
        except Exception as e:
            print("SupportPolyhedronDrawer: {}".format(e))

    def update_z(self, z):
        self.z = z
        self.update_polygon()


class StaticWrenchDrawer(PointMassWrenchDrawer):

    """
    Draw contact wrenches applied to a robot in static-equilibrium.

    Parameters
    ----------
    stance : Stance
        Contacts and COM position of the robot.
    """

    def __init__(self, stance):
        super(StaticWrenchDrawer, self).__init__(stance.com, stance)
        stance.com.set_accel(zeros((3,)))
        self.stance = stance

    def find_supporting_wrenches(self, sim):
        return self.stance.find_static_supporting_wrenches()


if __name__ == "__main__":
    sim = pymanoid.Simulation(dt=0.03)
    robot = pymanoid.robots.JVRC1('JVRC-1.dae', download_if_needed=True)
    sim.set_viewer()
    sim.viewer.SetCamera([
        [0.60587192, -0.36596244,  0.70639274, -2.4904027],
        [-0.79126787, -0.36933163,  0.48732874, -1.6965636],
        [0.08254916, -0.85420468, -0.51334199,  2.79584694],
        [0.,  0.,  0.,  1.]])
    robot.set_transparency(0.25)

    stance = Stance.from_json('stances/double.json')
    stance.bind(robot)
    robot.ik.solve()

    polygon_drawer = SupportPolyhedronDrawer(stance)
    wrench_drawer = StaticWrenchDrawer(stance)

    sim.schedule(robot.ik)
    sim.schedule_extra(polygon_drawer)
    sim.schedule_extra(wrench_drawer)
    sim.start()

    print("""
COM robust static-equilibrium polygon
=====================================

Ready to go! The GUI displays the COM static-equilibrium polytope in green. You
can move contacts around to see how they affect the shape of the polytope.
Sample contact wrenches are displayed at each contact (green dot is COP
location, arrow is resultant force).

Enjoy :)
""")

    if IPython.get_ipython() is None:
        IPython.embed()
