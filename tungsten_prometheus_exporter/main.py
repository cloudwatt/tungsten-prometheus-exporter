from gevent import monkey

monkey.patch_all()

import os.path
import logging
import argparse

import confuse
from prometheus_client import start_http_server

from tungsten_prometheus_exporter.metric import MetricCollection
from tungsten_prometheus_exporter.config import Config


def filename(string):
    if not os.path.exists(string):
        raise argparse.ArgumentTypeError("%s does not exists" % string)
    if not os.path.isfile(string):
        raise argparse.ArgumentTypeError("%s isn't a file" % string)
    return string


def main():
    parser = argparse.ArgumentParser(prog="tungsten-prometheus-exporter")
    parser.add_argument(
        "--config",
        type=filename,
        default=os.environ.get("TUNGSTEN_PROMETHEUS_EXPORTER_CONFIG"),
    )
    args = parser.parse_args()
    if args.config:
        Config().set_file(args.config)
    start_http_server(port=Config().prometheus.port)
    logging_format = '%(asctime)-15s:%(levelname)s:%(module)s:%(message)s'
    logging.basicConfig(level=Config().logging.level, format=logging_format)
    collection = MetricCollection()
    collection.scrape()


if __name__ == "__main__":
    main()