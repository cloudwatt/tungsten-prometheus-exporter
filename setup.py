from setuptools import setup, find_packages


setup(
    name="tungsten-prometheus-exporter",
    version="0.1.2",
    description="Scrape TungstenFabric/OpenContrail analytics UVEs and provide prometheus endpoint",
    author="Jean-Philippe Braun",
    author_email="jean-philippe.braun@orange.com",
    maintainer="Jean-Philippe Braun",
    maintainer_email="jean-philippe.braun@orange.com",
    url="http://www.github.com/cloudwatt/tungsten-prometheus-exporter",
    packages=find_packages(),
    install_requires=[
        "requests",
        "prometheus_client~=0.7.0",
        "jsonpath-rw~=1.4.0",
        "confuse",
        "gevent~=1.4.0",
        "keystoneauth1~=3.15.0",
    ],
    scripts=[],
    license="MIT",
    entry_points={
        "console_scripts": [
            "tungsten-prometheus-exporter = tungsten_prometheus_exporter.main:main"
        ]
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: System Administrators",
        "Topic :: System :: Monitoring",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.7",
    ],
)
