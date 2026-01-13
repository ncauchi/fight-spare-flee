import logging
from pathlib import Path


class ColoredConsoleFormatter(logging.Formatter):

    LEVEL_COLORS = {
        'DEBUG': '\033[36m',
        'INFO': '\033[32m',
        'WARNING': '\033[33m',
        'ERROR': '\033[31m',
        'CRITICAL': '\033[35m',
    }

    NAME_COLORS = {
        'blue': '\033[94m',
        'cyan': '\033[96m',
        'green': '\033[92m',
        'yellow': '\033[93m',
        'red': '\033[91m',
        'magenta': '\033[95m',
        'white': '\033[97m',
        'gray': '\033[90m',
    }

    RESET = '\033[0m'

    def __init__(self, fmt, datefmt=None, name_color=None):
        super().__init__(fmt, datefmt)
        self.name_color = name_color

    def format(self, record):
        if record.levelname in self.LEVEL_COLORS:
            record.levelname = f"{self.LEVEL_COLORS[record.levelname]}{record.levelname}{self.RESET}"

        if self.name_color and hasattr(record, 'context_name'):
            color_code = self.NAME_COLORS.get(self.name_color, '')
            if color_code:
                record.context_name = f"{color_code}{record.context_name}{self.RESET}"

        return super().format(record)


class AppLogger:

    _shared_file_handler = None
    _log_file_setup = False

    def __init__(self, name='app', color='white'):
        '''
        Creates logger that logs to .logs/log
        
        :param name: [name] to log with message
        :param color: color of [name] can be 'blue' | 'cyan' | 'green' | 'yellow' | 'red' | 'magenta' | 'white' | 'gray'
        '''
        self.name = name
        self.color = color
        self._setup_logger()

    def _setup_logger(self):
        self._setup_shared_file_handler()
        self._setup_instance_logger()
        self._setup_console_handler()

    def _setup_shared_file_handler(self):
        if AppLogger._log_file_setup:
            return

        log_dir = Path(__file__).parent.parent / '.logs'
        log_dir.mkdir(exist_ok=True)

        log_file = log_dir / 'log.txt'
        AppLogger._shared_file_handler = logging.FileHandler(log_file, mode='a')
        AppLogger._shared_file_handler.setLevel(logging.DEBUG)

        file_formatter = logging.Formatter(
            '%(asctime)s - [%(context_name)s] - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        AppLogger._shared_file_handler.setFormatter(file_formatter)
        AppLogger._log_file_setup = True

    def _setup_instance_logger(self):
        self._logger = logging.getLogger(f'app_logger_{self.name}')
        self._logger.setLevel(logging.DEBUG)
        self._logger.propagate = False

        if AppLogger._shared_file_handler not in self._logger.handlers:
            self._logger.addHandler(AppLogger._shared_file_handler)

    def _setup_console_handler(self):
        self._console_handler = logging.StreamHandler()
        self._console_handler.setLevel(logging.DEBUG)

        console_formatter = ColoredConsoleFormatter(
            '[%(context_name)s] - %(levelname)s - %(message)s',
            name_color=self.color
        )
        self._console_handler.setFormatter(console_formatter)

    def _log_with_console(self, level, message, console):
        extra = {'context_name': self.name}

        if console and self._console_handler not in self._logger.handlers:
            self._logger.addHandler(self._console_handler)

        getattr(self._logger, level)(message, extra=extra)

        if console and self._console_handler in self._logger.handlers:
            self._logger.removeHandler(self._console_handler)

    def debug(self, message, console=False):
        self._log_with_console('debug', message, console)

    def info(self, message, console=False):
        self._log_with_console('info', message, console)

    def warning(self, message, console=False):
        self._log_with_console('warning', message, console)

    def error(self, message, console=False):
        self._log_with_console('error', message, console)

    def critical(self, message, console=False):
        self._log_with_console('critical', message, console)


if __name__ == "__main__":
    foo_logger = AppLogger(name='foo', color='blue')
    bar_logger = AppLogger(name='bar', color='red')
    db_logger = AppLogger(name='database', color='green')

    foo_logger.info("Foo is starting up")
    foo_logger.debug("Foo debug info", console=True)

    bar_logger.info("Bar is processing data")
    bar_logger.warning("Bar encountered a warning", console=True)

    db_logger.info("Database connection established")
    db_logger.error("Database query failed", console=True)

    foo_logger.critical("Foo critical issue!", console=True)
