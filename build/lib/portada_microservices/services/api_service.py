import threading
from werkzeug.serving import make_server
from flask import Flask, jsonify, request, send_file
from flask_reuploads import UploadSet, IMAGES, configure_uploads
from py_portada_image.deskew_tools import DeskewTool
from werkzeug.utils import secure_filename
import os
import configparser


def configure_app():
    configp = configparser.ConfigParser()
    configp.read(os.path.abspath(os.path.curdir + '/config/service.cfg'))
    return configp


config = configure_app()
port = int(os.environ.get('PORT', config['DEFAULT']['port']))
host = config['DEFAULT']['host']
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
    # Check the file is an allowed type and store
    try:
        file = request.files['image']
        filename = secure_filename(file.filename)
    except:
        return jsonify({'error': 'No image found with the \'image\' key'}), 400

    if not allowed_file(filename):
        return jsonify({'error': 'This file type is not allowed'}), 400

    try:
        extension = filename.rsplit('.', 1)[1].lower()
        fp = images.config.destination + '/uploaded.' + extension
        if os.path.exists(fp):
            os.remove(fp)
        filename = images.save(file, name='uploaded.')
    except:
        return jsonify({'error': 'Could not store the image'}), 500

    return jsonify({
        "image_id": 'uploaded',
        "filename": filename
    }), 201


@app.route("/deskewImageFile", methods=['POST', 'PUT'])
def deskewImageFile():
    """
    Deskew the image arrived as file. The process save the file, deskew it if it's necessary and save
    the image fixed in a file and return it in the response. If some exception is raised, the response
    will content a json with the error message.
    :return: the content of the image file deskewed.
    """
    image_to_process = 'toprocess.'
    # Check the file is an allowed type and store
    try:
        file = request.files['image']
        filename = secure_filename(file.filename)
    except:
        return jsonify({'error': 'No image found with the \'image\' key'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'This file type is not allowed'}), 400

    try:
        extension = filename.rsplit('.', 1)[1].lower()
        fp = images.config.destination + '/' + image_to_process + extension
        if os.path.exists(fp):
            os.remove(fp)
        file.seek(0)
        filename = images.save(file, name=image_to_process)
    except:
        return jsonify({'error': 'Could not store the image'}), 500

    deskew_tool = DeskewTool()
    deskew_tool.image_path = images.config.destination + "/" + filename
    deskew_tool.minAngle = 0.5
    deskew_tool.deskewImage()
    deskew_tool.saveImage()
    return send_file(images.config.destination + "/" + filename, mimetype='image/' + extension)


@app.route('/stop', methods=['GET', 'POST'])
def stop_service():
    """
    Stop the microservice when it was run in a remote server using run_service() function
    :return:
    """
    global vis_service_running
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()
    vis_service_running = False
    return jsonify({'message': 'Server shutting down...'}), 200


def run_service():
    """
    Run the service
    :return:
    """
    global vis_service_running
    if not vis_service_running:
        app.run(debug=True, host=host, port=port)
    return app


def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def shutdown_server():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()


global vis_service_running
vis_service_running = False


class ServerThread(threading.Thread):
    def __init__(self, fapp, host, port):
        threading.Thread.__init__(self)
        self.server = make_server(host, port, fapp)
        self.ctx = fapp.app_context()
        self.ctx.push()

    def run(self):
        global vis_service_running
        vis_service_running = True
        self.server.serve_forever()

    def shutdown(self):
        global vis_service_running
        vis_service_running = False
        self.server.shutdown()


def run_local_service():
    global service
    global vis_service_running
    if not vis_service_running:
        vis_service_running = True
        # app.run(debug=True, host="0.0.0.0", port=port)
        service = ServerThread(app, "localhost", port)
        service.start()
    return service


def stop_local_service():
    global vis_service_running
    global service
    if vis_service_running:
        service.shutdown()


def is_local_service_running():
    global vis_service_running
    return vis_service_running


global service

if __name__ == "__main__":
    run_service()
