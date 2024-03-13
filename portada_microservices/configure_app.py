import configparser


def configure_app(cfg_name):
    config = configparser.ConfigParser()
    config.read(cfg_name)
    return config
