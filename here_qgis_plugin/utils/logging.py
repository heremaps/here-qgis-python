###############################################################################
#
# Copyright (c) 2023 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

import gzip
import logging
import os
import shutil
import sys
from logging.handlers import QueueHandler, QueueListener, RotatingFileHandler
from queue import Queue

from ..config import LOG_FILE, LOG_FILE_NAME


def archive_log_file():
    base, _ = os.path.split(LOG_FILE)
    idx_offset = len([s for s in os.listdir(base) if s.endswith(".gz")])
    for idx, log_file in enumerate(
        reversed(
            [
                s
                for s in os.listdir(base)
                if not s.endswith(".gz") and s.startswith("{}.".format(LOG_FILE_NAME))
            ]
        )
    ):
        log_path = os.path.join(base, log_file)
        archive_path = os.path.join(
            base, "{name}.{idx}.gz".format(name=LOG_FILE_NAME, idx=idx + idx_offset)
        )
        with open(log_path, "rb") as f_in:
            with gzip.open(archive_path, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
        os.remove(log_path)


def setup_logger(level=logging.INFO):
    archive_log_file()
    logger_ = logging.getLogger()
    logger_.setLevel(level)

    formatter = logging.Formatter(
        "%(asctime)s %(name)-12s %(levelname)-8s %(message)s "
    )
    # formatter = logging.Formatter("%(asctime)s %(name)-12s %(levelname)-8s "
    #                               "%(message)s (%(filename)s:%(lineno)d)")
    # formatter = logging.Formatter("%(relativeCreated)6d %(threadName)s "
    #                               "%(message)s")

    queue = Queue(-1)  # no limit on size
    queue_handler = QueueHandler(queue)
    listener = QueueListener(
        queue,
        RotatingFileHandler(
            LOG_FILE, encoding="utf-8", maxBytes=1024**2, backupCount=5
        ),
        logging.StreamHandler(sys.stdout),
    )
    for h in logger_.handlers:
        logger_.removeHandler(h)
    queue_handler.setFormatter(formatter)
    logger_.addHandler(queue_handler)

    # Fix EOFError in multiprocessing
    # https://stackoverflow.com/questions/49209385/eof-error-at-program-exit-using-multiprocessing-queue-and-thread
    import atexit

    atexit.register(listener.stop)

    listener.start()
    return logger_


def get_logger(name: str = None, level=logging.INFO):
    logger_ = logging.getLogger(name)
    logger_.setLevel(level)
    return logger_
