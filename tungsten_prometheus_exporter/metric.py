from collections import UserList, UserDict
import logging

from gevent.pool import Pool, Group

import requests
from requests.packages.urllib3.util import Retry
from requests.adapters import HTTPAdapter

from keystoneauth1.session import Session

from jsonpath_rw import parse, Fields
from prometheus_client import Enum

from tungsten_prometheus_exporter.utils import my_import
from tungsten_prometheus_exporter.scrape import Scraper, StopScrape
from tungsten_prometheus_exporter.config import Config


METRIC_NAME_PREFIX = "tungsten"
METRICS_REGISTRY = {}

logger = logging.getLogger(__name__)


# Function to get the first attributes of a JSON path expression
# Theses attributes are used in the query filter to analytics API
def _find_attributes(path_expr):
    if isinstance(path_expr, Fields):
        return path_expr.fields
    return _find_attributes(path_expr.left)


class MetricInstance:
    def __init__(
        self,
        name,
        type,
        desc,
        uve_type,
        uve_module,
        json_path,
        uve_instance,
        labels_from_path={},
        append_field_name=True,
        kwargs={},
    ):
        self.host = Config().analytics.host
        self.base_url = Config().analytics.base_url

        self.name = name
        self.type = type
        self.desc = desc
        self.uve_type = uve_type
        self.uve_module = uve_module
        self.uve_instance = uve_instance
        self.json_path = json_path
        self.labels_from_path = labels_from_path
        self.append_field_name = append_field_name
        self.kwargs = kwargs

        self._metric_class = my_import("prometheus_client.%s" % type)
        self._path_expr = parse(json_path)
        self.uve_attributes = _find_attributes(self._path_expr)
        self._labels = [uve_type.replace("-", "_")] + [
            l for l, _ in labels_from_path.items()
        ]

    def _metric_name(self, match):
        if self.append_field_name:
            return "%s_%s_%s" % (METRIC_NAME_PREFIX, self.name, match.path)
        return "%s_%s" % (METRIC_NAME_PREFIX, self.name)

    def _get_metric(self, match):
        metric_name = self._metric_name(match)
        if metric_name not in METRICS_REGISTRY:
            METRICS_REGISTRY[metric_name] = self._metric_class(
                metric_name, self.desc, self._labels, **self.kwargs
            )
        return METRICS_REGISTRY[metric_name]

    def _update_metric(self, match, labels):
        metric = self._get_metric(match)
        for label, index in self.labels_from_path.items():
            labels.append((label, str(match.full_path).split(".")[index]))
        if isinstance(metric, Enum):
            metric.labels(**dict(labels)).state(match.value)
        else:
            metric.labels(**dict(labels)).set(match.value)

    # called from instance scraper
    def update(self, data):
        if self.uve_module in data:
            labels = [(self.uve_type.replace("-", "_"), self.uve_instance)]
            for match in self._path_expr.find(data[self.uve_module]):
                self._update_metric(match, labels)
        else:
            logger.warning("No match of %s on %s" % (self.json_path, self.url))

    @property
    def url(self):
        filters = set()
        for attr in self.uve_attributes:
            filters.add("%s:%s" % (self.uve_module, attr))
        return "%s%s/%s/%s?flat&cfilt=%s" % (
            self.host,
            self.base_url,
            self.uve_type,
            self.uve_instance,
            ",".join(filters),
        )

    def __repr__(self):
        return "MetricInstance(%s/%s:%s.%s)" % (
            self.uve_type,
            self.uve_instance,
            self.uve_module,
            self.json_path,
        )


class MetricTypeCollection(UserDict):
    """
    MetricTypeCollection scrape the UVE type page and for each instance that
    match the configuration:

        * create a MetricInstance for each metric_config
        * create a Scraper that will update the instance metrics
    """
    def __init__(self, session, uve_type, metric_configs, scrapers, scrape_pool):
        super().__init__()
        self.host = Config().analytics.host
        self.base_url = Config().analytics.base_url
        self.session = session
        self.uve_type = uve_type
        self.metric_configs = metric_configs
        self.scrapers = scrapers
        self.scrape_pool = scrape_pool

        self.to_scrape = []
        for metric_config in metric_configs:
            for uve_instance in metric_config.uve_instances:
                self.to_scrape.append(uve_instance)

    @property
    def url(self):
        return "%s%s/%ss" % (self.host, self.base_url, self.uve_type)

    def scrape(self):
        self.scrapers.start(Scraper(self.session, self.scrape_pool, self.url, [self], wait=False))

    def _to_metric(self, metric_config, instance):
        new_config = metric_config
        if "uve_instances" in new_config:
            del new_config["uve_instances"]
        new_config["uve_instance"] = instance
        return MetricInstance(**new_config)

    def update(self, data):
        instances = [instance["name"] for instance in data]
        for instance in instances:
            if self.to_scrape and instance not in self.to_scrape:
                continue
            if instance not in self:
                metrics = [
                    self._to_metric(metric_config, instance)
                    for metric_config in self.metric_configs
                ]
                scraper = self.scrapers.start(
                    Scraper(
                        self.session,
                        self.scrape_pool,
                        self.instance_url(instance, metrics),
                        metrics,
                    )
                )
                self[instance] = {"metrics": metrics, "scraper": scraper}
        for instance in self:
            if instance not in instances:
                logger.info("Removing scraper of %s" % instance)
                del self[instance]

    def instance_url(self, instance, metrics):
        filters = set()
        for m in metrics:
            for attr in m.uve_attributes:
                filters.add("%s:%s" % (m.uve_module, attr))
        return "%s%s/%s/%s?flat&cfilt=%s" % (
            self.host,
            self.base_url,
            self.uve_type,
            instance,
            ",".join(filters),
        )


class MetricCollection(UserList):
    """
    MetricCollection aggregates all metrics from config by uve_type.

    For each uve_type a MetricTypeCollection class is created.
    """
    def __init__(self, auth=None):
        super().__init__()
        self.scrapers = Group()
        self.scrape_pool = Pool(size=Config().scraper.pool_size)
        self.session = Session(auth=auth)
        self.session.mount(
            "http://",
            HTTPAdapter(
                max_retries=Retry(
                    total=Config().scraper.max_retry,
                    connect=Config().scraper.max_retry,
                    read=Config().scraper.max_retry,
                    backoff_factor=0.3,
                ),
                pool_connections=10,
            ),
        )
        metric_types = {}
        for metric_config in Config().metrics:
            if metric_config.uve_type not in metric_types:
                metric_types[metric_config.uve_type] = []
            metric_types[metric_config.uve_type].append(metric_config)
        for uve_type, metric_configs in metric_types.items():
            self.append(
                MetricTypeCollection(
                    self.session,
                    uve_type,
                    metric_configs,
                    self.scrapers,
                    self.scrape_pool,
                )
            )

    def scrape(self):
        for instance in self:
            instance.scrape()
        try:
            self.scrapers.join()
        except KeyboardInterrupt:
            self.scrape_pool.kill(StopScrape)
            self.scrapers.kill(StopScrape)
        return
