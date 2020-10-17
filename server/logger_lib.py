import logging
import logstash


def get_logger(host, level="INFO", port=5959):
    """Create a new logger

    :return: a logger
    :rtype: logging
    """
    logger = logging.getLogger("Coalition")
    if level == "INFO":
        logger.setLevel(logging.INFO)
    elif level == "DEBUG":
        logger.setLevel(logging.DEBUG)
    elif level == "WARNING":
        logger.setLevel(logging.WARNING)
    elif level == "ERROR":
        logger.setLevel(logging.ERROR)
    elif type(level) == "int":
        logger.setLevel(level)
    else:
        raise TypeError("level value is not INFO,DEBUG, WARNING, ERROR or int")
    logger.addHandler(logstash.TCPLogstashHandler(host, port, version=1))
    return logger
