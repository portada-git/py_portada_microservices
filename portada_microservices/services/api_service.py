import base64
from functools import wraps
from pathlib import Path
from py_extractor_calculators.sm import get_arrival_date_from_publication_date as sm_get_arrival_date_from_publication_date
from py_extractor_calculators.sm import get_departure_date as sm_get_departure_date
from py_extractor_calculators.sm import get_duration_value as sm_get_duration_value
from py_extractor_calculators.sm import get_quarantine as sm_get_quarantine
from py_extractor_calculators.sm import get_port_of_call_list as sm_get_port_of_call_list

import cv2
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from flask import Flask, jsonify, request, send_file, after_this_request, session
from flask_reuploads import UploadSet, IMAGES, configure_uploads
from huggingface_hub.hf_api import api
# from numpy.distutils.command.config import config
# from pip._internal import req
from py_portada_image.deskew_tools import DeskewTool
from py_portada_image.dewarp_tools import DewarpTools
from werkzeug.utils import secure_filename
import os
from py_portada_paragraphs import PortadaParagraphCutter
from py_portada_order_blocks import PortadaRedrawImageForOcr
import json
import uuid
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from py_openai_extractor import AutonewsExtractorAdaptor, AutonewsExtractorAdaptorBuilder
from py_portada_order_blocks import decrypt
from py_openai_extractor import QwenOcrProcessor, QwenOcrCorrector


def __add_public_key(team, public_key):
    if team not in pkt:
        pkt[team] = []

    pkt[team].append(public_key)


def __init():
    global init_properties

    init_properties = dict()
    for line in open('/etc/.portada_microservices/papi_access.properties'):
        if line.strip():
            k, v = line.strip().split('=')
            init_properties[k.strip()] = v.strip()
    public_key_base_path = init_properties["publicKeyBasePath"]
    public_key_dir_name = init_properties["publicKeydirName"]
    teams = init_properties["teams"].split(",")
    for team in teams:
        public_key_dir_path = public_key_base_path + "/" + team + "/" + public_key_dir_name
        if os.path.exists(public_key_dir_path) and os.path.isdir(public_key_dir_path):
            for publickey_file in os.listdir(public_key_dir_path):
                with open(public_key_dir_path+"/"+publickey_file, 'rb') as pem_file:
                    __add_public_key(team, load_pem_public_key(pem_file.read(), backend=default_backend()))


def reloat_team_keys(team):
    global init_properties

    # Carrega totes les claus públiques d'un equip determinat
    if init_properties is None:
        init_properties = dict(
            line.strip().split('=') for line in open('/etc/.portada_microservices/papi_access.properties'))
    public_key_base_path = init_properties["publicKeyBasePath"]
    public_key_dir_name = init_properties["publicKeydirName"]
    public_key_dir_path = public_key_base_path + "/" + team + "/" + public_key_dir_name
    if os.path.exists(public_key_dir_path) and os.path.isdir(public_key_dir_path):
        pkt[team] = []
        for publickey_file in os.listdir(public_key_dir_path):
            with open(public_key_dir_path+"/"+publickey_file, 'rb') as pem_file:
                __add_public_key(team, pem_file.read())


app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['UPLOADS_DEFAULT_DEST'] = os.path.abspath('./tmp')
images = UploadSet('images', IMAGES)
configure_uploads(app, images)
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])
init_properties = None
pkt = dict()
__init()

"""
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.cookies.get('token')
        if not token:
            return jsonify({'error': 'Authorization token is missing'}), 401
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user_id = data['user_id']
        except DecodeError:
            return jsonify({'error': 'Authorization token is invalid'}), 401
        return f(current_user_id, *args, **kwargs)
    return decorated

with open('../../config/users.json', 'r') as f:
    users = json.load(f)
@app.route('/auth', methods=['POST'])
def authenticate_user():
    if request.headers['Content-Type'] != 'application/json':
        return jsonify({'error': 'Unsupported Media Type'}), 415
    username = request.json.get('username')
    password = request.json.get('password')
    for user in users:
        if user['username'] == username and user['password'] == password:
            token = jwt.encode({'user_id': user['id']}, app.config['SECRET_KEY'],algorithm="HS256")
            response = make_response(jsonify({'message': 'Authentication successful'}))
            response.set_cookie('token', token)
            return response, 200
    return jsonify({'error': 'Invalid username or password'}), 401

@app.route("/testAuth", methods=['GET'])
def testAuth(current_user_id):
    return jsonify({'success':True, 'message':'image-tools service is working'}), 200

"""


def __verify_signature_for_team(signature_bytes, data, team):
    verified = False
    for i in range(2):
        for public_key in pkt[team]:
            if not verified:
                try:
                    public_key.verify(
                        signature_bytes,  # La signatura enviada pel client
                        data,  # Les dades que han estat signades
                        padding.PKCS1v15(),  # Tipus de padding (PKCS1v15 en aquest cas)
                        hashes.SHA256()  # Algorisme de hash (ha de coincidir amb el de la signatura)
                    )
                    verified = True
                except Exception as e:
                    verified = False
        if not verified and i==0:
            reloat_team_keys(team)

    return verified


def verify_signature(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # Obtenir la signatura de la capçalera HTTP
        if request.host.startswith("localhost") or request.host.startswith("127.0.0."):
            return f(*args, **kwargs)
        signature = request.headers.get('X-Signature')
        if signature is None:
            challenge = init_properties['papicli_access_signature_data']
            return jsonify({"error": "Missing signature", "challenge": challenge}), 401

        # Decodificar la signatura en base64
        try:
            signature_bytes = base64.b64decode(signature)
        except Exception as e:
            return jsonify({"error": "Invalid signature format"}), 400

        # Verificar la signatura amb la clau pública
        challenge = request.headers.get('X-Challenge')
        if challenge is None:
            challenge =  init_properties['papicli_access_signature_data']
        if "team" in request.values:
            team = request.values['team']
        elif "team" in request.json:
            team = request.json['team']
        else:
            return jsonify({"error": "Unknown team"}), 500
        if __verify_signature_for_team(signature_bytes,  challenge.encode('utf-8'), team):
            # Si la verificació és correcte, continuem
            return f(*args, **kwargs)
        else:
            return jsonify({"error": "forbidden resource"}), 403

    return decorated


@app.route("/test", methods=['GET', 'POST'])
def test():
    """
    Test the microservice
    :return: None
    """
    return jsonify({'success': True, 'message': 'python test service is working'}), 200


@app.route("/testUploadImage", methods=['POST'])
def testUploadImage():
    """
    Test microservice uploading images
    :return: a json with information of the file uploaded
    """
    message, extension, status = __save_uploaded_file()
    if status >= 400:
        return jsonify(message), status

    @after_this_request
    def remove_file(response):
        __remove_file(message)
        return response

    return jsonify({
        "image_id": 'uploaded',
        "filename": message
    }), 201


@app.route("/dewarpImageFile", methods=['POST', 'PUT'])
def dewarp_image_file():
    message, extension, status = __save_uploaded_file()
    if status < 400:
        filename = message
    else:
        return jsonify(message), status

    try:
        tool = DewarpTools()
        tool.image_path = filename
        tool.dewarp_image()
        tool.save_image()
    except Exception as e:
        return str(e), 500


    @after_this_request
    def remove_file(response):
        __remove_file(filename)
        return response

    return send_file(filename, mimetype='image/' + extension)


@app.route("/deskewImageFile", methods=['POST', 'PUT'])
def deskew_image_file():
    """
    Deskew the image arrived as file. The process save the file, deskew it if it's necessary and save
    the image fixed in a file and return it in the response. If some exception is raised, the response
    will content a json with the error message.
    :return: the content of the image file deskewed.
    """
    message, extension, status = __save_uploaded_file()
    if status < 400:
        filename = message
    else:
        return jsonify(message), status
    try:
        tool = DeskewTool()
        tool.image_path = filename
        tool.min_angle = 0.1
        tool.deskew_image()
        tool.save_image()
    except Exception as e:
        return str(e), 500


    @after_this_request
    def remove_file(response):
        __remove_file(filename)
        return response

    return send_file(filename, mimetype='image/' + extension)

@app.route("/testParagraphImageFile", methods=['POST', 'PUT'])
def test_paragraph_image_file():
    message, extension, status = __save_uploaded_file()
    if status < 400:
        filename = message
    else:
        return jsonify({'status': -1, 'message': message, 'error': True, 'http_status':status})

    try:
        with open("/etc/.portada_microservices/yolo_config.json") as f:
            config_json = json.load(f)

        tool = PortadaParagraphCutter(layout_model_path=config_json['column_model_path'], paragraph_model_path=config_json['para_model_path'])
        tool.image_path = filename
        tool.config = config_json
        col_boxes = tool.get_columns()
        annotated_image = PortadaParagraphCutter.draw_annotated_image_by_boxes(col_boxes, tool.image)

        file_name = Path(tool.image_path).stem
        ext = Path(tool.image_path).suffix
        if len(ext) == 0:
            ext = ".jpg"
    except Exception as e:
        return jsonify({'status': -2, 'message': f'error processing {filename}', 'error': True})

    @after_this_request
    def remove_file(response):
        __remove_file(filename)
        return response

    #    return send_file(filename, mimetype='image/' + extension)
    jpg_image = cv2.imencode(ext, annotated_image)[1]
    ret = [(dict(file_name=file_name, extension=ext, count="1" ,image=base64.b64encode(jpg_image).decode('utf-8')))]
    return jsonify({'status': 0, 'message': 'annotated image generated', 'images': ret})

def __redraw_fragment_image_file(action_type):
    message, extension, status = __save_uploaded_file()
    if status < 400:
        filename = message
    else:
        return jsonify({'status': -1, 'message': message, 'error': True, 'http_status':status})

    try:
        with open("/etc/.portada_microservices/yolo_config.json") as f:
            config_json = json.load(f)

        tool = PortadaParagraphCutter(layout_model_path=config_json['column_model_path'], paragraph_model_path=config_json['para_model_path'])
        tool.image_path = filename
        tool.config = config_json
        tool.process_image(action_type)
    except Exception as e:
        return jsonify({'status': -2, 'message': f'error processing {filename}', 'error': True})

    @after_this_request
    def remove_file(response):
        __remove_file(filename)
        return response

    #    return send_file(filename, mimetype='image/' + extension)
    ret = []
    for ib in tool.image_blocks:
        ret.append(dict(file_name=ib["file_name"], extension=ib["extension"], count=ib["count"],
                        image=base64.b64encode(ib["image"]).decode('utf-8')))
    return jsonify({'status': 0, 'message': 'image blocks generated', 'images': ret})


@app.route("/redrawParagraphImageFile", methods=['POST', 'PUT'])
def redraw_paragraph_image_file():
    resp = __redraw_fragment_image_file('P')
    return resp

@app.route("/redrawColumnImageFile", methods=['POST', 'PUT'])
def redraw_column_image_file():
    resp = __redraw_fragment_image_file('C')
    return resp

@app.route("/redrawBlockImageFile", methods=['POST', 'PUT'])
def redraw_block_image_file():
    resp = __redraw_fragment_image_file('B')
    return resp


@app.route("/pr/redrawOrderedImageFile", methods=['POST', 'PUT'])
@verify_signature
def redraw_ordered_image_file():
    message, extension, status = __save_uploaded_file()
    if status < 400:
        filename = message
    else:
        return jsonify({'status': -1, 'message': message, 'error': True, 'http_status':status})

    team = request.form.get("team")

    try:
        with open("/etc/.portada_microservices/" + team + "/arc_config.json") as f:
            config_json = json.load(f)

        tool = PortadaRedrawImageForOcr()
        tool.image_path = filename
        tool.config = config_json
        tool.process_image()
    except Exception as e:
        return jsonify({'status': -2, 'message': f'error processing {filename}', 'error': True})

    @after_this_request
    def remove_file(response):
        __remove_file(filename)
        return response

#    return send_file(filename, mimetype='image/' + extension)
    ret = []
    for ib in tool.image_blocks:
        ret.append(dict(file_name=ib["file_name"], extension=ib["extension"], count=ib["count"],
                        image=base64.b64encode(ib["image"]).decode('utf-8')))
    return jsonify({'status': 0, 'message': 'image blocks generated', 'images': ret})

@app.route("/pr/extract_with_openai", methods=['POST', 'PUT'])
@verify_signature
def extract_with_openai():
    params = request.get_json()
    team = params["team"]
    config_json = params["config_json"]
    text = params["text"]
    with open("/etc/.portada_microservices/" + team + "/project_access.properties") as f:
            properties = f.read().split("\n")
    prop_json = {}
    for property in properties:
        a_prop = property.split("=")
        if len(a_prop)==2:
            prop_json[a_prop[0].strip()] = a_prop[1].strip()
    decrypt_key = os.environ['ADATROP_TERCES']
    if "api" in config_json:
        key_path = config_json['api'].lower()+"_key_path"
    else:
        key_path = "openai_key_path"
    if key_path not in prop_json:
        return jsonify({"status":-10, "json_type": False, "content": None, "error_message": "Error API to extract doesn't exist"})
    api_key = decrypt.decrypt_file_openssl(prop_json[key_path], decrypt_key)
    extractor = AutonewsExtractorAdaptorBuilder().with_api_key(api_key).with_config_json(config_json).build()
    return jsonify(extractor.extract_data(text))

@app.route("/api/get_arrival_date_from_publication_date", methods=['POST'])
def get_arrival_date_from_publication_date(params):
    jsonp = request.get_json()
    params = jsonp["parameters_by_position"]
    return jsonify(sm_get_arrival_date_from_publication_date(params))

@app.route("/api/get_departure_date", methods=['POST'])
def get_departure_date(params):
    jsonp = request.get_json()
    params = jsonp["parameters_by_position"]
    return jsonify(sm_get_departure_date(params))

@app.route("/api/get_duration_value", methods=['POST'])
def get_duration_value(params):
    jsonp = request.get_json()
    params = jsonp["parameters_by_position"]
    return jsonify(sm_get_duration_value(params))

@app.route("/api/get_quarantine", methods=['POST'])
def get_quarantine(params):
    jsonp = request.get_json()
    params = jsonp["parameters_by_position"]
    return jsonify(sm_get_quarantine(params))

@app.route("/api/get_port_of_call_list", methods=['POST'])
def get_port_of_call_list(params):
    jsonp = request.get_json()
    params = jsonp["parameters_by_position"]
    return jsonify(sm_get_port_of_call_list(params))

@app.route("/pr/fix_ocr_from_text_and_images", methods=['POST', 'PUT'])
@verify_signature
def get_fixed_ocr_from_text_and_images():
    params = request.get_json()
    team = params["team"]
    if "config_json" in params:
        config_json = params["config_json"]
    else:
        config_json = {}
    with open("/etc/.portada_microservices/" + team + "/project_access.properties") as f:
        properties = f.read().split("\n")
    prop_json = {}
    for property in properties:
        a_prop = property.split("=")
        if len(a_prop) == 2:
            prop_json[a_prop[0].strip()] = a_prop[1].strip()
    decrypt_key = os.environ['ADATROP_TERCES']
    api_key = decrypt.decrypt_file_openssl(prop_json['qwen_key_path'], decrypt_key)
    processor = QwenOcrCorrector().set_api_key(api_key)
    if "model" in config_json:
        processor.set_model(config_json["model"])
    if "model_config" in config_json:
        processor.set_model_config(config_json['model_config'])
    sm = config_json["system_message"] if "system_message" in config_json else None
    um = config_json["user_message"] if "user_message" in config_json else None
    if sm is not None or um is not None:
        processor.set_messages_config(sm, um)
    try:
        text = processor.getFixedOcrText(params["text"], params["images"])
        ret = {"status": 0, "text": text}
    except Exception as e:
        message_error = str(e)
        ret = {"status": -1, "error_message": message_error}
    return jsonify(ret)

@app.route("/pr/get_text_from_images", methods=['POST', 'PUT'])
@verify_signature
def get_text_from_images():
    params = request.get_json()
    team = params["team"]
    if "config_json" in params:
        config_json = params["config_json"]
    else:
        config_json = {}
    with open("/etc/.portada_microservices/" + team + "/project_access.properties") as f:
        properties = f.read().split("\n")
    prop_json = {}
    for property in properties:
        a_prop = property.split("=")
        if len(a_prop) == 2:
            prop_json[a_prop[0].strip()] = a_prop[1].strip()
    decrypt_key = os.environ['ADATROP_TERCES']
    api_key = decrypt.decrypt_file_openssl(prop_json['qwen_key_path'], decrypt_key)
    processor = QwenOcrProcessor().set_api_key(api_key)
    if "model" in config_json:
        processor.set_model(config_json["model"])
    if "model_config" in config_json:
        processor.set_model_config(config_json['model_config'])
    sm = config_json["system_message"] if "system_message" in config_json else None
    um = config_json["user_message"] if "user_message" in config_json else None
    if sm is not None or um is not None:
        processor.set_messages_config(sm, um)
    try:
        text = processor.getTextFromImage(params["images"])
        ret = {"status": 0, "text": text}
    except Exception as e:
        message_error = str(e)
        ret = {"status": -1, "error_message": message_error}
    return jsonify(ret)


# @app.route('/stop', methods=['POST'])
# def stop_service():
#     """
#     Stop the microservice when it was run in a remote server using run_service() function
#     :return:
#     """
#     func = request.environ.get('werkzeug.server.shutdown')
#     if func is None:
#         raise RuntimeError('Not running with the Werkzeug Server')
#     func()
#     return jsonify({'message': 'Server shutting down...'}), 200


def get_application():
    """
    get the application object of Flask configured but not running
    :return:  the application object of Flask
    """
    return app


def run_service(port=None):
    """
    Run the service
    :return:
    """
    if port is not None:
        if type(port) is str:
            p = int(port)
        else:
            p = port
    else:
        p = 5555

    host = '0.0.0.0'  # config['DEFAULT']['host']
    app.run(debug=True, host=host, port=p)
    return app


def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def __save_uploaded_file():
    image_to_process = str(uuid.uuid4()) + "."
    #    image_to_process = 'toprocess.'
    # Check the file is an allowed type and store
    try:
        file = request.files['image']
        filename = secure_filename(file.filename)
    except Exception as e:
        return {'error': 'No image found with the \'image\' key'}, 'error', 400

    if not allowed_file(file.filename):
        return {'error': 'This file type is not allowed'}, 'error', 400

    try:
        extension = filename.rsplit('.', 1)[1].lower()
        fp = images.config.destination + '/' + image_to_process + extension
        if os.path.exists(fp):
            os.remove(fp)
        file.seek(0)
        filename = images.save(file, name=image_to_process)
    except Exception as e:
        return jsonify({'error': 'Could not store the image'}), 'error', 500

    return images.config.destination + "/" + filename, extension, 200


def __remove_file(filepath: str):
    try:
        os.remove(filepath)
    except Exception as e:
        app.logger.error(f'Error removing or closing downloaded file handle: {e}')
