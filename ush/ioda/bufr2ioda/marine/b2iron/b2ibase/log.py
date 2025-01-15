import logging
from .util import compute_hash
import hashlib


class B2ILogger:
    def __init__(self, name, log_to_console=True, log_file=None):
        self.log_to_console = log_to_console
        self.log_file = log_file

        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)  # Set default logging level to DEBUG

        console_format = '%(message)s'
        self.console_formatter = logging.Formatter(console_format)
        self.console_handler = None

        file_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        self.file_formatter = logging.Formatter(file_format)
        self.file_handler = None

        test_file_format = '%(message)s'
        self.test_file_formatter = logging.Formatter(test_file_format)
        self.test_file_handler = None

        self.enable_logging()

    def debug(self, message):
        self.logger.debug(message)

    def info(self, message):
        self.logger.info(message)

    def warning(self, message):
        self.logger.warning(message)

    def error(self, message):
        self.logger.error(message)

    def critical(self, message):
        self.logger.critical(message)

    def disable_console_logging(self):
        if self.console_handler:
            self.logger.removeHandler(self.console_handler)

    def enable_console_logging(self):
        if not self.console_handler:
            self.console_handler = logging.StreamHandler()
            self.console_handler.setFormatter(self.console_formatter)
        self.logger.addHandler(self.console_handler)

    def disable_file_logging(self):
        if self.file_handler:
            self.logger.removeHandler(self.file_handler)

    def enable_file_logging(self):
        if not self.file_handler and self.log_file:
            self.file_handler = logging.FileHandler(self.log_file)
            self.file_handler.setFormatter(self.file_formatter)
        self.logger.addHandler(self.file_handler)

    def disable_test_file_logging(self):
        if self.test_file_handler:
            self.logger.removeHandler(self.test_file_handler)

    def enable_test_file_logging(self, test_log_file):
        if not self.test_file_handler and test_log_file:
            self.test_file_handler = logging.FileHandler(test_log_file)
            self.test_file_handler.setFormatter(self.test_file_formatter)
        self.logger.addHandler(self.test_file_handler)

    def disable_logging(self):
        self.disable_file_logging()
        self.disable_console_logging()

    def enable_logging(self):
        if self.log_file:
            self.enable_file_logging()
        if self.log_to_console:
            self.enable_console_logging()

    def log_var(self, v_name, v):
        # print(f"log_var   {v_name}, {v}")
        if isinstance(v[0], str):
            self.debug(f"{v_name}: {len(v)}, {v.dtype}")
            concatenated_string = ''.join(v)
            # Compute the hash using SHA-256
            hash_object = hashlib.sha256(concatenated_string.encode())
            hash_hex = hash_object.hexdigest()
            self.debug(f"{v_name} hash = {hash_hex}")
        else:
            self.debug(f"{v_name}: {len(v)}, {v.dtype}    min, max = {v.min()}, {v.max()}")
            self.debug(f"{v_name} hash = {compute_hash(v)}")
