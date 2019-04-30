import sys
import collections

import confuse

try:
    import enum

    SUPPORTS_ENUM = True
except ImportError:
    SUPPORTS_ENUM = False


class Sequence(confuse.Template):
    """A template used to validate lists of similar items,
    based on a given subtemplate.
    """

    def __init__(self, subtemplate):
        """Create a template for a list with items validated
        on a given subtemplate.
        """
        self.subtemplate = confuse.as_template(subtemplate)

    def value(self, view, template=None):
        """Get a list of items validated against the template.
        """
        out = []
        for item in view:
            out.append(self.subtemplate.value(item, self))
        return out

    def __repr__(self):
        return "Sequence({0})".format(repr(self.subtemplate))


class Choice(confuse.Template):
    """A template that permits values from a sequence of choices.
    """

    def __init__(self, choices, default=confuse.REQUIRED):
        """Create a template that validates any of the values from the
        iterable `choices`.

        If `choices` is a map, then the corresponding value is emitted.
        Otherwise, the value itself is emitted.

        If `choices` is a `Enum`, then the enum entry with the value is
        emitted.
        """
        super(Choice, self).__init__(default)
        self.choices = choices

    def convert(self, value, view):
        """Ensure that the value is among the choices (and remap if the
        choices are a mapping).
        """
        if (
            SUPPORTS_ENUM
            and isinstance(self.choices, type)
            and issubclass(self.choices, enum.Enum)
        ):
            try:
                return self.choices(value)
            except ValueError:
                self.fail(
                    u"must be one of {0!r}, not {1!r}".format(
                        [c.value for c in self.choices], value
                    ),
                    view,
                )

        if value not in self.choices:
            self.fail(
                u"must be one of {0!r}, not {1!r}".format(list(self.choices), value),
                view,
            )

        if isinstance(self.choices, collections.Mapping):
            return self.choices[value]
        else:
            return value

    def __repr__(self):
        return "Choice({0!r})".format(self.choices)


class Dict(confuse.Template):
    def convert(self, value, view):
        if isinstance(value, dict):
            return value
        else:
            self.fail(u"must be a dict", view, True)


_metric_template = {
    "name": confuse.String(),
    "type": Choice(choices=["Enum", "Gauge"]),
    "desc": confuse.String(default=""),
    "kwargs": Dict(default={}),
    "uve_type": confuse.String(),
    "uve_module": confuse.String(),
    "uve_instances": confuse.StrSeq(default=[]),
    "json_path": confuse.String(),
    "append_field_name": Choice(choices=[True, False], default=True),
    "labels_from_path": Dict(default={}),
}

_global_template = {
    "analytics": {
        "host": confuse.String(pattern=r"^https?://"),
        "base_url": confuse.String(pattern=r"^/", default="/analytics/uves"),
    },
    "prometheus": {
        "port": confuse.Integer(default=8080),
        "metric_name_prefix": confuse.String(default="tungsten"),
    },
    "scraper": {
        "max_retry": confuse.Integer(default=3),
        "timeout": confuse.Integer(default=1),
        "pool_size": confuse.Integer(default=10),
        "interval": confuse.Integer(default=60),
    },
    "logging": {
        "level": Choice(choices=["DEBUG", "INFO", "WARNING", "ERROR"], default="INFO")
    },
    "metrics": Sequence(_metric_template),
}


class Config:
    instance = None

    class __Config:
        def __init__(self):
            self.config = confuse.LazyConfig("tungsten-prometheus-exporter", __name__)

        def render(self):
            try:
                self.rendered_config = self.config.get(_global_template)
            except confuse.ConfigError as e:
                print("Configuration error: %s" % e)
                sys.exit(1)

    def __init__(self):
        if not Config.instance:
            Config.instance = Config.__Config()

    def set(self, args):
        self.instance.config.add(args)

    def set_file(self, filename):
        self.instance.config.set_file(filename)

    def render(self):
        self.instance.render()

    def __getattr__(self, name):
        if not hasattr(self.instance, "rendered_config"):
            print("Missing configuration")
            sys.exit(1)
        return getattr(self.instance.rendered_config, name)
