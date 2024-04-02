from flask import Flask, jsonify, request, send_file
from flask_reuploads import UploadSet, IMAGES, configure_uploads
from py_portada_image.deskew_tools import DeskewTool
from py_portada_image.dewarp_tools import DewarpTools
from werkzeug.utils import secure_filename
import os


app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['UPLOADS_DEFAULT_DEST'] = os.path.abspath('./tmp')
images = UploadSet('images', IMAGES)
configure_uploads(app, images)
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])

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


@app.route("/test", methods=['GET', 'POST'])
def test():
    """
    Test the microservice
    :return: None
    """
    return jsonify({'success': True, 'message': 'image-tools service is working'}), 200


@app.route("/testUploadImage", methods=['POST'])
def testUploadImage():
    """
    Test microservice uploading images
    :return: a json with information of the file uploaded
    """
    message, extension, status = __save_uploaded_file()
    if status >= 400:
        return message, status

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
        return message, status

    tool = DewarpTools ()
    tool.image_path = filename
    tool.dewarp_image()
    tool.save_image()
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
        return message, status

    tool = DeskewTool()
    tool.image_path = filename
    tool.min_angle = 0.1
    tool.deskew_image()
    tool.save_image()
    return send_file(filename, mimetype='image/' + extension)


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
            p =port
    else:
        p = 5555

    host = '0.0.0.0'  # config['DEFAULT']['host']
    app.run(debug=True, host=host, port=p)
    return app


def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def __save_uploaded_file():
    image_to_process = 'toprocess.'
    # Check the file is an allowed type and store
    try:
        file = request.files['image']
        filename = secure_filename(file.filename)
    except:
        return jsonify({'error': 'No image found with the \'image\' key'}), 'error', 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'This file type is not allowed'}), 'error', 400

    try:
        extension = filename.rsplit('.', 1)[1].lower()
        fp = images.config.destination + '/' + image_to_process + extension
        if os.path.exists(fp):
            os.remove(fp)
        file.seek(0)
        filename = images.save(file, name=image_to_process)
    except:
        return jsonify({'error': 'Could not store the image'}), 'error', 500

    return images.config.destination + "/" + filename, extension, 200
