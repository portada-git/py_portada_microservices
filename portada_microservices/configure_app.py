import configparser


def configure_app():
    config = configparser.ConfigParser()
    config.read('../config/service.cfg')
    return config
