import os
from dominate.tags import *
from dominate.util import raw
from markdownify import markdownify
import inspect

from .event_base import EdgeOnceEvent, TriggerControllableEvent
from .visualization import ModelCheckGUI


class ModelReport:
    """
    GUI for state machine, event, parameter of Person class.

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
        self.model_check_gui = ModelCheckGUI(person)

    def make_state_machine_report(self, state_machine_fig):
        def tag_a(event_name):
            return '<a href="#{}">{}</a>'.format(event_name, event_name)

        state_machine = state_machine_fig.state_machine
        h2(state_machine.name)
        img(src="{}.jpg".format(state_machine.name))

        html_info_table = table()
        html_info_table.set_attribute("class", "normal")
        with html_info_table.add(tbody()):
            l = tr()
            l.add(th("trigger"))
            l.add(th("state (from)"))
            l.add(th("state (to)"))
            l.add(th("event name"))
            l.add(th("event formula"))
            for _, state in state_machine.state_dict.items():
                name_from = state.name
                for name_to, trigger in state.next.items():
                    l = tr()
                    event = trigger.event
                    l.add(td(trigger.name))
                    l.add(
                        td(
                            raw(
                                '<a href="#{}_{}">{}</a>'.format(
                                    state_machine.name, name_from, name_from
                                )
                            )
                        )
                    )
                    l.add(
                        td(
                            raw(
                                '<a href="#{}_{}">{}</a>'.format(
                                    state_machine.name, name_to, name_to
                                )
                            )
                        )
                    )
                    l.add(td(event.name))
                    l.add(td(raw(event.get_event_formula(tag_a))))
            event = state_machine.reset_event
            if event is not None:
                name_to = "start"
                l = tr()
                l.add(td("reset"))
                l.add(td("-"))
                l.add(
                    td(
                        raw(
                            '<a href="#{}_{}">{}</a>'.format(
                                state_machine.name, name_to, name_to
                            )
                        )
                    )
                )
                l.add(td(event.name))
                l.add(td(raw(event.get_event_formula(tag_a))))
            event = state_machine.drop_event
            if event is not None:
                name_to = "drop"
                l = tr()
                l.add(td("drop"))
                l.add(td("-"))
                l.add(
                    td(
                        raw(
                            '<a href="#{}_{}">{}</a>'.format(
                                state_machine.name, name_to, name_to
                            )
                        )
                    )
                )
                l.add(td(event.name))
                l.add(td(raw(event.get_event_formula(tag_a))))

    def get_default_param(self, func):
        sig = inspect.signature(func)
        default_param = {}
        for arg_name, param in sig.parameters.items():
            if param is not None and type(param.default) is not type:
                default_param[arg_name] = param.default
        return default_param

    def make_event_report(self, state_machine_figs, format):
        total_event_set = set()
        for state_machine_fig in state_machine_figs:
            state_machine = state_machine_fig.state_machine
            trigger_event_list = state_machine.get_trigger_event_list()
            for event in trigger_event_list:
                event.get_log_info_event(total_event_set)
        h2("Event")
        html_info_table = table()
        html_info_table.set_attribute("class", "normal")
        info_header_title = "event info"
        if format == "md":
            info_header_title += " (some information omitted in md file)"
        with html_info_table.add(tbody()):
            l = tr()
            l.add(th("event name"))
            l.add(th("event type"))
            l.add(th(info_header_title))
            for event in total_event_set:
                if not isinstance(event, TriggerControllableEvent):
                    continue
                if isinstance(event, EdgeOnceEvent):
                    continue
                l = tr()
                l.add(td(raw('<div id="{}">{}</div>'.format(event.name, event.name))))
                l.add(td(event.__class__.__name__))
                info_text, info_func = event.get_info()
                text = ""
                if format == "html":
                    if len(info_text) > 0:
                        text += info_text
                    if info_func is not None:
                        text += "<p>function</br><code>{}</code></p>".format(
                            inspect.getsource(info_func)
                        )
                        default_param = self.get_default_param(info_func)
                        param_text = ", ".join(
                            [
                                "{}={}".format(*arg_param)
                                for arg_param in default_param.items()
                            ]
                        )
                        if len(param_text) > 0:
                            text += (
                                "<p>default parameter</br><code>{}</code></p>".format(
                                    param_text
                                )
                            )
                l.add(td(raw(text)))

    def make_state_report(self, state_machine_figs, format):
        total_state_set = set()
        for state_machine_fig in state_machine_figs:
            state_machine = state_machine_fig.state_machine
            state_machine.get_state(total_state_set)

        h2("State")
        html_info_table = table()
        html_info_table.set_attribute("class", "normal")
        info_header_title = "state info and update parameter func"
        if format == "md":
            info_header_title += " (some information omitted in md file)"
        with html_info_table.add(tbody()):
            l = tr()
            l.add(th("state machine"))
            l.add(th("state name"))
            l.add(th(info_header_title))
            for state in total_state_set:
                if len(state.update_parameter_func_list) == 0:
                    l = tr()
                    l.add(td(state.state_machine.name))
                    l.add(
                        td(
                            raw(
                                '<div id="{}_{}">{}</div>'.format(
                                    state.state_machine.name, state.name, state.name
                                )
                            )
                        )
                    )
                    l.add(td(""))
                    continue
                for info_func in state.update_parameter_func_list:
                    l = tr()
                    l.add(td(state.state_machine.name))
                    l.add(
                        td(
                            raw(
                                '<div id="{}_{}">{}</div>'.format(
                                    state.state_machine.name, state.name, state.name
                                )
                            )
                        )
                    )
                    text = ""
                    if format == "html":
                        text += "<p>function</br><code>{}</code></p>".format(
                            inspect.getsource(info_func)
                        )
                        default_param = self.get_default_param(info_func)
                        param_text = ", ".join(
                            [
                                "{}={}".format(*arg_param)
                                for arg_param in default_param.items()
                            ]
                        )
                        if len(param_text) > 0:
                            text += (
                                "<p>default parameter</br><code>{}</code></p>".format(
                                    param_text
                                )
                            )
                    l.add(td(raw(text)))

    def make_event_func_report(self):
        h2("event func")
        cols, header = self.model_check_gui.get_event_func_table()
        html_info_table = table()
        html_info_table.set_attribute("class", "normal")
        with html_info_table.add(tbody()):
            l = tr()
            for text in header:
                l.add(td(text))
            for col in cols:
                l = tr()
                for row in col:
                    l.add(td("None" if row is None else row))

    def make_update_parameter_func_report(self):
        h2("update parameter func")
        cols, header = self.model_check_gui.get_update_parameter_func_table()
        html_info_table = table()
        html_info_table.set_attribute("class", "normal")
        with html_info_table.add(tbody()):
            l = tr()
            for text in header:
                l.add(td(text))
            for col in cols:
                l = tr()
                for row in col:
                    l.add(td("None" if row is None else row))

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
        self.model_check_gui.draw_network()
        state_machine_figs = self.model_check_gui.state_machine_figs

        for state_machine_fig in state_machine_figs:
            pic_filename = "{}.jpg".format(state_machine_fig.name)
            pic_output_path = os.path.join(output_path, pic_filename)
            state_machine_fig.fig.savefig(pic_output_path)

        h = html()
        if format is "html":
            self._add_head_style(h)
        with h.add(body()).add(div(id="content")):
            h1("Model Report")
            for state_machine_fig in state_machine_figs:
                self.make_state_machine_report(state_machine_fig)
            self.make_event_report(state_machine_figs, format)
            self.make_state_report(state_machine_figs, format)

        output_str = str(h)
        if format is "md":
            output_str = markdownify(output_str, heading_style="ATX")

        html_filename = "model_report.{}".format(format)
        html_output_path = os.path.join(output_path, html_filename)

        with open(html_output_path, mode="w") as f:
            f.write(output_str)
