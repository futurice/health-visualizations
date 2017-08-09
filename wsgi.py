import logging
from os import environ as env

from werkzeug.serving import run_simple

from puoback import create_app

# Add root logger
logger = logging.getLogger()
stream_hdlr = logging.StreamHandler()
stream_hdlr.setFormatter(
    logging.Formatter(
        '[%(asctime)s] [%(process)d] [%(name)s] [%(levelname)s] '
        '{%(funcName)s:%(lineno)d} %(message)s'
    )
)
logger.addHandler(stream_hdlr)
logger.setLevel(logging.DEBUG if env.get('TESTING') else logging.WARN)

app = create_app()

if __name__ == '__main__':
    run_simple.WSGIServer(
        '0.0.0.0', 5000, app, use_reloader=True, use_debugger=True
    )
