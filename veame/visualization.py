import numpy as np
import inspect
import matplotlib

matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider
from matplotlib.widgets import TextBox
from matplotlib.widgets import Button
import networkx as nx
from networkx.drawing.nx_pydot import graphviz_layout
import prettytable
import tkinter as tk
import tkinter.ttk as ttk
from tkinter.font import Font

from .common import vis_log
from .statemachine import State
from .statemachine import Trigger
from .event_base import Event
from .event_base import VirtualEvent
from .event import TimerEvent
from .event import StochasticEvent
from .event import RandomEventChild


def make_table(cols, header=[]):
    if not header:
        header = range(len(list(cols)[0]))
    if len(header) != len(cols[0]):
        print("incorrect length!")
        return
    table = prettytable.PrettyTable(header)
    for other in cols:
        table.add_row(other)
    return table


def get_default_param(func, arg_names):
    sig = inspect.signature(func)
    default_param = {}
    for arg_name in arg_names:
        param = sig.parameters.get(arg_name)
        if param is not None:
            default_param[arg_name] = param.default
    return default_param


def get_event_func_table(event_set):
    timer_event_set = set()
    stochastic_event_set = set()
    random_event_set = set()

    for event in event_set:
        if isinstance(event, TimerEvent):
            timer_event_set.add(event)
            continue
        if isinstance(event, StochasticEvent):
            stochastic_event_set.add(event)
            continue
        if isinstance(event, RandomEventChild):
            random_event_set.add(event.parent)
            continue

    arg_names = ["sm_name", "ev_name", "tag_name"]
    cols = []
    event_type = "timer event"
    for event in timer_event_set:
        func = event.interval
        if func is not None and callable(func):
            default_param = get_default_param(func, arg_names)
            cols.append(
                [
                    event_type,
                    event.name,
                    default_param.get(arg_names[0]),
                    default_param.get(arg_names[1]),
                    default_param.get(arg_names[2]),
                ]
            )
    event_type = "stochastic event"
    for event in stochastic_event_set:
        func = event.probability_func
        if func is not None and callable(func):
            default_param = get_default_param(func, arg_names)
            cols.append(
                [
                    event_type,
                    event.name,
                    default_param.get(arg_names[0]),
                    default_param.get(arg_names[1]),
                    default_param.get(arg_names[2]),
                ]
            )
    event_type = "random event"
    for event in random_event_set:
        func = event.name_and_probability_func
        if func is not None and callable(func):
            default_param = get_default_param(func, arg_names)
            cols.append(
                [
                    event_type,
                    event.name,
                    default_param.get(arg_names[0]),
                    default_param.get(arg_names[1]),
                    default_param.get(arg_names[2]),
                ]
            )
    return cols, [
        "type",
        "event name",
        "{} in func".format(arg_names[0]),
        "{} in func".format(arg_names[1]),
        "{} in func".format(arg_names[2]),
    ]


def get_update_parameter_func_table(state_set):
    arg_names = ["sm_name", "state_name", "tag_name"]
    cols = []
    for state in state_set:
        for func in state.update_parameter_func_list:
            default_param = get_default_param(func, arg_names)
            cols.append(
                [
                    state.name,
                    default_param.get(arg_names[0]),
                    default_param.get(arg_names[1]),
                    default_param.get(arg_names[2]),
                ]
            )
    return cols, [
        "state name",
        "{} in func".format(arg_names[0]),
        "{} in func".format(arg_names[1]),
        "{} in func".format(arg_names[2]),
    ]


def make_string(value):
    if value is None:
        return "None"
    if value == True:
        return "True"
    if value == False:
        return "False"
    return "{}".format(value)


def draw(G, pos=None, ax=None, **keywords):
    if ax is not None:
        cf = ax.get_figure()
    else:
        cf = plt.gcf()
    cf.set_facecolor("w")
    if ax is None:
        if cf._axstack() is not None:
            ax = cf.gca()
        else:
            ax = cf.add_axes((0, 0, 1, 1))

    if "with_labels" not in keywords:
        keywords["with_labels"] = "labels" in keywords

    scatter, edge_list = draw_networkx(G, pos=pos, ax=ax, **keywords)
    ax.set_axis_off()
    plt.draw_if_interactive()
    return scatter, edge_list


def draw_networkx(G, pos=None, arrows=None, with_labels=True, **keywords):
    valid_edge_keywords = set(
        [
            "alpha",
            "ax",
            "arrowstyle",
            "arrowsize",
            "connectionstyle",
            "edgelist",
            "edge_color",
            "edge_cmap",
            "edge_vmax",
            "edge_vmin",
            "label",
            "min_source_margin",
            "min_target_margin",
            "nodelist",
            "node_shape",
            "node_size",
            "style",
            "width",
        ]
    )

    valid_label_keywords = set(
        [
            "alpha",
            "ax",
            "bbox",
            "font_size",
            "font_color",
            "font_family",
            "font_weight",
            "horizontalalignment",
            "labels",
            "verticalalignment",
        ]
    )

    valid_node_keywords = set(
        [
            "alpha",
            "ax",
            "cmap",
            "edgecolors",
            "label",
            "linewidths",
            "nodelist",
            "node_color",
            "node_shape",
            "node_size",
            "vmax",
            "vmin",
        ]
    )

    valid_keywords = valid_edge_keywords | valid_label_keywords | valid_node_keywords
    invalid_keywords = keywords.keys() - valid_keywords
    if len(invalid_keywords) > 0:
        invalid_args = ", ".join(invalid_keywords)
        raise ValueError(f"invalid argument(s): {invalid_args}")

    edge_keywords = {k: keywords[k] for k in keywords.keys() & valid_edge_keywords}
    label_keywords = {k: keywords[k] for k in keywords.keys() & valid_label_keywords}
    node_keywords = {k: keywords[k] for k in keywords.keys() & valid_node_keywords}

    if pos is None:
        pos = nx.drawing.spring_layout(G)

    scatter = nx.draw_networkx_nodes(G, pos, **node_keywords)
    edge_list = nx.draw_networkx_edges(G, pos, arrows=arrows, **edge_keywords)
    if with_labels:
        nx.draw_networkx_labels(G, pos, **label_keywords)
    plt.draw_if_interactive()
    return scatter, edge_list


class PanZoomFigure:
    def __init__(self):
        self.ax = None
        self.fig = None
        self.base_scale = 2.0
        self.fig_scale = 0.01
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

        if event.button in (1, 3):  # Start
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

    def adjust_figure_size(self, pos, G):
        x_margin = 75
        y_margin = 25
        pos_x = [pos[node][0] for node in G.nodes]
        pos_y = [pos[node][1] for node in G.nodes]
        x_min = min(pos_x) - x_margin
        x_max = max(pos_x) + x_margin
        y_min = min(pos_y) - y_margin
        y_max = max(pos_y) + y_margin
        fig_width = (x_max - x_min) * self.fig_scale
        fig_height = (y_max - y_min) * self.fig_scale
        self.fig.set_size_inches(fig_width, fig_height)


class MultiDictElem:
    def __init__(self, multi_dict, attr_value_dict):
        self.multi_dict = multi_dict
        self.attr_value_dict = attr_value_dict

    def _is_already_set(self, attr_value_dict):
        return len(self.attr_value_dict.keys() & attr_value_dict.keys()) > 0

    def update(self, attr_value_dict):
        if self._is_already_set(attr_value_dict) or self.multi_dict._is_duplicated(
            attr_value_dict
        ):
            return
        self.attr_value_dict.update(attr_value_dict)
        self.multi_dict._update_elem(self, attr_value_dict)

    def get(self, attr):
        return self.attr_value_dict.get(attr)


class MultiDict:
    def __init__(self, index_attr_list):
        self.index_attr_list = index_attr_list
        self.index_dict = {}
        for attr in index_attr_list:
            self.index_dict[attr] = {}

    def _is_duplicated(self, attr_value_dict):
        duplicated_flag = False
        for attr, value in attr_value_dict.items():
            if attr not in self.index_attr_list:
                continue
            index = self.index_dict.get(attr)
            if index is None:
                self.index_dict[attr] = {}
                index = self.index_dict[attr]
            if index.get(value) is not None:
                duplicated_flag = True
        return duplicated_flag

    def append(self, attr_value_dict):
        if self._is_duplicated(attr_value_dict):
            return
        multi_dict_elem = MultiDictElem(self, attr_value_dict)
        for attr, value in attr_value_dict.items():
            if attr not in self.index_attr_list:
                continue
            index = self.index_dict.get(attr)
            index[value] = multi_dict_elem

    def _update_elem(self, multi_dict_elem, attr_value_dict):
        for attr, value in attr_value_dict.items():
            if attr not in self.index_attr_list:
                continue
            index = self.index_dict.get(attr)
            index[value] = multi_dict_elem

    def update(self, multi_dict):
        for attr in set(self.index_attr_list) & set(multi_dict.index_attr_list):
            self_index = self.index_dict[attr]
            other_index = multi_dict.index_dict[attr]
            self_index.update(other_index)

    def find(self, attr, value):
        index = self.index_dict.get(attr)
        if index is None:
            return None
        multi_dict_elem = index.get(value)
        return multi_dict_elem

    def keys(self, attr):
        index = self.index_dict.get(attr)
        if index is None:
            return None
        return index.keys()


class StateMachineFigure(PanZoomFigure):
    def __init__(self, state_machine):
        self.state_machine = state_machine
        self.last_state_name = None
        self.color_dict = None
        self.name = state_machine.name
        self.scatter_node_dict = {}
        self.node_color = None
        self.scatter = None
        self.annot = None
        self.attr_list = ["pick_process"]
        for attr in self.attr_list:
            self.__dict__[attr] = None

        self.edge_trigger_multi_dict = None
        self.edge_labels_dict = None
        self.edge_labels = None
        self.label_pos = 0.35
        super().__init__()

    def set_process(self, func, attr_name):
        if attr_name in self.attr_list:
            self.__dict__[attr_name] = func
        else:
            raise ValueError("not valid attr name: {}".format(attr_name))

    def update_state(self, state_name):
        is_change = False
        if self.color_dict is None:
            self.color_dict = {}
            for node in self.G.nodes:
                self.color_dict[node] = "white"
            self.color_dict["start"] = "cyan"
            is_change = True
        else:
            if self.last_state_name != state_name:
                self.color_dict[self.last_state_name] = "white"
                self.color_dict[state_name] = "red"
                self.last_state_name = state_name
                is_change = True
            else:
                if self.color_dict[state_name] != "cyan":
                    self.color_dict[state_name] = "cyan"
                    is_change = True

        if is_change and self.scatter is not None:
            node_color = [None] * len(self.G.nodes)
            for node in self.G.nodes:
                node_color[self.scatter_node_dict[node]] = self.color_dict[node]
            self.scatter.set_facecolor(node_color)

    def _update_annot_scatter(self, ind):
        idx = ind["ind"][0]
        pos = self.scatter.get_offsets()[idx]
        self.annot.xy = pos
        state_name = self.state_name_list[idx]
        text = state_name
        self.annot.set_text(text)

    def _hover_scatter(self, event):
        cont, ind = self.scatter.contains(event)
        if cont:
            self._update_annot_scatter(ind)
            self.annot.set_visible(True)
            self._draw()
            return True
        return False

    def _update_annot_edge(self, edge, trigger):
        self.annot.xy = self.edge_trigger_multi_dict.find("edge", edge).get(
            "nx_edge_pos"
        )
        text = trigger.name
        self.annot.set_text(text)

    def _hover_edge(self, event):
        for edge in self.edge_trigger_multi_dict.keys("edge"):
            cont, ind = edge.contains(event)
            if cont:
                trigger = self.edge_trigger_multi_dict.find("edge", edge).get("trigger")
                self._update_annot_edge(edge, trigger)
                self.annot.set_visible(True)
                self._draw()
                return True
        return False

    def _update_annot_label(self, t, label):
        edge_trigger_info = self.edge_trigger_multi_dict.find("nx_edge_label", label)
        self.annot.xy = edge_trigger_info.get("nx_edge_pos")
        trigger = edge_trigger_info.get("trigger")
        text = trigger.name
        self.annot.set_text(text)

    def _hover_label(self, event):
        for label, t in self.edge_labels_dict.items():
            cont, ind = t.contains(event)
            if cont:
                self._update_annot_label(t, label)
                self.annot.set_visible(True)
                self._draw()
                return True
        return False

    def _hover(self, event):
        vis = self.annot.get_visible()
        if event.inaxes == self.ax:
            if not (
                self._hover_scatter(event)
                or self._hover_edge(event)
                or self._hover_label(event)
            ):
                if vis:
                    self.annot.set_visible(False)
                    self._draw()

    def select(self, artist, param, element):
        # clear
        for text in self.edge_trigger_multi_dict.keys("nx_text"):
            text.set_backgroundcolor("white")
        for i in range(len(self.node_color)):
            self.node_color[i] = "white"
        self.scatter.set_facecolor(self.node_color)
        # set color
        if isinstance(artist, matplotlib.text.Text):
            text = artist
            text.set_backgroundcolor("yellow")
        if isinstance(artist, matplotlib.collections.PathCollection):
            scatter = artist
            idx = param
            self.node_color[idx] = "yellow"
            scatter.set_facecolor(self.node_color)
        self._draw()

    def _pick(self, event):
        artist = event.artist
        if isinstance(artist, matplotlib.text.Text):
            text = artist
            if self.pick_process is not None:
                trigger = self.edge_trigger_multi_dict.find("nx_text", text).get(
                    "trigger"
                )
                trigger_name = trigger.name
                print("trigger_name = {}".format(trigger_name))
                self.pick_process(text, None, trigger, self)
            return
        if isinstance(artist, matplotlib.collections.PathCollection):
            scatter = artist
            idx = event.ind[0]
            if self.pick_process is not None:
                state_name = self.state_name_list[idx]
                state = self.state_machine.state_dict.get(state_name)
                if state is not None:
                    self.pick_process(scatter, idx, state, self)
            return

    def draw_network_state_machine(self, rotate_angle=0):
        state_machine = self.state_machine
        state_dict = state_machine.state_dict
        G = nx.DiGraph()
        state_name_list = [state.name for _, state in state_dict.items()]
        start_num = 0
        trigger_dict = {}
        for _, state in state_dict.items():
            name_from = state.name
            for name_to, trigger in state.next.items():
                trigger_dict[trigger.name] = trigger
                if name_to == "start":
                    name_to = "start#{}".format(start_num)
                    start_num = start_num + 1
                    state_name_list.append(name_to)
        state_labels = {state_name: state_name for state_name in state_name_list}
        G.add_nodes_from(state_name_list)
        edge_labels = {}
        start_num = 0
        for _, state in state_dict.items():
            name_from = state.name
            for name_to, trigger in state.next.items():
                if not G.has_edge(name_from, name_to):
                    if name_to == "start":
                        name_to = "start#{}".format(start_num)
                        start_num = start_num + 1
                    G.add_edge(name_from, name_to)
                    edge_label = trigger.name
                    edge_labels[(name_from, name_to)] = edge_label
        fig = plt.figure()
        fig.canvas.manager.set_window_title(self.state_machine.name)
        ax = fig.add_subplot(111)
        # draw graph
        pos = graphviz_layout(G, prog="dot")
        self.node_color = ["white" for node in G.nodes]
        self.scatter, edge_list = draw(
            G,
            pos,
            with_labels=False,
            width=5,
            arrows=True,
            arrowsize=25,
            node_color=self.node_color,
            node_size=300,
            edgecolors="b",
            edge_color="lightblue",
            min_source_margin=600,
            min_target_margin=600,
        )
        for node_i, node in enumerate(G.nodes):
            self.scatter_node_dict[node] = node_i
        self.fig = fig
        self.G = G
        self.pos = pos
        self.ax = ax
        self.state_name_list = state_name_list
        self.edge_labels = edge_labels
        self.adjust_figure_size(pos, G)
        # set labels
        node_labels_dict = nx.draw_networkx_labels(
            G, pos, labels=state_labels, font_size=8
        )
        for label, t in node_labels_dict.items():
            t.set_rotation(rotate_angle)
        edge_labels_dict = nx.draw_networkx_edge_labels(
            G,
            pos,
            edge_labels=edge_labels,
            label_pos=self.label_pos,
            font_size=8,
            font_color="black",
            rotate=False,
        )
        ax.set_aspect("equal", anchor="C", adjustable="datalim")
        self.edge_labels_dict = edge_labels_dict
        for label, t in node_labels_dict.items():
            state = state_dict.get(label)
            if state is None:
                vis_log.debug("skip registering state: {}".format(label))
        for label, t in edge_labels_dict.items():
            trigger = trigger_dict[edge_labels[label]]
            if not hasattr(trigger, "event"):
                t.set_color("red")
        self.edge_trigger_multi_dict = MultiDict(
            ["trigger", "edge", "nx_edge_label", "nx_text"]
        )
        for i, e in enumerate(G.edges()):
            label = (e[0], e[1])
            trigger_name = edge_labels[label]
            trigger = trigger_dict[trigger_name]
            edge = edge_list[i]
            text = edge_labels_dict[label]
            edge_pos = (
                (pos[e[0]][0] * self.label_pos + pos[e[1]][0] * (1.0 - self.label_pos)),
                (pos[e[0]][1] * self.label_pos + pos[e[1]][1] * (1.0 - self.label_pos)),
            )
            self.edge_trigger_multi_dict.append(
                {
                    "trigger": trigger,
                    "edge": edge,
                    "nx_edge_label": label,
                    "nx_text": text,
                    "nx_edge_pos": edge_pos,
                }
            )

        # annotation
        self.annot = ax.annotate(
            "",
            xy=(0, 0),
            xytext=(20, 20),
            textcoords="offset points",
            bbox=dict(boxstyle="round", fc="w"),
            arrowprops=dict(arrowstyle="->"),
        )
        self.annot.set_visible(False)
        fig.canvas.mpl_connect("motion_notify_event", self._hover)
        fig.canvas.mpl_connect("pick_event", self._pick)
        # set picker
        self.scatter.set_picker(True)
        for label, t in edge_labels_dict.items():
            t.set_picker(True)
        self.init_figure()
        return fig.canvas.get_tk_widget().master


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
        f = Font(family="Helvetica", size=10)

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
        v1 = tk.StringVar()
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


class EventWindow:
    def __init__(self, tk_win):
        self.tk_win = tk_win
        self.tree = None
        self.tree_col = {}
        self.create()
        self.attr_list = ["pick_process"]
        for attr in self.attr_list:
            self.__dict__[attr] = None
        self.event_dict = {}
        self.event_trigger_dict = {}

    def set_process(self, func, attr_name):
        if attr_name in self.attr_list:
            self.__dict__[attr_name] = func
        else:
            raise ValueError("not valid attr name: {}".format(attr_name))

    def on_tree_select(self, event):
        tree = event.widget
        for item in tree.selection():
            if self.pick_process is not None:
                item1 = tree.item(item)
                event_name = item1["values"][0]
                event = self.event_dict[event_name]
                self.pick_process(tree, item, event)
            return

    def header_selected(self, tree, reverse_flag):
        click_x_pos = tree.winfo_pointerx() - tree.winfo_rootx()
        select_column = tree.identify_column(click_x_pos)
        select_column = int(select_column[1:]) - 1

        table_list = [
            (tree.set(row_id, select_column), row_id)
            for row_id in tree.get_children("")
        ]
        table_list.sort(reverse=reverse_flag)

        for index, (val, row_id) in enumerate(table_list):
            tree.move(row_id, "", index)

        tree.heading(
            select_column,
            command=lambda: self.header_selected(tree, not reverse_flag),
        )

    def create(self):
        if self.tk_win is None:
            raise ValueError("tk must be set")
        self.tk_win.title("Event")
        frame = ttk.Frame(self.tk_win, width=100, height=100)

        tree = ttk.Treeview(frame)

        tree["columns"] = (1, 2, 3, 4, 5)
        tree["show"] = "headings"

        tree.column(1, width=100)
        tree.column(2, width=100)
        tree.column(3, width=100)
        tree.column(4, width=100)
        tree.column(5, width=100)

        tree.heading(
            1, text="event name", command=lambda: self.header_selected(tree, False)
        )
        tree.heading(
            2, text="formula", command=lambda: self.header_selected(tree, False)
        )
        tree.heading(
            3,
            text="event_raise_time",
            command=lambda: self.header_selected(tree, False),
        )
        tree.heading(
            4, text="done time", command=lambda: self.header_selected(tree, False)
        )
        tree.heading(
            5,
            text="is event raise flag",
            command=lambda: self.header_selected(tree, False),
        )

        tree.grid(row=1, column=1, sticky="nsew")
        vbar = tk.Scrollbar(frame, orient=tk.VERTICAL, width=35, command=tree.yview)
        tree.configure(yscrollcommand=vbar.set)

        vbar.grid(row=1, column=2, sticky="nsew")

        frame.grid_columnconfigure(1, weight=1)
        frame.grid_columnconfigure(2, minsize=35)
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_rowconfigure(2, minsize=35)
        frame.pack(fill="both", expand=True)

        tree.tag_configure("highlight", background="yellow")
        tree.bind("<ButtonRelease-1>", self.on_tree_select)

        self.tree = tree

    def init_list(self, log_store, person):
        item_set = set()
        state_machines = person.state_machines
        total_event_set = set()
        for state_machine in state_machines:
            trigger_event_list = state_machine.get_trigger_event_list()
            for event in trigger_event_list:
                event.get_log_info_event(total_event_set)
        for event in total_event_set:
            item_set.add(event.name)
            self.event_dict[event.name] = event

        for state_machine in state_machines:
            if state_machine.drop_event is not None:
                event = state_machine.drop_event
                if self.event_trigger_dict.get(event) is None:
                    self.event_trigger_dict[event] = ["drop_trigger"]

            for trigger in state_machine.get_trigger_list():
                if not hasattr(trigger, "event"):
                    continue
                event = trigger.event
                if self.event_trigger_dict.get(event) is None:
                    self.event_trigger_dict[event] = [trigger.name]

        for name in item_set:
            col = self.tree.insert("", "end", values=(name, "", "", ""), tags="black")
            self.tree_col[name] = col

        self.tree.tag_configure("red", foreground="red")
        self.tree.tag_configure("black", foreground="black")

    def update(self, prev_info_dict, info_dict):
        def diff_info(info1, info2):
            if info1 is not None and info2 is not None:
                if info1.event_raise_time != info2.event_raise_time:
                    return True
                if info1.done_time != info2.done_time:
                    return True
                if info1.is_event_raise_flag != info2.is_event_raise_flag:
                    return True
                return False
            if info1 != info2:
                return True
            return False

        for name, col in self.tree_col.items():
            info = info_dict.get(name) if info_dict is not None else None
            if info is None:
                event = self.event_dict[name]
                self.tree.set(col, 1, name)
                self.tree.set(col, 2, event.event_formula)
                self.tree.set(col, 3, "")
                self.tree.set(col, 4, "")
                self.tree.set(col, 5, "")
                self.tree.item(col, tags="black")
            else:
                prev_info = (
                    prev_info_dict.get(name) if prev_info_dict is not None else None
                )
                color = "red" if diff_info(prev_info, info) else "black"
                self.tree.set(col, 1, info.name)
                self.tree.set(col, 2, info.event_formula)
                self.tree.set(col, 3, make_string(info.event_raise_time))
                self.tree.set(col, 4, make_string(info.done_time))
                self.tree.set(col, 5, make_string(info.is_event_raise_flag))
                self.tree.item(col, tags=color)


class ParameterWindow:
    def __init__(self, tk_win):
        self.tk_win = tk_win
        self.tree = None
        self.tree_col = {}
        self.create()

    def header_selected(self, tree, reverse_flag):
        click_x_pos = tree.winfo_pointerx() - tree.winfo_rootx()
        select_column = tree.identify_column(click_x_pos)
        select_column = int(select_column[1:]) - 1

        table_list = [
            (tree.set(row_id, select_column), row_id)
            for row_id in tree.get_children("")
        ]
        table_list.sort(reverse=reverse_flag)

        for index, (val, row_id) in enumerate(table_list):
            tree.move(row_id, "", index)

        tree.heading(
            select_column,
            command=lambda: self.header_selected(tree, not reverse_flag),
        )

    def create(self):
        if self.tk_win is None:
            raise ValueError("tk must be set")
        self.tk_win.title("Parameter")
        frame = ttk.Frame(self.tk_win, width=100, height=100)

        tree = ttk.Treeview(frame)

        tree["columns"] = (
            1,
            2,
        )
        tree["show"] = "headings"

        tree.column(1, width=100)
        tree.column(2, width=100)

        tree.heading(
            1, text="parameter name", command=lambda: self.header_selected(tree, False)
        )
        tree.heading(
            2, text="parameter value", command=lambda: self.header_selected(tree, False)
        )

        tree.grid(row=1, column=1, sticky="nsew")
        vbar = tk.Scrollbar(frame, orient=tk.VERTICAL, width=35, command=tree.yview)
        tree.configure(yscrollcommand=vbar.set)

        vbar.grid(row=1, column=2, sticky="nsew")

        frame.grid_columnconfigure(1, weight=1)
        frame.grid_columnconfigure(2, minsize=35)
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_rowconfigure(2, minsize=35)
        frame.pack(fill="both", expand=True)

        self.tree = tree

    def init_list(self, log_store, person):
        last_idx = log_store.get_log_last_idx()
        item_set = set()
        for idx in range(last_idx):
            state, parameter, event, current_time = log_store.get_log(idx)
            if parameter is not None:
                for name in parameter.log_info.keys():
                    item_set.add(name)
        for name in item_set:
            col = self.tree.insert(
                "",
                "end",
                values=(
                    name,
                    "",
                ),
                tags="black",
            )
            self.tree_col[name] = col
        self.tree.tag_configure("red", foreground="red")
        self.tree.tag_configure("black", foreground="black")

    def update(self, prev_info_dict, info_dict):
        for name, col in self.tree_col.items():
            info = info_dict.get(name) if info_dict is not None else None
            if info is None:
                self.tree.set(col, 1, name)
                self.tree.set(col, 2, "")
                self.tree.item(col, tags="black")
            else:
                prev_info = (
                    prev_info_dict.get(name) if prev_info_dict is not None else None
                )
                color = "red" if info != prev_info else "black"
                self.tree.set(col, 1, name)
                self.tree.set(col, 2, make_string(info))
                self.tree.item(col, tags=color)


class EventNetworkFigure(PanZoomFigure):
    def __init__(self, person):
        self.person = person
        super().__init__()
        self.init()

    def init(self):
        self.node_connection = {}
        self.node_name_dict = {}
        self.name_node_dict = {}
        self.node_name_serial = {}

    def get_serial_name(self, event_name0):
        serial = self.node_name_serial.get(event_name0)
        if serial is None:
            serial = 0
            self.node_name_serial[event_name0] = serial
        else:
            serial += 1
            self.node_name_serial[event_name0] = serial
        if serial > 0:
            event_name = "{}#{}".format(event_name0, serial)
        else:
            event_name = event_name0
        return event_name

    def add_node(self, node):
        if isinstance(node, Event):
            event = node
            event_name = "#E_{}".format(event.name)
            serial_name = self.get_serial_name(event_name)
            self.node_name_dict[event] = serial_name
            self.name_node_dict[serial_name] = event
            return
        if isinstance(node, VirtualEvent):
            event = node
            event_name0 = event.get_event_name()
            event_name1 = event.get_name()
            event_name = event_name0 if event_name0 is not None else event_name1
            event_name = "#V_{}".format(event.name)
            serial_name = self.get_serial_name(event_name)
            self.node_name_dict[event] = serial_name
            self.name_node_dict[serial_name] = event
            return
        if isinstance(node, Trigger):
            trigger = node
            trigger_name = "#T_{}".format(trigger.name)
            serial_name = self.get_serial_name(trigger_name)
            self.node_name_dict[trigger] = serial_name
            self.name_node_dict[serial_name] = trigger
            return

    def _update_annot_scatter(self, ind):
        idx = ind["ind"][0]
        pos = self.scatter.get_offsets()[idx]
        self.annot.xy = pos
        node_name = self.node_name_list[idx]
        self.annot.set_text(node_name)

    def _hover_scatter(self, event):
        cont, ind = self.scatter.contains(event)
        if cont:
            self._update_annot_scatter(ind)
            self.annot.set_visible(True)
            self._draw()
            return True
        return False

    def _hover(self, event):
        vis = self.annot.get_visible()
        if event.inaxes == self.ax:
            if not (self._hover_scatter(event)):
                if vis:
                    self.annot.set_visible(False)
                    self._draw()

    def make_event_connection(self):
        def find_event_connection(event, event_stack=[]):
            # loop check
            if event in event_stack:
                raise ValueError("event evaluation looping")
            event_stack.append(event)

            child_events = self.node_connection.get(event)
            if child_events is not None:
                event_stack.pop()
                return
            if isinstance(event, Event):
                child_events = []
                self.node_connection[event] = child_events
                if hasattr(event, "child_a") and event.child_a is not None:
                    child_events.append(event.child_a)
                    find_event_connection(event.child_a, event_stack)
                if hasattr(event, "child_b") and event.child_b is not None:
                    child_events.append(event.child_b)
                    find_event_connection(event.child_b, event_stack)
                event_stack.pop()
                return
            if isinstance(event, VirtualEvent):
                child_events = []
                self.node_connection[event] = child_events
                if event.is_real_event:
                    if event.real_event is not None:
                        child_events.append(event.real_event)
                        find_event_connection(event.real_event, event_stack)
                    event_stack.pop()
                    return
                if hasattr(event, "child_a") and event.child_a is not None:
                    child_events.append(event.child_a)
                    find_event_connection(event.child_a, event_stack)
                if hasattr(event, "child_b") and event.child_b is not None:
                    child_events.append(event.child_b)
                    find_event_connection(event.child_b, event_stack)
                event_stack.pop()
                return
            event_stack.pop()

        def print_node_connection():
            for event, child_events in self.node_connection.items():
                event_name = self.node_name_dict[event]
                child_event_name_list = []
                for child_event in child_events:
                    child_event_name = self.node_name_dict[child_event]
                    child_event_name_list.append(child_event_name)
                print("{}, {}".format(event_name, child_event_name_list))

        def make_node_name_dict():
            self.node_name_serial.clear()
            for node in self.node_connection.keys():
                self.add_node(node)

        def get_events(trigger_list):
            for trigger in trigger_list:
                event = trigger.event
                child_events = self.node_connection.get(trigger)
                if child_events is None:
                    self.node_connection[trigger] = [event]
                find_event_connection(event, [])
            make_node_name_dict()

        self.init()
        state_machines = self.person.state_machines
        for state_machine in state_machines:
            trigger_list = state_machine.get_trigger_list()
            get_events(trigger_list)

    def get_network_of_virtual_event_with_no_child(self, G):
        virtual_event_no_child_set = set()
        for node_name in G.nodes:
            node = self.name_node_dict[node_name]
            if isinstance(node, VirtualEvent):
                child_nodes = self.node_connection[node]
                if len(child_nodes) == 0:
                    virtual_event_no_child_set.add(node_name)
        undirect_G = G.to_undirected()
        component_list = nx.connected_components(undirect_G)
        component_set_list = []
        for c in component_list:
            if len(virtual_event_no_child_set & set(c)) == 0:
                component_set_list.append(c)
        for component_set in component_set_list:
            for node_name in component_set:
                G.remove_node(node_name)
        pos = graphviz_layout(G, prog="neato")
        return G, pos

    def make_event_network(self, detail_flag=False):
        self.make_event_connection()
        G = nx.DiGraph()
        self.node_name_list = [
            self.node_name_dict[node] for node in self.node_connection.keys()
        ]
        G.add_nodes_from(self.node_name_list)
        for node, child_nodes in self.node_connection.items():
            name_from = self.node_name_dict[node]
            for child_node in child_nodes:
                name_to = self.node_name_dict[child_node]
                G.add_edge(name_from, name_to)
        pos = graphviz_layout(G, prog="neato")
        if not detail_flag:
            G, pos = self.get_network_of_virtual_event_with_no_child(G)
            self.node_name_list = list(G.nodes)
        self.node_color = []
        for node_name in G.nodes:
            node = self.name_node_dict[node_name]
            if isinstance(node, Trigger):
                self.node_color.append("yellow")
                continue
            if isinstance(node, VirtualEvent):
                child_nodes = self.node_connection[node]
                if len(child_nodes) == 0:
                    self.node_color.append("red")
                    continue
            self.node_color.append("white")
        return G, pos

    def draw_event_network(self, detail_flag=False, rotate_angle=0):
        fig = plt.figure()
        fig.canvas.manager.set_window_title("event network")
        ax = fig.add_subplot(111)
        G, pos = self.make_event_network(detail_flag=detail_flag)
        # draw graph
        self.scatter, edge_list = draw(
            G,
            pos,
            with_labels=False,
            width=2,
            arrows=True,
            arrowsize=20,
            node_color=self.node_color,
            node_size=300,
            edgecolors="b",
            edge_color="lightblue",
            min_source_margin=200,
            min_target_margin=200,
        )
        # set labels
        node_labels = {}
        for node_name in G.nodes:
            node_labels[node_name] = node_name

        node_labels_dict = nx.draw_networkx_labels(
            G, pos, labels=node_labels, font_size=8
        )
        for label, t in node_labels_dict.items():
            t.set_rotation(rotate_angle)

        self.fig = fig
        self.G = G
        self.pos = pos
        self.ax = ax

        if len(G.nodes) == 0:
            return fig.canvas.get_tk_widget().master

        self.annot = ax.annotate(
            "",
            xy=(0, 0),
            xytext=(20, 20),
            textcoords="offset points",
            bbox=dict(boxstyle="round", fc="w"),
            arrowprops=dict(arrowstyle="->"),
        )
        self.annot.set_visible(False)
        fig.canvas.mpl_connect("motion_notify_event", self._hover)

        self.init_figure()
        return fig.canvas.get_tk_widget().master


class ModelCheckGUI:
    """
    GUI for state machines, events, parameters of Person class.

    Constructor options
    -------------------
    person : Person

    Examples
    --------
    >>> person = Person(
            "template",
            state_machines,
            parameter_updaters,
            health_parameter,
        )
    >>> model_check_gui = ModelCheckGUI(person)
    >>> model_check_gui.show()
    """

    def __init__(self, person):
        self.person = person
        self.person.log_store.replay_reset()
        self.state_machine_figs = []
        self.last_edge = None
        self.txt = None
        self.name_txt = None
        self.type_txt = None
        self.tk_list = []
        self.mw = None
        self.ew = None
        self.pw = None

    def update_event(self, prev_event, event):
        if self.ew is None:
            return
        event_log_info = event.log_info if event is not None else None
        prev_event_log_info = prev_event.log_info if prev_event is not None else None
        self.ew.update(prev_event_log_info, event_log_info)

    def update_parameter(self, prev_parameter, parameter):
        if self.pw is None:
            return
        parameter_log_info = parameter.log_info if parameter is not None else None
        prev_parameter_log_info = (
            prev_parameter.log_info if prev_parameter is not None else None
        )
        self.pw.update(prev_parameter_log_info, parameter_log_info)

    def clear_pick(self):
        pass

    def pick_process_event_window(self, tree, item, event):
        for state_machine_fig in self.state_machine_figs:
            state_machine_fig.select(None, None, None)
        tree.tk.call(tree, "tag", "remove", "highlight")
        tree.tk.call(tree, "tag", "add", "highlight", item)
        self.mw.set_type("event")
        self.mw.set_name(event.name)
        trigger_name_list = self.ew.event_trigger_dict[event]
        desc_text = "\n".join(trigger_name_list)
        self.mw.set_desc(desc_text)

    def pick_process_diagram(self, artist, param, element, picked_state_machine_fig):
        for state_machine_fig in self.state_machine_figs:
            if picked_state_machine_fig == state_machine_fig:
                state_machine_fig.select(artist, param, element)
            else:
                state_machine_fig.select(None, None, None)
        self.ew.tree.tk.call(self.ew.tree, "tag", "remove", "highlight")

        if isinstance(element, Trigger):
            trigger = element
            sim_event = trigger.event if hasattr(trigger, "event") else None
            if sim_event is not None:
                self.mw.set_type("trigger")
                self.mw.set_name(trigger.name)
                self.mw.set_desc(sim_event.name)
            else:
                self.mw.set_type("trigger")
                self.mw.set_name(trigger.name)
                self.mw.set_desc("no event. trigger must be linked to an event.")
            return True

        if isinstance(element, State):
            state = element
            vis_log.info("show update_parameter_func: {}".format(state.name))
            self.mw.set_type("state")
            self.mw.set_name(state.name)
            if state.update_parameter_func_list is not None:
                for update_parameter_func in state.update_parameter_func_list:
                    vis_log.info("func_text")
                    func_text = inspect.getsource(update_parameter_func)
                    txt_to_print = func_text
                    self.mw.set_desc(txt_to_print)
            else:
                self.mw.set_desc("")
            return True
        return False

    def update(self):
        s_val = self.slider.val
        state, parameter, event, current_time = self.log_store.get_log(s_val)
        if state is None:
            return
        (
            prev_state,
            prev_parameter,
            prev_event,
            prev_current_time,
        ) = self.log_store.get_log(s_val - 1)
        self.textbox.set_val("(#{}) {}".format(s_val, current_time))
        print("log {}".format(s_val))
        self.log_store.print_log_info(state)
        self.log_store.print_log_info(parameter)
        self.update_parameter(prev_parameter, parameter)
        self.update_event(prev_event, event)
        if state is not None:
            for state_machine_i, state_machine_fig in enumerate(
                self.state_machine_figs
            ):
                next_state_name = state.log_info[state_machine_i + 1]
                state_machine_fig.update_state(next_state_name)
            for state_machine_fig in self.state_machine_figs:
                state_machine_fig.fig.canvas.draw()
            self.slider_fig.canvas.draw()

    def draw_slider(self):
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
        self.log_store = self.person.log_store
        self.step_max = len(self.log_store.detail_log) - 1
        step_init = 0
        step_delta = 1
        self.slider = Slider(
            ax_slider,
            "event",
            self.step_min,
            self.step_max,
            valinit=step_init,
            valstep=step_delta,
        )
        # configure TextBox
        self.textbox = TextBox(ax_textbox, "time")
        self.textbox.set_val("(#{})".format(step_init))
        # configure Button
        self.button_prev = Button(ax_button_prev, "<<")
        self.button_next = Button(ax_button_next, ">>")
        # show data
        self.update()
        self.tk_list.append(fig.canvas.get_tk_widget().master)

        fig.canvas.mpl_connect("key_press_event", self.on_press)

    def get_event_func_table(self):
        state_machines = self.person.state_machines
        total_event_set = set()
        for state_machine in state_machines:
            trigger_event_list = state_machine.get_trigger_event_list()
            for event in trigger_event_list:
                event.get_log_info_event(total_event_set)
        return get_event_func_table(total_event_set)

    def print_event_func_table(self):
        cols, header = self.get_event_func_table()
        if len(cols) == 0:
            print("no event to print")
        else:
            print(make_table(cols, header))

    def get_update_parameter_func_table(self):
        state_machines = self.person.state_machines
        total_state_set = set()
        for state_machine in state_machines:
            state_machine.get_state(total_state_set)
        return get_update_parameter_func_table(total_state_set)

    def print_update_parameter_func_table(self):
        cols, header = self.get_update_parameter_func_table()
        if len(cols) == 0:
            print("no state to print")
        else:
            print(make_table(cols, header))

    def draw_event_network(self, detail_flag=False, show=False):
        """
        Draw a network which nodes are trigger or events and which edges are dependencies.

        Parameters
        ----------
        detail_flag : bool
            False : default
                drawn network contains dependencies of virtual events not assigned.
            True :
                drawn network contains all dependencies.
        rotate_angle : float
            set angle of label
        """

        enf = EventNetworkFigure(self.person)
        tk_root = enf.draw_event_network(detail_flag=detail_flag)
        self.tk_list.append(tk_root)
        if show:
            plt.show()

    def draw_network(self):
        if self.person is None:
            return

        state_machines = self.person.state_machines
        for state_machine in state_machines:
            state_machine_fig = StateMachineFigure(state_machine)
            state_machine_fig.set_process(self.pick_process_diagram, "pick_process")
            tk_root = state_machine_fig.draw_network_state_machine()
            state_machine_fig.ax.format_coord = lambda x, y: ""
            self.state_machine_figs.append(state_machine_fig)
            self.tk_list.append(tk_root)

    def on_press(self, event):
        if event.key == "left":
            self.update_button_prev(None)
        if event.key == "right":
            self.update_button_next(None)

    def view_change(self, val):
        self.update()

    def update_button_prev(self, event):
        val = self.slider.val
        val = np.max([self.step_min, val - 1])
        self.slider.set_val(val)
        self.slider_fig.canvas.draw_idle()

    def update_button_next(self, event):
        val = self.slider.val
        val = np.min([self.step_max, val + 1])
        val = np.max([0, val])
        self.slider.set_val(val)
        self.slider_fig.canvas.draw_idle()

    def show(self, detail_flag=False):
        """
        Show state machines, events, parameters of Person class.

        Parameters
        ----------
        detail_flag : bool
            False : default
                drawn network contains dependencies of virtual events not assigned.
            True :
                drawn network contains all dependencies.
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
        self.ew = EventWindow(root)
        self.ew.init_list(self.person.log_store, self.person)
        self.ew.set_process(self.pick_process_event_window, "pick_process")
        self.tk_list.append(root)

        root = tk.Toplevel()
        self.pw = ParameterWindow(root)
        self.pw.init_list(self.person.log_store, self.person)
        self.tk_list.append(root)

        self.draw_network()
        self.draw_event_network(detail_flag=detail_flag)
        self.draw_slider()
        self.slider.on_changed(self.view_change)
        self.button_prev.on_clicked(self.update_button_prev)
        self.button_next.on_clicked(self.update_button_next)
        for tk_root in self.tk_list:
            tk_root.protocol("WM_DELETE_WINDOW", lambda: tk_destroy(tk_root))

        plt.show()
