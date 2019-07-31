from gevent import monkey

monkey.patch_all()

import sys
import os.path
import logging
import argparse

import confuse
from prometheus_client import start_http_server

from keystoneauth1.loading import cli as kcli

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
    parser.add_argument(
        "--host",
        type=str,
        default=os.environ.get("TUNGSTEN_PROMETHEUS_EXPORTER_ANALYTICS_HOST"),
    )
    argv = sys.argv[1:]
    kcli.register_argparse_arguments(parser, argv, default=None)
    args = parser.parse_args()
    auth = None
    if args.os_auth_type is not None:
        auth = kcli.load_from_argparse_arguments(args)
    if args.config:
        Config().set_file(args.config)
    if args.host:
        Config().set({'analytics': {'host': args.host}})
    Config().render()
    start_http_server(port=Config().prometheus.port)
    logging_format = '%(asctime)-15s:%(levelname)s:%(module)s:%(message)s'
    logging.basicConfig(level=Config().logging.level, format=logging_format)
    collection = MetricCollection(auth=auth)
    collection.scrape()


if __name__ == "__main__":
    main()
