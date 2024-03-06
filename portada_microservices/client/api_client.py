import requests
import configparser
import os


def configure_app():
    p = os.path.abspath(os.path.curdir + '/config/service.cfg')
    print(p)
    configp = configparser.ConfigParser()
    configp.read(p)
    return configp


config = configure_app()
port = int(os.environ.get('PORT', config['DEFAULT']['port']))
host = config['DEFAULT']['host']
url = "http://{}}:{}/stop".format(host, port)


def stop_remote_service():
    """
    This function stop the service
    :return: None
    """
    requests.get(url)


def deskewImageFile(input_path, output_path=''):
    """
    This function read the image file passed as the first parameter,
    deskew the image and save the fixed image in output_path if it is
    not empty or using the same input_path elsewhere.
    :param input_path: path where thw image is
    :param output_path: path to be used to save teh fixed image. By default
    output_path = input_path
    :return: None
    """
    files = {'image': open(input_path, 'rb')}
    response = requests.post(url, files=files)
    if response.status_code < 400:
        if len(output_path) == 0:
            output_path = input_path
        with open(output_path, "wb") as f:
            f.write(response.content)
    elif response.status_code == 404:
        raise RuntimeError("This Microservice is not available")
    else:
        raise RuntimeError("ERROR")
