"""
This module provides utilities for loading and parsing configuration files for the AlertMagnet application.

Functions:
    load_config(config_file: str) -> dict:
        Loads the configuration from the specified file and parses it into a dictionary.

Exceptions:
    ConfigFileNotExistsError:
        Raised when the specified configuration file does not exist.
    InvalidConfigValueError:
        Raised when a configuration value is invalid.
    RequiredConfigKeyNotFound:
        Raised when a required configuration key is not found in the configuration file.
"""

import configparser
import logging
import os

from utilities.errors import ConfigFileNotExistsError, InvalidConfigValueError, RequiredConfigKeyNotFound


def load_config(config_file: str):
    if not os.path.isfile(config_file):
        raise ConfigFileNotExistsError()

    config = configparser.ConfigParser()
    config.read(config_file)

    conf = dict(config.items("AlertMagnet"))

    __parse_config(conf)

    return conf


def __parse_config(conf: dict):
    try:
        if conf["api_endpoint"] == "":
            raise RequiredConfigKeyNotFound("The config key 'api_endpoint' is required.")

        if conf["timeout"] == "":
            conf["timeout"] = 30
        else:
            conf["timeout"] = int(conf["timeout"])

        if conf["threshold"] == "":
            conf["threshold"] = None
        else:
            conf["threshold"] = int(conf["threshold"])

        if conf["delay"] == "":
            conf["delay"] = 0.25
        else:
            conf["delay"] = float(conf["delay"])

        if conf["cores"] == "":
            conf["cores"] = 12
        else:
            conf["cores"] = int(conf["cores"])

        if conf["max_long_term_storage"] == "":
            conf["max_long_term_storage"] = "1y"

        if conf["prometheus_port"] == "":
            conf["prometheus_port"] = 8123
        else:
            conf["prometheus_port"] = int(conf["prometheus_port"])

        if conf["naptime_seconds"] == "":
            conf["naptime_seconds"] = 86400
        else:
            conf["naptime_seconds"] = int(conf["naptime_seconds"])

        if conf["log_to_file"].lower() == "true":
            conf["log_to_file"] = True
        else:
            conf["log_to_file"] = False

        match conf["log_level"]:
            case "DEBUG":
                conf["log_level"] = logging.DEBUG
            case "INFO":
                conf["log_level"] = logging.INFO
            case "WARNING":
                conf["log_level"] = logging.WARNING
            case "ERROR":
                conf["log_level"] = logging.ERROR
            case "CRITICAL":
                conf["log_level"] = logging.CRITICAL
            case _:
                raise InvalidConfigValueError(f"Invalid value {conf['log_level']} for 'log_level' in config file.")

    except KeyError as e:
        raise KeyError(f"Missing configuration parameter: {e}") from e
