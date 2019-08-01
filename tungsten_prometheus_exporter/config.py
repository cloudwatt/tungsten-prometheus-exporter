import sys

import confuse


class Dict(confuse.Template):
    def convert(self, value, view):
        if isinstance(value, dict):
            return value
        else:
            self.fail(u"must be a dict", view, True)


_metric_template = {
    "name": confuse.String(),
    "type": confuse.Choice(choices=["Enum", "Gauge"]),
    "desc": confuse.String(default=""),
    "kwargs": Dict(default={}),
    "uve_type": confuse.String(),
    "uve_module": confuse.String(),
    "uve_instances": confuse.StrSeq(default=[]),
    "json_path": confuse.String(),
    "append_field_name": confuse.Choice(choices=[True, False], default=True),
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
        "level": confuse.Choice(choices=["DEBUG", "INFO", "WARNING", "ERROR"], default="INFO")
    },
    "metrics": confuse.Sequence(_metric_template),
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
