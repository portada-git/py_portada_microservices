import os

from flask import Flask, jsonify, request, send_file
from flask_reuploads import UploadSet, IMAGES, configure_uploads
from py_portada_image.deskew_tools import DeskewTool
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
port = int(os.environ.get('PORT', 5555))
app.config['UPLOADS_DEFAULT_DEST'] = '../../data/service_host'
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
    return jsonify({'success': True, 'message': 'image-tools service is working'}), 200


@app.route("/testUploadImage", methods=['POST'])
def testUploadImage():
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


@app.route("/deskewImageFile", methods=['POST'])
def deskewImageFile():
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
        fp = images.config.destination+'/'+image_to_process + extension
        if os.path.exists(fp):
            os.remove(fp)
        filename = images.save(file, name=image_to_process)
    except:
        return jsonify({'error': 'Could not store the image'}), 500

    deskew_tool = DeskewTool()
    deskew_tool.image_path = images.config.destination + "/" + filename
    deskew_tool.minAngle = 0.5
    deskew_tool.deskewImage()
    deskew_tool.saveImage()
    return send_file(deskew_tool.image_path, mimetype='image/' + extension)


def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=port)
