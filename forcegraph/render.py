"""
Render
"""

import sys
import time

from collections import defaultdict

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation

from matplotlib.patches import Circle
from matplotlib.lines import Line2D

DEBUG = True

class Node(object):
    def __init__(self, i, posi, static, mass, theta=None):
        self.i = i
        self.pos = posi
        self.theta = theta
        self.v = np.zeros(2, dtype=np.float)
        self.mass = mass
        self.static = static

    def __repr__(self):
        return repr(self.pos)


class Force(object):
    def get_force(self, node0, node1, d):
        return NotImplemented


#class Gravity(Force):
#    def __init__(self, G):
#        self.G = G
#
#    def get_force(self, node0, node1, d):
#        n = max(np.linalg.norm(d), 0.01)
#        return self.G * node0.mass * node1.mass * d / n ** 3


class Spring(Force):
    def __init__(self, K, l0):
        self.K = K
        self.l0 = l0

    def get_force(self, node0, node1, d):
        n = np.linalg.norm(d)
        if not self.l0:
            return self.K * d
        if n < 0.01:
            return d * 0
        return self.K * (d / n) * (n - self.l0)


class Render(object):
    def __init__(self, T=0.2, f=1e2):
        self.nodes = {}
        self.lines = {}
        self.forces = defaultdict(list)
        # constants
        self.T = T
        self.f = f
        self.m = 1e5
        # create plot
        self.fig = plt.figure()
        self.ax = self.fig.add_axes([0, 0, 1, 1], frameon=False)
        self.ax.set_ylim((0, 1))
        self.ax.set_xlim((0, 1))
        self.points = None
        self.lines2d = {}
        # radius mode
        self.radius = None
        self.center = np.array((0.5, 0.5))

    @property
    def nodes_length(self):
        return len(self.nodes.values())

    def set_radius(self, radius, center=None):
        self.radius = radius
        if center:
            self.center = center

    def load(self, init):
        # Center point
        self.add_node(0, pos=self.center, static=True)
        init(self)
        self.nodes_ar = np.zeros((self.nodes_length, 2))
        # Initialize first frame and plot
        self.next_frame()
        self.points = self.ax.scatter(self.nodes_ar[:,0],
                                      self.nodes_ar[:,1],
                                      s=50)
        for line, dat in self.lines.items():
            x, y, kwargs = dat
            line2d = Line2D(x, y, **kwargs)
            self.lines2d[line] = line2d
            self.ax.add_line(line2d)
        # Add extras
        if self.radius:
            self.ax.add_artist(Circle(self.center, self.radius, fill=False,
                                      linestyle="--"))

    def add_force(self, node0, node1, force):
        id = self.nmlz(node0.i, node1.i)
        self.forces[id].append(force)
        if DEBUG:
            kwargs = {}
            kwargs["linestyle"] = "-."
            kwargs["color"] = "green"
            self.link(node0, node1, kwargs)

    def add_node(self, i, pos=None, theta=None,
                 link_to=None, mass=None, static=False, lcenter=True):
        if pos is None and theta is None:
            theta = np.random.rand()
        if pos is None and theta is not None:
            r = self.radius
            pos = self.center + np.array((r * np.cos(theta), r * np.sin(theta)))
        node = Node(i, pos, static, mass or self.m, theta=theta)
        if i in self.nodes:
            raise ValueError("Index already present")
        self.nodes[i] = node
        if link_to:
            self.link(node, link_to)
        return node

    def nmlz(self, i, j):
        return tuple(sorted([i, j]))

    def link(self, a, b, kwargs={}):
        id = self.nmlz(a.i, b.i)
        self.lines[id] = (0,0, kwargs)

    def force_on(self, node0):
        F = np.zeros(2, dtype=np.float)
        for node in self.nodes.values():
            id = self.nmlz(node0.i, node.i)
            for force in self.forces[id]:
                d = node.pos - node0.pos
                f = force.get_force(node, node0, d)
                #print(force.__class__.__name__ + str(f))
                F += f
        # Frottements
        fr = - node.v * self.f
        #print("f: %s" % fr)
        F += fr
        return F

    def next_frame(self):
        new_values = {}
        for i, node in self.nodes.items():
            if node.static:
                new_values[i] = (node.pos, node.v)
                continue
            # Get next position of node
            F = self.force_on(node)
            if self.radius:
                r = self.radius
                t = node.theta
                F_theta = -F[0] * np.sin(t) + F[1] * np.cos(t)
                dv = F_theta * self.T / node.mass
                v = np.array((node.v[0], node.v[1] + dv))
                theta = node.theta = node.theta + dv / r
                pos = self.center + np.array((r * np.cos(theta), r * np.sin(theta)))
            else:
                v = node.v + F * self.T / node.mass
                pos = node.pos + v * self.T
            new_values[i] = (pos, v)
        # Apply new positions
        for i in self.nodes:
            self.nodes_ar[i,:] = self.nodes[i].pos = new_values[i][0]
            self.nodes[i].v = new_values[i][1]
        for line in self.lines:
            x = [self.nodes_ar[line[0],0], self.nodes_ar[line[1],0]]
            y = [self.nodes_ar[line[0],1], self.nodes_ar[line[1],1]]
            self.lines[line] = (x, y, self.lines[line][2])
    
    def draw_frame(self, t=0):
        self.next_frame()
        self.points.set_offsets(self.nodes_ar)
        for line, dat in self.lines.items():
            x, y, _ = dat
            self.lines2d[line].set_data(x, y)
        #print(self.nodes_ar)

def animate(init):
    render = Render()
    render.load(init)
    
    ani = animation.FuncAnimation(
        render.fig,
        render.draw_frame,
        interval=1,
        blit=False
    )
    plt.show()
