from flask import Flask, jsonify, request, send_file, render_template_string
import time, os
from gevent import pywsgi
import io, random

app = Flask(__name__)

storage = {}   # room → messages

def unique_id():
    return hex(time.time_ns())[2:]

@app.route('/')
def index():
    return "Status --> OK " + str(random.randint(1000,9999))

# Post message to a room
@app.route('/u/<user>/<room_id>/post/<data>')
def post_data(user, room_id, data):
    if room_id not in storage:
        storage[room_id] = {}

    uid = unique_id()[:8]
    storage[room_id][uid] = {
        "user": user,
        "data": data,
        "time": time.strftime('%Y-%m-%d %H:%M:%S')
    }
    return jsonify({"user":user,"status": "posted", "room": room_id, "id": uid})

# Get messages in a room
@app.route('/u/<user>/<room_id>/get')
def get_data(user,room_id):
    room_data = storage.get(room_id, {})
    return jsonify(room_data)

# Upload file to a room
@app.route('/u/<user>/<room_id>/upload/', methods=['GET', 'POST'])
def upload_file(room_id, user):
    if request.method == 'GET':
        return render_template_string('''
        <form method="post" enctype="multipart/form-data">
          <input type="file" name="file" />
          <input type="submit" value="Upload" />
        </form>
        ''')

    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if room_id not in storage:
        storage[room_id] = {}

    uid = unique_id()[:8]
    storage[room_id][uid] = {
        "user": user,
        "filename": file.filename,
        "content": file.read(),
        "time": time.strftime('%Y-%m-%d %H:%M:%S')
    }
    return jsonify({"status": "file uploaded", "room": room_id, "id": uid})

# Download file
@app.route('/u/<room_id>/download/<uid>')
def download_file(room_id, uid):
    room = storage.get(room_id, {})
    entry = room.get(uid)
    if not entry:
        return jsonify({"error": "File not found"}), 404

    return send_file(
        io.BytesIO(entry['content']),
        as_attachment=True,
        download_name=entry.get('filename', 'file'),
        mimetype='application/octet-stream'
    )

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    server = pywsgi.WSGIServer(('0.0.0.0', port), app)
    server.serve_forever()
