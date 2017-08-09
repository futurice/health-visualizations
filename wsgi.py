import logging

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
logger.setLevel(logging.DEBUG if config.get('TESTING') else logging.WARN)

app = create_app()

if __name__ == '__main__':
    from wsgiref import simple_server

    httpd = simple_server.WSGIServer(
        ('', 5000),
        simple_server.WSGIRequestHandler
    )
    httpd.set_app(app)
    httpd.serve_forever()