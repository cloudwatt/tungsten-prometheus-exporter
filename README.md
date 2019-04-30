tungsten-prometheus-exporter
============================

A simple prometheus exporter for OpenContrail/TungstenFabric.

Usage
-----

```bash
$ tungsten-prometheus-exporter --config /path/to/config.yml
or
$ TUNGSTEN_PROMETHEUS_EXPORTER=/path/to/config.yml tungsten-prometheus-exporter
```

Metrics are available on port `8080` by default.

Configuration
-------------

Configuration is provided as a yaml file.

You should at least configure `analytics.host` and `metrics`.

Analytics host can be configured with the `--host` option or
`TUNGSTEN_PROMETHEUS_EXPORTER_ANALYTICS_HOST` env variable.

Configuration file location can be configured with the `--config` option or
`TUNGSTEN_PROMETHEUS_EXPORTER_CONFIG` env variable.

Other configuration options are described below with default values for
reference.

### Section `analytics`

```yaml
analytics:
  host: http://ANALYTICS_API:8081
  base_url: /analytics/uves
```

### Section `prometheus`

Define port of metrics endpoint and prefix for all metric names.

Default settings:

```yaml
prometheus:
  port: 8080
  metric_name_prefix: "tungsten"
```

### Section `logging`

Defines the pyhon logging level of `tungsten-prometheus-exporter`.

Default settings:

```yaml
logging:
  level: INFO
```

### Section `scraper`

Settings for scraper workers that will fetch data from analytics API.

Default settings:

```yaml
scraper:
  max_retry: 3      # number of retries when an http call fails
  timeout: 1        # http timeout in seconds
  pool_size: 10     # maximum number of concurrent http calls
  interval: 60      # wait time in seconds between scrapes
```

### Section `metrics`

Describes the list of metrics to export.

A metric is described with the following attributes:

 * name: base name of the metric
 * type: prometheus metric type (eg: Gauge, Enum)
 * uve_type: uve type to fetch (eg: vrouter, bgp-peer...)
 * uve_module: uve module data to fetch (eg: NodeStatus...)
 * uve_instances: list of instances (default: `*`)
 * json_path: a JSON path expression to target the metric in the json
 * labels_from_path: add metric labels based on the attribute path
 * append_field_name: append the target attribute to the metric name (default: `true`)

Look at `./examples` directory for metrics examples.

#### Vrouters drop stats example

```yaml
metrics:
  - name: vrouter_drop_stats
    type: Gauge
    uve_type: vrouter
    uve_module: VrouterStatsAgent
    json_path: drop_stats.*
```

This will scrape the url `http://ANALYTICS_IP:8081/analytics/uves/vrouter/*?flat&cfilt=VrouterStatsAgent`.

The returned json will contain:

```json
{
  "VrouterStatsAgent": {
    "drop_stats": {
      "ds_rewrite_fail": 0,
      "ds_mcast_df_bit": 0,
      "ds_flow_no_memory": 0,
      "ds_push": 0,
      ...
    }
  }
}
```

Because of `json_path` for every attribute in the `drop_stats` object a
prometheus gauge will be created:

  * vrouter_drop_stats_ds_rewrite_fail
  * vrouter_drop_stats_ds_mcast_df_bit
  * ...
