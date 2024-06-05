from os import terminal_size

import requests
import os

from cv2.gapi.ie import params


class RequestConfig(object):
    def __init__(self):
        self.__url = "http://localhost/"

    @property
    def url(self):
        return self.__url

    @url.setter
    def url(self, v):
        self.__url = v


config = RequestConfig()


def request_configure(host, port, pref=''):
    if len(pref) > 0 and pref[-1] != '/':
        pref = pref + "/"
    url = "http://{}:{}/{}".format(host, port, pref)
    config.url = url


def dewrap_image_file(input_path, output_path=''):
    """
    This function read the image file passed as the first parameter,
    dewrop the image and save the fixed image in output_path if it is
    not empty or using the same input_path elsewhere.
    :param input_path: path where thw image is
    :param output_path: path to be used to save teh fixed image. By default
    output_path = input_path
    :return: None
    """
    tool_url = "{}{}".format(config.url, "dewarpImageFile")
    files = {'image': open(input_path, 'rb')}
    response = requests.post(tool_url, files=files)
    if response.status_code < 400:
        if len(output_path) == 0:
            output_path = input_path
        with open(output_path, "wb") as f:
            f.write(response.content)
    elif response.status_code == 404:
        raise RuntimeError("This Microservice is not available")
    else:
        raise RuntimeError("ERROR")


def deskew_image_file(input_path, output_path=''):
    """
    This function read the image file passed as the first parameter,
    deskew the image and save the fixed image in output_path if it is
    not empty or using the same input_path elsewhere.
    :param input_path: path where thw image is
    :param output_path: path to be used to save teh fixed image. By default
    output_path = input_path
    :return: None
    """
    deskew_url = "{}{}".format(config.url, "deskewImageFile")
    files = {'image': open(input_path, 'rb')}
    response = requests.post(deskew_url, files=files)
    if response.status_code < 400:
        if len(output_path) == 0:
            output_path = input_path
        with open(output_path, "wb") as f:
            f.write(response.content)
    elif response.status_code == 404:
        raise RuntimeError("This Microservice is not available")
    else:
        raise RuntimeError("ERROR")


def redraw_ordered_image(team:str, input_path:str, output_path=''):
    redraw_url = "{}{}".format(config.url, "redrawOrderedImageFile")
    params = {
        'team': team
    }
    files = {'image': open(input_path, 'rb')}
    response = requests.post(redraw_url, data=params, files=files)
    if response.status_code < 400:
        if len(output_path) == 0:
            output_path = input_path
        with open(output_path, "wb") as f:
            f.write(response.content)
    elif response.status_code == 404:
        raise RuntimeError("This Microservice is not available")
    else:
        raise RuntimeError("ERROR")

