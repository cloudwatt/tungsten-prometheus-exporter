import logging
import random

import gevent
from gevent import Greenlet, GreenletExit
from prometheus_client import Counter, Summary, Gauge
from requests.models import Response
from requests.exceptions import RequestException

from tungsten_prometheus_exporter.config import Config

logger = logging.getLogger(__name__)

scrape_retries = Counter("scrape_retries_count", "Retries count while scraping data")
scrape_errors = Counter("scrape_errors_count", "Errors count while scraping data")
scrape_time = Summary("scrape_fetch_seconds", "Time spent scraping data")
scrape_pool_size = Gauge("scrape_pool_size", "Number of scrapes to be run or running")


class StopScrape(GreenletExit):
    pass


class Scraper(Greenlet):
    def __init__(self, session, pool, url, metrics, wait=True):
        super().__init__()
        logger.info("Init scraper for %s" % url)
        self.session = session
        self.pool = pool
        self.url = url
        self.metrics = metrics
        self.wait = wait

    def _run(self):
        if self.wait:
            gevent.sleep(random.randint(0, Config().scraper.interval * 0.75))
        while True:
            scrape_pool_size.inc()
            r = self.pool.apply(self._request)
            scrape_pool_size.dec()
            if isinstance(r, Response):
                r.raise_for_status()
                for m in self.metrics:
                    m.update(r.json())
            elif isinstance(r, StopScrape):
                return
            gevent.sleep(Config().scraper.interval)

    @scrape_time.time()
    def _request(self):
        try:
            r = self.session.get(self.url, timeout=Config().scraper.timeout)
            scrape_retries.inc(Config().scraper.max_retry - r.raw.retries.total)
        except RequestException as e:
            scrape_errors.inc(1)
            logger.error("Failed to scrape: %s" % e)
            return
        return r
