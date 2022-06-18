import os
from functools import cmp_to_key
from itertools import zip_longest
import numpy as np
import matplotlib as mpl
import matplotlib.patches as patches
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider
from matplotlib.widgets import TextBox
from matplotlib.widgets import Button
import prettytable
import textwrap
import threading
import tkinter as tk
import tkinter.ttk as ttk
from tkinter.font import Font
from dominate.tags import *
from dominate.util import raw
from markdownify import markdownify

from .common import diagram_log
from .statistics import IdManager
from .statistics import EventDataSet


def draw_line(ax, text, pos, scale=1.0, color="k"):
    tp = mpl.textpath.TextPath((0.0, 0.0), text, size=1)

    verts = []
    for vert in tp.vertices:
        vx = vert[0] * scale + pos[0]
        vy = vert[1] * scale + pos[1]
        verts += [[vx, vy]]
    verts = np.array(verts)

    tp = mpl.path.Path(verts, tp.codes)
    ax.add_patch(mpl.patches.PathPatch(tp, facecolor=color, lw=0))


def draw_label(ax, text, pos, letter_n, line_h, margin=0.05, color="k"):
    text_blocks = text.splitlines()
    line_list = []
    for text_block in text_blocks:
        line_list.extend(textwrap.wrap(text_block, letter_n))
    if ax is None:
        return len(line_list) * line_h + margin / 1.8 * 2
    x = pos[0] + margin
    y = pos[1] - margin / 1.8
    for s in line_list:
        y -= line_h
        draw_line(ax, s, pos=(x, y), scale=0.2, color=color)


def draw_rectangle(ax, p, w, h, label, w_scale=0.2, color="w"):
    letter_n = int(w / w_scale * 1.8)  # maximum number of letters in one line
    line_h = w_scale  # height of line
    label_h = draw_label(None, label, None, letter_n, line_h)
    if ax is None:
        return label_h
    r = patches.Rectangle(
        xy=p, width=w, height=h, ec="k", fc=color, fill=True, label=label
    )
    ax.add_patch(r)
    r.set_picker(True)
    if ax is not None:
        rx, ry = r.get_xy()
        draw_label(ax, label, (rx, ry + r.get_height()), letter_n, line_h)
    return r


def draw_connector(ax, p1, p2):
    width = 0.01
    head_width = 0.08
    head_length = 0.10
    color = "grey"
    center_x = (p1[0] + p2[0]) / 2.0
    center_y = (p1[1] + p2[1]) / 2.0
    pa = [p1[0], center_y]
    pb = [p2[0], center_y]
    ax.arrow(
        x=p1[0],
        y=p1[1],
        dx=pa[0] - p1[0],
        dy=pa[1] - p1[1],
        width=width,
        head_width=0.0,
        head_length=0.0,
        length_includes_head=True,
        color=color,
    )
    ax.arrow(
        x=pa[0],
        y=pa[1],
        dx=pb[0] - pa[0],
        dy=pb[1] - pa[1],
        width=width,
        head_width=0.0,
        head_length=0.0,
        length_includes_head=True,
        color=color,
    )
    ax.arrow(
        x=pb[0],
        y=pb[1],
        dx=p2[0] - pb[0],
        dy=p2[1] - pb[1],
        width=width,
        head_width=head_width,
        head_length=head_length,
        length_includes_head=True,
        color=color,
    )


class TreeNode:
    def __init__(self, label, name=None, wh=(1, 0.75)):
        if name is not None:
            self.name = name
        else:
            self.name = label
        self.label = label
        self.p_global = None  # x and y coordinates in the frame of root node
        self.rect_global = None
        self.rect = [
            -wh[0] / 2.0,
            -wh[1],
            wh[0],
            wh[1],
        ]  # height is fitted to label text
        self.parent = None
        self.child_statnode = None
        self.child_p = None  # coordinates of child nodes
        self.margin_left = 0.2
        self.margin_right = 0.2
        self.y_distance = 0.5
        self.branch_style = "center"
        # x coordinate of left edge of the rectangle surrounding child nodes
        self.left_x = None
        # x coordinate of right edge of the rectangle surrounding child nodes
        self.right_x = None
        self.attr_list = ["pick_process"]
        for attr in self.attr_list:
            self.__dict__[attr] = None
        self.statnode_id = None  # anchor id
        self.statnode_id_detail = []
        self.level = None

    def set_process(self, func, attr_name):
        if attr_name in self.attr_list:
            self.__dict__[attr_name] = func
        else:
            raise ValueError("not valid attr name: {}".format(attr_name))

    def set_branch(self, statnode_list, branch_style="center"):
        self.child_statnode = statnode_list
        self.branch_style = branch_style  # left, right, center

    def _pos_translation(self, frame1_p, frame1_p0, frame2_p0):
        # calculate coordinates in frame2 when frame1_p0 = frame2_p0
        return [
            frame1_p[0] - frame1_p0[0] + frame2_p0[0],
            frame1_p[1] - frame1_p0[1] + frame2_p0[1],
        ]

    def _change_frame(self, frame1_p, frame1_p0, frame2_p0):
        # translate coordinates in frame1 to coordinates in frame2
        return [
            frame1_p[0] + frame1_p0[0] - frame2_p0[0],
            frame1_p[1] + frame1_p0[1] - frame2_p0[1],
        ]

    def _update_annot_label(self, pos, label):
        self.annot.xy = pos
        text = label
        self.annot.set_text(text)

    def _hover_rect(self, event):
        for rect, info in self.rect_dict.items():
            cont, ind = rect.contains(event)
            if cont:
                self._update_annot_label(info[0], info[2])
                self.annot.set_visible(True)
                self._draw()
                return True
        return False

    def _hover(self, event):
        vis = self.annot.get_visible()
        if event.inaxes == self.ax:
            if not (self._hover_rect(event)):
                if vis:
                    self.annot.set_visible(False)
                    self._draw()

    def _draw(self):
        self.fig.canvas.draw_idle()

    def _pick(self, event):
        r = event.artist
        if isinstance(r, patches.Rectangle):
            info = self.rect_dict[r]
            if self.pick_process is not None:
                self.pick_process(info[3])
                return True
        return False

    def draw_all(self, fig=None, ax=None, equal_arrange=True):
        # initialize
        self._clear_area([])
        # arrange nodes
        self._calc_area([], equal_arrange)
        self._calc_p([])
        layer_h = []
        self._get_layer_y_pos([], layer_h)
        layer_p = [0] * len(layer_h)
        current_p = 0
        for i in range(len(layer_h) - 1):
            current_p -= layer_h[i]
            layer_p[i + 1] = current_p
        self._update_p([], layer_p)
        # draw diagram
        self.rect_dict = {}
        self.draw([], ax, self.rect_dict)
        if fig is None or ax is None:
            return
        # annotation
        self.annot = ax.annotate(
            "",
            xy=(0, 0),
            xytext=(20, 20),
            textcoords="offset points",
            bbox=dict(boxstyle="round", fc="w"),
            arrowprops=dict(arrowstyle="->"),
        )
        self.fig = fig
        self.ax = ax
        self.annot.set_visible(False)
        # set event handlers
        fig.canvas.mpl_connect("motion_notify_event", self._hover)
        fig.canvas.mpl_connect("pick_event", self._pick)

    def make_label(self):
        return ""

    def print(self):
        return

    def draw(self, statnode_stack, ax=None, rect_dict=None):
        # loop check
        if self in statnode_stack:
            raise ValueError("loop connection")
        self.level = len(statnode_stack)
        if self.level == 0:
            # initialize
            self.statnode_id = ""
            self.statnode_id_detail.clear()
        statnode_stack.append(self)
        self.rect_global = [
            self.p_global[0] + self.rect[0],
            self.p_global[1] + self.rect[1],
            self.rect[2],
            self.rect[3],
        ]
        label = self.make_label()
        condition_miss = self._check_condition_miss()
        if ax is not None:
            rect_color = "y" if condition_miss else "w"
            r = draw_rectangle(
                ax,
                self.rect_global[0:2],
                self.rect_global[2],
                self.rect_global[3],
                label,
                color=rect_color,
            )
            if rect_dict is not None:
                rect_dict[r] = (
                    (
                        self.rect_global[0] + self.rect_global[2],
                        self.rect_global[1] + self.rect_global[3],
                    ),
                    self.name,
                    label,
                    self,
                )
        else:
            print("label={}".format(label))
            self.print()

        if self.child_statnode is not None:
            for idx, child in enumerate(self.child_statnode):
                child.parent = self
                child.statnode_id = "{}_{}".format(self.statnode_id, idx)
                child.statnode_id_detail.clear()
                child.statnode_id_detail.extend(self.statnode_id_detail)
                child.statnode_id_detail.append(idx)
                # draw child recursively
                child.draw(statnode_stack, ax, rect_dict)
                if ax is not None:
                    bottom_p = [self.p_global[0], self.p_global[1] - self.rect[3]]
                    draw_connector(ax, bottom_p, child.p_global)
        statnode_stack.pop()

    # calculate p_global
    def _calc_p(self, statnode_stack):
        # loop check
        if self in statnode_stack:
            raise ValueError("loop connection")
        statnode_stack.append(self)
        if len(statnode_stack) == 1:
            self.p_global = [0, 0]
        if self.child_statnode is None:
            statnode_stack.pop()
            return
        diagram_log.debug("name={}".format(self.name))
        for i, child in enumerate(self.child_statnode):
            child_p = self.child_p[i]  # position of a child in the frame of parent node
            diagram_log.debug("child.child_p={}".format(child_p))
            child.p_global = self._pos_translation(child_p, [0, 0], self.p_global)
            child._calc_p(statnode_stack)
        statnode_stack.pop()

    def _get_layer_y_pos(self, statnode_stack, layer_h):  # update rect and get y pos
        # loop check
        if self in statnode_stack:
            raise ValueError("loop connection")
        statnode_stack.append(self)
        # extend layer_h
        layer_n = len(statnode_stack)
        layer_h_n = len(layer_h)
        if layer_h_n < layer_n:
            layer_h.extend([0] * (layer_n - layer_h_n))

        this_w = self.rect[2]
        label = self.make_label()
        rect_h = draw_rectangle(None, None, this_w, None, label)
        rect_h = max(rect_h, self.rect[3])
        self.rect[1] = -rect_h  # y coordinate of bottom edge
        self.rect[3] = rect_h  # height
        # update y coordinate
        layer_h[layer_n - 1] = max(layer_h[layer_n - 1], rect_h + self.y_distance)
        if self.child_statnode is None:
            statnode_stack.pop()
            return
        diagram_log.debug("name={}".format(self.name))
        for i, child in enumerate(self.child_statnode):
            child_p = self.child_p[i]
            diagram_log.debug("child.child_p={}".format(child_p))
            child._get_layer_y_pos(statnode_stack, layer_h)
        statnode_stack.pop()

    def _update_p(self, statnode_stack, layer_p):
        # loop check
        if self in statnode_stack:
            raise ValueError("loop connection")
        statnode_stack.append(self)
        layer_n = len(statnode_stack)
        # set y coordinate of this node in the frame of root node
        self.p_global[1] = layer_p[layer_n - 1]
        if self.child_statnode is None:
            statnode_stack.pop()
            return
        diagram_log.debug("name={}".format(self.name))
        for i, child in enumerate(self.child_statnode):
            child_p = self.child_p[i]
            diagram_log.debug("child.child_p={}".format(child_p))
            child._update_p(statnode_stack, layer_p)
        statnode_stack.pop()

    def _clear_area(self, statnode_stack):
        # loop check
        if self in statnode_stack:
            raise ValueError("loop connection")
        statnode_stack.append(self)
        if self.child_statnode is not None:
            for child in self.child_statnode:
                child._clear_area(statnode_stack)
        # clear area parameters
        self.left_x = None
        self.right_x = None
        statnode_stack.pop()

    def _stack_left(self, statnode, left_boundary=None, right_boundary=None):
        if right_boundary is None or left_boundary is None:
            new_left_boundary = statnode.left_x
            new_right_boundary = statnode.right_x
            statnode_p_x = 0
            return statnode_p_x, new_left_boundary, new_right_boundary

        p_x_list = []
        for boundary_x, left_x in zip(right_boundary, statnode.left_x):
            p_x_list.append(boundary_x - left_x)
        statnode_p_x = max(p_x_list)

        new_left_boundary = []
        for boundary_x, left_x in zip_longest(left_boundary, statnode.left_x):
            if boundary_x is None:
                new_left_boundary.append(statnode_p_x + left_x)
                continue
            new_left_boundary.append(boundary_x)

        new_right_boundary = []
        for boundary_x, right_x in zip_longest(right_boundary, statnode.right_x):
            if right_x is None:
                new_right_boundary.append(boundary_x)
                continue
            new_right_boundary.append(statnode_p_x + right_x)
        return statnode_p_x, new_left_boundary, new_right_boundary

    def _shift_boundary(self, boundary, shift_x):
        new_boundary = []
        for boundary_x in boundary:
            new_boundary.append(boundary_x + shift_x)
        return new_boundary

    def _make_boundary(self, child_p, child, left_boundary=None, right_boundary=None):
        diagram_log.debug("child.left_x = {}".format(child.left_x))
        diagram_log.debug("child.right_x = {}".format(child.right_x))
        new_left_boundary_tmp = self._shift_boundary(child.left_x, child_p[0])
        new_right_boundary_tmp = self._shift_boundary(child.right_x, child_p[0])
        diagram_log.debug("new_left_boundary_tmp = {}".format(new_left_boundary_tmp))
        diagram_log.debug("new_right_boundary_tmp = {}".format(new_right_boundary_tmp))
        if right_boundary is None or left_boundary is None:
            return new_left_boundary_tmp, new_right_boundary_tmp

        new_left_boundary = []
        for boundary_x, left_x in zip_longest(left_boundary, new_left_boundary_tmp):
            if boundary_x is None:
                new_left_boundary.append(left_x)
                continue
            if left_x is None:
                new_left_boundary.append(boundary_x)
                continue
            new_left_boundary.append(min(boundary_x, left_x))

        new_right_boundary = []
        for boundary_x, right_x in zip_longest(right_boundary, new_right_boundary_tmp):
            if boundary_x is None:
                new_right_boundary.append(right_x)
                continue
            if right_x is None:
                new_right_boundary.append(boundary_x)
                continue
            new_right_boundary.append(max(boundary_x, right_x))
        return new_left_boundary, new_right_boundary

    def _calc_area(self, statnode_stack, equal_arrange=True):
        if self.left_x is not None or self.right_x is not None:
            return
        if self.child_statnode is None:
            # add margin
            self.left_x = [self.rect[0] - self.margin_left]
            self.right_x = [self.rect[0] + self.rect[2] + self.margin_right]
            return
        # loop check
        if self in statnode_stack:
            raise ValueError("loop connection")
        statnode_stack.append(self)
        # calculate areas of child nodes
        for child in self.child_statnode:
            child._calc_area(statnode_stack, equal_arrange)
        child_statnode_len = len(self.child_statnode)
        if child_statnode_len == 1:
            # only one child node
            child = self.child_statnode[0]
            # set the child under the parent
            child_p = [0, -self.rect[3] - self.y_distance]
            self.child_p = [child_p]
            # update x coordinate of the rectangle surrounding the child node
            self.left_x = [self.rect[0] - self.margin_left]
            self.right_x = [self.rect[0] + self.rect[2] + self.margin_right]
            self.left_x.extend(child.left_x)
            self.right_x.extend(child.right_x)
            statnode_stack.pop()
            return
        # child nodes
        self.child_p = []
        left_boundary = None
        right_boundary = None
        for child in self.child_statnode:
            statnode_p_x, left_boundary, right_boundary = self._stack_left(
                child, left_boundary, right_boundary
            )
            self.child_p.append([statnode_p_x, 0])
        child_p_distance = []
        for i, child in enumerate(self.child_statnode):
            if i == 0:
                continue
            child_p_distance.append(self.child_p[i][0] - self.child_p[i - 1][0])
        max_child_p_distance = max(child_p_distance)
        # arrange the child nodes at equal intervals
        if equal_arrange:
            for i, child in enumerate(self.child_statnode):
                self.child_p[i] = [max_child_p_distance * i, 0]
        diagram_log.debug("self.child_p={}".format(self.child_p))
        # set coordinates of this node
        if self.branch_style == "center":
            this_p = [
                (self.child_p[0][0] + self.child_p[-1][0]) / 2.0,
                +self.rect[3] + self.y_distance,
            ]
        if self.branch_style == "left":
            this_p = [
                self.child_p[0][0],
                +self.rect[3] + self.y_distance,
            ]
        if self.branch_style == "right":
            this_p = [
                self.child_p[-1][0],
                +self.rect[3] + self.y_distance,
            ]
        diagram_log.debug("this_p={}".format(this_p))
        # calculate coordinates of the child nodes in the frame of this node
        for i, child in enumerate(self.child_statnode):
            diagram_log.debug("from self.child_p[{}]={}".format(i, self.child_p[i]))
            self.child_p[i] = self._change_frame(self.child_p[i], [0, 0], this_p)
            diagram_log.debug("to self.child_p[{}]={}".format(i, self.child_p[i]))
        left_boundary = None
        right_boundary = None
        for i, child in enumerate(self.child_statnode):
            left_boundary, right_boundary = self._make_boundary(
                self.child_p[i], child, left_boundary, right_boundary
            )
            diagram_log.debug("left_boundary = {}".format(left_boundary))
            diagram_log.debug("right_boundary = {}".format(right_boundary))
        # update x coordinate of the rectangle surrounding the child nodes
        self.left_x = [self.rect[0] - self.margin_left]
        self.right_x = [self.rect[0] + self.rect[2] + self.margin_right]
        self.left_x.extend(left_boundary)
        self.right_x.extend(right_boundary)
        statnode_stack.pop()
        return


class StatNode(TreeNode):
    def __init__(self, label, name=None, wh=(1, 0.75), condition=None):
        super().__init__(label, name, wh)
        self.condition = condition
        self.event_data_set_stop = EventDataSet()
        self.event_data_set_inbound = EventDataSet()
        self._self_clear_count()

    def make_label(self):
        return "{},\nI={}, S={}".format(self.label, self.inbound, self.stop)

    def _check_condition_miss(self):
        if self.child_statnode is None:
            return False
        return self.stop > 0

    def print(self, count_type="stop"):
        if count_type == "stop":
            event_data_set = self.event_data_set_stop
        if count_type == "inbound":
            event_data_set = self.event_data_set_inbound
        event_data_set.print()

    def _get_node_main(self, name, statnode_list, statnode_stack):
        # loop check
        if self in statnode_stack:
            raise ValueError("loop connection")
        diagram_log.debug("get_node: name = {}".format(self.name))
        if name is None or self.name == name:
            # collect nodes which has the specified name.
            statnode_list.append(self)
        if self.child_statnode is None:
            return
        statnode_stack.append(self)
        for child in self.child_statnode:
            child._get_node_main(name, statnode_list, statnode_stack)
        statnode_stack.pop()

    def _get_node(self, name):
        statnode_list = []
        self._get_node_main(name, statnode_list, [])
        return statnode_list

    def __call__(self, name):
        statnode_list = self._get_node(name)
        if len(statnode_list) > 0:
            return statnode_list[0]
        else:
            return None

    def event_eval(self, event_log, count_type="stop", ignore_error=True):
        if count_type == "stop":
            event_data_set = self.event_data_set_stop
        if count_type == "inbound":
            event_data_set = self.event_data_set_inbound
        event_data_eval = []
        eval_error_data_info = []
        eval_error_detail = []
        if event_data_set is None:
            return event_data_eval, []
        for event_data_info in event_data_set.get_event_data_info_list():
            try:
                event_data_eval.append(event_log.eval(event_data_info, ignore_error))
            except ValueError as e:
                eval_error_data_info.append(event_data_info)
                eval_error_detail.append(e)
        eval_error = zip(eval_error_data_info, eval_error_detail)
        return event_data_eval, eval_error

    def get_event_data_set(self, count_type="stop"):
        event_data_set = None
        if count_type == "stop":
            event_data_set = self.event_data_set_stop
        if count_type == "inbound":
            event_data_set = self.event_data_set_inbound
        if event_data_set is None:
            return EventDataSet()
        return event_data_set

    def set_condition(self, condition):
        self.condition = condition

    def add_event_data_info(self, event_data_info, count_type="stop"):
        if count_type == "stop":
            self.event_data_set_stop.add_event_data_info(event_data_info)
            return
        if count_type == "inbound":
            self.event_data_set_inbound.add_event_data_info(event_data_info)
            return

    def _self_clear_count(self):
        self.inbound = 0
        self.stop = 0
        if self.event_data_set_inbound is not None:
            self.event_data_set_inbound.clear()
        if self.event_data_set_stop is not None:
            self.event_data_set_stop.clear()

    def _clear_count_main(self, statnode_stack):
        # loop check
        if self in statnode_stack:
            raise ValueError("loop connection")
        statnode_stack.append(self)
        if self.child_statnode is not None:
            for child in self.child_statnode:
                child._clear_count_main(statnode_stack)
        # clear
        self._self_clear_count()
        statnode_stack.pop()

    def clear_count(self):
        self._clear_count_main([])

    def _send_main(self, event_data_info, statnode_stack, ignore_error):
        # loop check
        if self in statnode_stack:
            raise ValueError("loop connection")
        statnode_stack.append(self)
        send_statnode = None
        self.inbound = self.inbound + 1
        self.add_event_data_info(event_data_info, "inbound")
        if self.child_statnode is None:
            self.stop = self.stop + 1
            statnode_stack.pop()
            return self

        for child in reversed(self.child_statnode):
            if child.condition is None:
                continue
            if child.condition.is_true(event_data_info, ignore_error):
                # send events to child nodes recursively
                send_statnode = child._send_main(
                    event_data_info, statnode_stack, ignore_error
                )
                break
        statnode_stack.pop()
        if send_statnode is None:
            self.stop = self.stop + 1
            return self
        else:
            return send_statnode

    def send(self, event_data_info, ignore_error=True):
        send_statnode = self._send_main(event_data_info, [], ignore_error)
        send_statnode.add_event_data_info(event_data_info)


class PanZoomFigure:
    def __init__(self):
        self.ax = None
        self.fig = None
        self.base_scale = 2.0
        self.fig_scale = 0.08
        self._pressed_button = None
        self._event = None

    def _draw(self):
        self.fig.canvas.draw_idle()

    def _zoom(self, event):
        cur_xlim = self.ax.get_xlim()
        cur_ylim = self.ax.get_ylim()
        cur_xrange = (cur_xlim[1] - cur_xlim[0]) * 0.5
        cur_yrange = (cur_ylim[1] - cur_ylim[0]) * 0.5
        xdata = event.xdata  # get event x location
        ydata = event.ydata  # get event y location
        if event.button == "up":
            scale_factor = 1 / self.base_scale
        elif event.button == "down":
            scale_factor = self.base_scale
        else:
            scale_factor = 1
            print(event.button)
        # set new limits
        self.ax.set_xlim(
            [xdata - cur_xrange * scale_factor, xdata + cur_xrange * scale_factor]
        )
        self.ax.set_ylim(
            [ydata - cur_yrange * scale_factor, ydata + cur_yrange * scale_factor]
        )
        self._draw()

    def _pan_update_limits(self, axis_id, event, last_event):
        assert axis_id in (0, 1)
        if axis_id == 0:
            lim = self.ax.get_xlim()
        else:
            lim = self.ax.get_ylim()

        pixel_to_data = self.ax.transData.inverted()
        data = pixel_to_data.transform_point((event.x, event.y))
        last_data = pixel_to_data.transform_point((last_event.x, last_event.y))

        delta = data[axis_id] - last_data[axis_id]
        new_lim = lim[0] - delta, lim[1] - delta
        return new_lim

    def _pan(self, event):
        if event.name == "button_press_event":  # begin pan
            self._event = event

        elif event.name == "button_release_event":  # end pan
            self._event = None

        elif event.name == "motion_notify_event":  # pan
            if self._event is None:
                return

            if event.x != self._event.x:
                xlim = self._pan_update_limits(0, event, self._event)
                self.ax.set_xlim(xlim)

            if event.y != self._event.y:
                ylim = self._pan_update_limits(1, event, self._event)
                self.ax.set_ylim(ylim)

            if event.x != self._event.x or event.y != self._event.y:
                self._draw()

            self._event = event

    def _on_mouse_press(self, event):
        if self._pressed_button is not None:
            return

        if event.button in (1, 3):
            self._pressed_button = event.button

            if self._pressed_button == 3:  # pan
                self._pan(event)

    def _on_mouse_release(self, event):
        if self._pressed_button == event.button:
            if self._pressed_button == 3:  # pan
                self._pan(event)
            self._pressed_button = None

    def _on_mouse_motion(self, event):
        if self._pressed_button == 3:  # pan
            self._pan(event)

    def init_figure(self):
        self.fig.canvas.mpl_connect("scroll_event", self._zoom)
        self.fig.canvas.mpl_connect("button_press_event", self._on_mouse_press)
        self.fig.canvas.mpl_connect("button_release_event", self._on_mouse_release)
        self.fig.canvas.mpl_connect("motion_notify_event", self._on_mouse_motion)
        self.fig.subplots_adjust(
            left=0.0, bottom=0.0, right=1.0, top=1.0, wspace=None, hspace=None
        )


class MainWindow:
    def __init__(self, tk_win):
        self.tk_win = tk_win
        self.name_txt = None
        self.type_txt = None
        self.desc_txt = None
        self.create()

    def create(self):
        def press_OK():
            pass

        if self.tk_win is None:
            raise ValueError("tk must be set")

        self.tk_win.title("Infomation")
        self.tk_win.minsize(100, 100)
        self.tk_win.columnconfigure(0, weight=1)
        self.tk_win.rowconfigure(0, weight=1)

        # Frame
        frame1 = ttk.Frame(self.tk_win, padding=10)
        frame1.rowconfigure(1, weight=1)
        frame1.columnconfigure(0, weight=1)
        frame1.grid(sticky=(tk.N, tk.W, tk.S, tk.E))

        # Font
        f = Font(family="Courier", size=10)

        # name Text
        name_txt = tk.Text(frame1, height=1, width=20)
        name_txt.configure(font=f)
        name_txt.grid(row=0, column=0, sticky=(tk.N, tk.W, tk.E))
        name_txt.configure(state="disabled")

        # type Text
        type_txt = tk.Text(frame1, height=1, width=20)
        type_txt.configure(font=f)
        type_txt.grid(row=0, column=1, sticky=(tk.N, tk.W, tk.E))
        type_txt.configure(state="disabled")

        # Button
        button1 = ttk.Button(frame1, text="OK", command=press_OK)
        button1.grid(row=0, column=2, columnspan=2, sticky=(tk.N, tk.E))

        # description Text
        desc_txt = tk.Text(frame1, height=15, width=70)
        desc_txt.configure(font=f)
        desc_txt.grid(row=1, column=0, columnspan=3, sticky=(tk.N, tk.W, tk.S, tk.E))
        desc_txt.configure(state="disabled")

        # Scrollbar
        scrollbar = ttk.Scrollbar(frame1, orient=tk.VERTICAL, command=desc_txt.yview)
        desc_txt["yscrollcommand"] = scrollbar.set
        scrollbar.grid(row=1, column=3, sticky=(tk.N, tk.S))

        self.name_txt = name_txt
        self.type_txt = type_txt
        self.desc_txt = desc_txt

    def set_title(self, txt):
        self.tk_win.title(txt)

    def set_name(self, txt):
        tk_text = self.name_txt
        tk_text.configure(state="normal")
        tk_text.delete("1.0", tk.END)
        tk_text.insert(tk.END, txt)
        tk_text.configure(state="disabled")

    def set_type(self, txt):
        tk_text = self.type_txt
        tk_text.configure(state="normal")
        tk_text.delete("1.0", tk.END)
        tk_text.insert(tk.END, txt)
        tk_text.configure(state="disabled")

    def set_desc(self, txt):
        tk_text = self.desc_txt
        tk_text.configure(state="normal")
        tk_text.delete("1.0", tk.END)
        tk_text.insert(tk.END, txt)
        tk_text.configure(state="disabled")


class DiagramWindow(PanZoomFigure):
    def __init__(self, root_node):
        self.root_node = root_node
        super().__init__()

    def adjust_figure_size(self, root_node):
        x_margin = 75
        y_margin = 25
        statnode_list = root_node._get_node(None)
        pos_x = [statnode.rect_global[0] for statnode in statnode_list]
        pos_x.extend(
            [
                statnode.rect_global[0] + statnode.rect_global[2]
                for statnode in statnode_list
            ]
        )
        pos_y = [statnode.rect_global[1] for statnode in statnode_list]
        pos_y.extend(
            [
                statnode.rect_global[1] + statnode.rect_global[3]
                for statnode in statnode_list
            ]
        )
        x_min = min(pos_x) - x_margin
        x_max = max(pos_x) + x_margin
        y_min = min(pos_y) - y_margin
        y_max = max(pos_y) + y_margin
        fig_width = (x_max - x_min) * self.fig_scale
        fig_height = (y_max - y_min) * self.fig_scale
        self.fig.set_size_inches(fig_width, fig_height)

    def draw_diagram(self):
        fig = plt.figure()
        ax = plt.axes()
        fig.subplots_adjust(left=0.0, bottom=0.0, right=1.0, top=1.0)
        fig.canvas.manager.set_window_title("Diagram")
        self.root_node.draw_all(fig, ax, equal_arrange=False)
        ax.set_aspect("equal", anchor="C", adjustable="datalim")
        ax.autoscale()
        ax.axis("off")
        tk_root = fig.canvas.get_tk_widget().master
        self.fig = fig
        self.ax = ax
        self.adjust_figure_size(self.root_node)
        self.init_figure()
        return tk_root


class CalcWindow:
    def __init__(self, tk_win, statgui):
        self.tk_win = tk_win
        self.name_txt = None
        self.type_txt = None
        self.desc_txt = None
        self.statgui = statgui
        self.create()
        self.pb_val = {"val": 0, "status": "stop", "result": 0}

    def update_pb(self):
        val = self.pb_val["val"]
        status = self.pb_val["status"]
        if status == "start":
            self.pb.configure(value=0)
            self.set_name("-")
            self.pb.after(100, self.update_pb)
        elif status == "finish":
            self.pb.configure(value=0)
            self.pb_val["status"] = "stop"
            self.pb.after(100, self.update_pb)
        elif status == "stop":
            self.button1["state"] = tk.NORMAL
            self.set_name(self.pb_val["result"])
        else:
            self.pb.configure(value=val)
            self.pb.after(100, self.update_pb)
        self.pb.update()

    def run_calc(self):
        statnode_name = self.statgui.statnode_name
        if statnode_name is not None:
            self.set_type(statnode_name)
            self.button1["state"] = tk.DISABLED
            self.pb_val["val"] = 0
            self.pb_val["status"] = "start"
            self.update_pb()
            event_data_set = self.statgui.event_data_set
            text = self.desc_txt.get("1.0", "end-1c")
            t = threading.Thread(
                target=self.calc,
                args=(
                    text,
                    event_data_set,
                ),
            )
            t.start()
        else:
            self.set_type("please pick up a statnode")

    def calc(self, text, event_data_set):
        def progress_bar(progress_i, progress_max, status):
            self.pb_val["val"] = (
                100 if progress_max == 0 else int(100 * progress_i / progress_max)
            )
            self.pb_val["status"] = status

        self.pb_val["result"] = "0"
        if event_data_set is None:
            self.pb_val["status"] = "finish"
            return
        try:
            cond = eval(text)
            calc_event_data_set, eval_error = event_data_set._get_event_data_set_main(
                cond, callback=progress_bar
            )
            self.pb_val["result"] = "{}".format(calc_event_data_set.size())
        except Exception as e:
            print(e)
        self.pb_val["status"] = "finish"

    def create(self):
        if self.tk_win is None:
            raise ValueError("tk must be set")

        self.tk_win.title("Calculation")
        self.tk_win.minsize(100, 100)
        self.tk_win.columnconfigure(0, weight=1)
        self.tk_win.rowconfigure(0, weight=1)

        # Frame
        frame1 = ttk.Frame(self.tk_win, padding=10)
        frame1.rowconfigure(1, weight=1)
        frame1.columnconfigure(0, weight=1)
        frame1.grid(sticky=(tk.N, tk.W, tk.S, tk.E))

        # Font
        f = Font(family="Courier", size=10)

        # name Text
        name_txt = tk.Text(frame1, height=1, width=10)
        name_txt.configure(font=f)
        name_txt.grid(row=0, column=0, sticky=(tk.N, tk.W, tk.E))
        name_txt.configure(state="disabled")

        # type Text
        type_txt = tk.Text(frame1, height=1, width=40)
        type_txt.configure(font=f)
        type_txt.grid(row=0, column=1, sticky=(tk.N, tk.W, tk.E))
        type_txt.configure(state="disabled")

        # Button
        button1 = ttk.Button(frame1, text="OK", command=self.run_calc)
        button1.grid(row=0, column=2, columnspan=2, sticky=(tk.N, tk.E))

        # Progressbar
        pb = ttk.Progressbar(
            frame1,
            orient="horizontal",
            length=300,
            value=0,
            maximum=100,
            mode="determinate",
        )
        pb.grid(row=1, column=0, columnspan=3, sticky=(tk.N, tk.W, tk.S, tk.E))

        # description Text
        desc_txt = tk.Text(frame1, height=15, width=70)
        desc_txt.configure(font=f)
        desc_txt.grid(row=2, column=0, columnspan=3, sticky=(tk.N, tk.W, tk.S, tk.E))

        # Scrollbar
        scrollbar = ttk.Scrollbar(frame1, orient=tk.VERTICAL, command=desc_txt.yview)
        desc_txt["yscrollcommand"] = scrollbar.set
        scrollbar.grid(row=1, column=3, sticky=(tk.N, tk.S))

        self.name_txt = name_txt
        self.type_txt = type_txt
        self.desc_txt = desc_txt
        self.button1 = button1
        self.pb = pb

    def set_title(self, txt):
        self.tk_win.title(txt)

    def set_name(self, txt):
        tk_text = self.name_txt
        tk_text.configure(state="normal")
        tk_text.delete("1.0", tk.END)
        tk_text.insert(tk.END, txt)
        tk_text.configure(state="disabled")

    def set_type(self, txt):
        tk_text = self.type_txt
        tk_text.configure(state="normal")
        tk_text.delete("1.0", tk.END)
        tk_text.insert(tk.END, txt)
        tk_text.configure(state="disabled")

    def set_desc(self, txt):
        tk_text = self.desc_txt
        tk_text.configure(state="normal")
        tk_text.delete("1.0", tk.END)
        tk_text.insert(tk.END, txt)
        tk_text.configure(state="disabled")


class StatGUI:
    """
    GUI for statistics of event data.

    Constructor options
    -------------------
    root_node : StatNode
        set of condition used to classify event data.
    event_data_list : None or list
        None : default
        list :
            list of event data. for details, see Simulation class.
    person_event_data_list : None or list
        None : default
        list :
            list of person event data. for details, see Simulation class.

    Examples
    --------
    >>> node0 = StatNode("root", wh=(2, 0.75))
    >>> node1a = StatNode("event1 not happen", wh=(2, 0.75), condition=EventLog())
    >>> node1b = StatNode("event1 happen", wh=(2, 0.75), condition=EventLog("event1"))
    >>> node0.set_branch([node1a, node1b])
    >>> root_node = node0
    >>> statgui = StatGUI(root_node, person_event_data_list=person_event_data_list)
    """

    def __init__(self, root_node, event_data_list=None, person_event_data_list=None):
        self.root_node = root_node
        id_manager = IdManager()
        event_data_set = EventDataSet(
            id_manager,
            event_data_list=event_data_list,
            person_event_data_list=person_event_data_list,
        )
        for event_data_info in event_data_set.get_event_data_info_list():
            self.root_node.send(event_data_info, ignore_error=True)
        self.tk_list = []
        self.statnode_name = None
        self.event_data_set = None

    def _draw_slider(self):
        fig = plt.figure(figsize=(5, 2))
        self.slider_fig = fig
        fig.canvas.manager.set_window_title("Log")

        axcolor = "gold"
        gs = fig.add_gridspec(2, 10)
        ax_textbox = fig.add_subplot(gs[0, 0:6], facecolor=axcolor)
        ax_button_prev = fig.add_subplot(gs[0, 6:8], facecolor=axcolor)
        ax_button_next = fig.add_subplot(gs[0, 8:10], facecolor=axcolor)
        ax_slider = fig.add_subplot(gs[1, :], facecolor=axcolor)
        # configure Slider
        self.step_min = 0
        self.step_max = 0
        step_init = 0
        step_delta = 1
        self.slider = Slider(
            ax_slider,
            "event",
            self.step_min,
            max(self.step_max, 1),
            valinit=step_init,
            valstep=step_delta,
        )
        # configure Textbox
        self.textbox = TextBox(ax_textbox, "time")
        self.textbox.set_val("(#{})".format(step_init))
        # configure Button
        self.button_prev = Button(ax_button_prev, "<<")
        self.button_next = Button(ax_button_next, ">>")
        # set event handler
        fig.canvas.mpl_connect("key_press_event", self._on_press)
        tk_root = fig.canvas.get_tk_widget().master
        return tk_root

    def _make_event_text(self, event_data_info):
        event_data = event_data_info.event_data
        table = prettytable.PrettyTable(["date", "event"])
        for k, v in event_data.items():
            table.add_row(["{}".format(k), "\n".join(v)])
        return table

    def _update(self):
        if self.event_data_set is None:
            return

        s_val = self.slider.val
        max_val = self.event_data_set.size()
        if max_val <= s_val:
            s_val = max_val - 1
        if s_val < 0:
            self.textbox.set_val("no data")
            self.mw.set_type("")
            self.mw.set_desc("")
            return

        self.textbox.set_val("(#{})".format(s_val))
        event_data_info = self.event_data_set.get_event_data_info(s_val)
        text = self._make_event_text(event_data_info)
        person_name = event_data_info.meta_data["person_data"]["name"]
        self.mw.set_type("id[{}] [{}]".format(event_data_info.id, person_name))
        self.mw.set_desc(text)
        self.slider_fig.canvas.draw_idle()

    def _on_press(self, event):
        if event.key == "left":
            self._update_button_prev(None)
        if event.key == "right":
            self._update_button_next(None)

    def _view_change(self, val):
        self._update()

    def _update_button_prev(self, event):
        val = self.slider.val
        val = np.max([self.step_min, val - 1])
        self.slider.set_val(val)
        self.slider_fig.canvas.draw_idle()

    def _update_button_next(self, event):
        val = self.slider.val
        val = np.min([self.step_max, val + 1])
        val = np.max([0, val])
        self.slider.set_val(val)
        self.slider_fig.canvas.draw_idle()

    def _set_node(self, statnode):
        r_tmp = statnode
        self.statnode_name = statnode.name
        self.event_data_set = r_tmp.event_data_set_inbound
        size = self.event_data_set.size()
        max_val = np.max([0, size - 1])
        self.step_min = 0
        self.step_max = max_val
        self.slider.valmin = self.step_min
        self.slider.valmax = max(self.step_max, 1)
        self.slider.set_val(0)
        self.slider.ax.set_xlim(self.slider.valmin, self.slider.valmax)
        self.mw.set_name(self.statnode_name)
        self._update()

    def make_diagram_report(self, root_node, format):
        def compare_statnode(statnode1, statnode2):
            if statnode1.level > statnode2.level:
                return 1
            if statnode1.level < statnode2.level:
                return -1
            for idx in range(len(statnode1.statnode_id_detail)):
                if (
                    statnode1.statnode_id_detail[idx]
                    > statnode2.statnode_id_detail[idx]
                ):
                    return 1
                if (
                    statnode1.statnode_id_detail[idx]
                    < statnode2.statnode_id_detail[idx]
                ):
                    return -1
            return 0

        statnode_list = root_node._get_node(None)
        statnode_list.sort(key=cmp_to_key(compare_statnode))
        html_info_table = table()
        html_info_table.set_attribute("class", "normal")
        info_header_title = "info"
        if format == "md":
            info_header_title += " (some information omitted in md file)"
        with html_info_table.add(tbody()):
            l = tr()
            l.add(th("name"))
            l.add(th(info_header_title))
            l.add(th("up"))
            l.add(th("down"))
            for statnode in statnode_list:
                l = tr()
                l.add(
                    td(
                        raw(
                            '<div id="{}">{}</div>'.format(
                                statnode.statnode_id, statnode.name
                            )
                        )
                    )
                )

                text = "I={}, S={}".format(statnode.inbound, statnode.stop)
                if format == "html" and statnode.condition is not None:
                    text += "<p>event log</br><code>{}</code></p>".format(
                        statnode.condition.name
                    )
                l.add(td(raw(text)))

                text = ""
                if statnode.parent is not None:
                    text = '<a href="#{}">{}</a>'.format(
                        statnode.parent.statnode_id, statnode.parent.name
                    )
                l.add(td(raw(text)))

                text = ""
                if statnode.child_statnode is not None:
                    text_list = []
                    for child in statnode.child_statnode:
                        text_list.append(
                            '<a href="#{}">{}</a>'.format(child.statnode_id, child.name)
                        )
                    if format == "html":
                        text = "</br>".join(text_list)
                    if format == "md":
                        text = ", ".join(text_list)
                l.add(td(raw(text)))

    def _add_head_style(self, h):
        h.add(
            head(
                style(
                    (
                        """
h1 {
    background: #c2edff;
    padding: 0.5em;
}
h2 {
    padding: 0.25em 0.5em;
    color: #494949;
    background: transparent;
    border-left: solid 5px #7db4e6;
}
img {
    max-width: 100%;
}
table.normal {
    border-collapse: collapse;
    border:1px solid gray;
}
table.normal th, table.normal td {
    border: 1px solid gray;
}
code {
    font-size: 80%;
    display: inline-block;
    padding: 0.1em 0.25em;
    color: #444;
    background-color: #e7edf3;
    border-radius: 3px;
    border: solid 1px #d6dde4;
}
                     """
                    )
                )
            )
        )

    def make_report(self, output_path, format="html"):
        valid_format_list = ["html", "md"]
        if format not in valid_format_list:
            raise ValueError(
                "not valid format: {}. valid_format is {}".format(
                    format, valid_format_list
                )
            )
        dw = DiagramWindow(self.root_node)
        dw.draw_diagram()
        fig_name = "diagram"
        pic_filename = "{}.jpg".format(fig_name)
        pic_output_path = os.path.join(output_path, pic_filename)
        dw.fig.savefig(pic_output_path)

        h = html()
        if format is "html":
            self._add_head_style(h)
        with h.add(body()).add(div(id="content")):
            h1("Diagram Report")
            img(src=pic_filename)
            self.make_diagram_report(self.root_node, format)

        output_str = str(h)
        if format is "md":
            output_str = markdownify(output_str, heading_style="ATX")

        html_filename = "diagram_report.{}".format(format)
        html_output_path = os.path.join(output_path, html_filename)

        with open(html_output_path, mode="w") as f:
            f.write(str(output_str))

    def show(self):
        """
        Show a diagram and event logs.
        """

        def tk_destroy(tk_root):
            print("destroy")
            tk_root.quit()
            tk_root.destroy()

        def fixed_map(option):
            return [
                elm
                for elm in style.map("Treeview", query_opt=option)
                if elm[:2] != ("!disabled", "!selected")
            ]

        root = tk.Tk()
        style = ttk.Style(root)
        style.map(
            "Treeview",
            foreground=fixed_map("foreground"),
            background=fixed_map("background"),
        )

        self.mw = MainWindow(root)
        self.tk_list.append(root)
        self.name_txt = self.mw.name_txt
        self.type_txt = self.mw.type_txt
        self.txt = self.mw.desc_txt
        self.txt_root = root

        root = tk.Toplevel()
        self.cw = CalcWindow(root, self)
        self.tk_list.append(root)

        self.dw = DiagramWindow(self.root_node)
        tk_root = self.dw.draw_diagram()
        self.root_node.set_process(self._set_node, "pick_process")
        self.tk_list.append(tk_root)
        tk_root = self._draw_slider()
        self.tk_list.append(tk_root)
        self.slider.on_changed(self._view_change)
        self.button_prev.on_clicked(self._update_button_prev)
        self.button_next.on_clicked(self._update_button_next)
        for tk_root in self.tk_list:
            tk_root.protocol("WM_DELETE_WINDOW", lambda: tk_destroy(tk_root))

        plt.show()
