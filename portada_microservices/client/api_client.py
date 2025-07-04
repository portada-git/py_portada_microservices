import base64
# from os import terminal_size

import requests
import os
import re

# from cv2.gapi.ie import params
# from flask import jsonify


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
        imgdata = base64.b64decode(response.json()['response']['image'])
        with open(output_path, "wb") as f:
            f.write(imgdata)
    elif response.status_code == 404:
        raise RuntimeError("This Microservice is not available")
    else:
        raise RuntimeError("ERROR")


def test_yolo_paragraph_process(input_path:str, output_path=''):
    redraw_url = "{}{}".format(config.url, "testParagraphImageFile")
    files = {'image': open(input_path, 'rb')}
    response = requests.post(redraw_url, files=files)
    if response.status_code < 400:
        if len(output_path) == 0:
            output_path = input_path
        imgdata = base64.b64decode(response.json()['response']['image'])
        with open(output_path, "wb") as f:
            f.write(imgdata)
        with open(output_path, "wb") as f:
            f.write(response.content)
    elif response.status_code == 404:
        raise RuntimeError("This Microservice is not available")
    else:
        raise RuntimeError("ERROR")

def extract_with_openai(team:str, text:str, config_json):
    extract_url = "{}{}".format(config.url, "pr/extract_with_openai")
    params = {
        'team': team,
        'config_json':config_json,
        'text': text
    }
    response = requests.post(extract_url, json=params)
    if response.status_code < 400:
        return response.json()
    elif response.status_code == 404:
        raise RuntimeError("This Microservice is not available")
    else:
        raise RuntimeError("ERROR")

def _get_text_from_images(images, team, config_json=None):
    extract_url = "{}{}".format(config.url, "pr/get_text_from_images")
    if config_json is None:
        params = {
            'team': team,
            'images':images
        }
    else:
        params ={
            'team':team,
            'config_json':config_json,
            'images': images
        }
    response = requests.post(extract_url, json=params)
    if response.status_code < 400:
        return response.json()
    elif response.status_code == 404:
        raise RuntimeError("This Microservice is not available")
    else:
        raise RuntimeError("ERROR")

def get_text_from_images(out_dir, images_dir, team, config_json=None):
    patron = re.compile(r'(\d{4}_\d{2}_\d{2}_[A-Z]{3}_[A-Z]{2}_[A-Z]_\d{2})_?\d{0,3}\.(jpg|txt)')
    files = os.listdir(images_dir)
    files = sorted(files)
    base_nombre = text = ""
    images = []
    for file in files:
        match = patron.match(file)
        if match:
            if base_nombre != match.group(1):
                if images:
                    try:
                        response_json = _get_text_from_images(images, team, config_json)
                        if response_json["status"]==0:
                            with open(os.path.join(out_dir, base_nombre + ".txt"), "w") as f:
                                f.write(response_json["text"])
                        else:
                            print("Error: "+response_json["error_message"])
                    except Exception as e:
                        print(f"Error al escribir en {file}: {e}")
                base_nombre = match.group(1)  # Nombre base sin los últimos 3 dígitos
                images = []
            if file.lower().endswith(".jpg"):
                try:
                    with open(os.path.join(images_dir, file), "rb") as i:
                        imagen_bytes = i.read()
                except Exception as e:
                    print(f"Error al leer {file}: {e}")
                images.append({
                    "mime_type": "image/jpeg",
                    "image": base64.b64encode(imagen_bytes).decode('utf-8')
                })


