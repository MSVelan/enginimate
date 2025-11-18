import logging

import colorlog


def configure_logging():
    formatter = colorlog.ColoredFormatter(
        fmt=(
            "%(log_color)s[%(levelname)s]%(reset)s "
            "%(cyan)s%(asctime)s%(reset)s "
            "%(blue)s%(name)s%(reset)s "
            "%(white)s%(message)s%(reset)s"
        ),
        datefmt="%Y-%m-%d %H:%M:%S",
        log_colors={
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "bold_red",
        },
        secondary_log_colors={
            "asctime": {"INFO": "white"},
        },
        style="%",
    )

    handler = colorlog.StreamHandler()
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()
    root.addHandler(handler)
