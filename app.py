from flask import Flask, jsonify, request, send_file, render_template_string
import time, os
from gevent import pywsgi
import io, random 

app = Flask(__name__)

storage = {}

def unique_id():
    return hex(time.time_ns())[2:]

@app.route('/')
def index():
    return "Status --> OK " + str(random.randint(1000,9999))

@app.route('/u/<user>/<room_id>/post/<data>')
def post_data(user, room_id, data):
    if user not in storage:
        storage[user] = {}

    if room_id not in storage[user]:
        storage[user][room_id] = {}

    uid = unique_id()[:8]
    storage[user][room_id][uid] = {
        "data": data,
        "time": time.strftime('%Y-%m-%d %H:%M:%S')
    }

    return jsonify({"status": "saved", "user": user, "room": room_id, "id": uid})
 
@app.route('/u/<user>/<room_id>/get')
def get_data(user, room_id):
    room_data = storage.get(user, {}).get(room_id, {})
    filtered = {}
    for uid, entry in room_data.items():
        info = {
            "time": entry.get("time"),
            "user" : user
        }
        if "filename" in entry:
            info["filename"] = entry["filename"]
        if "data" in entry:
            info["data"] = entry["data"]
        filtered[uid] = info
    return jsonify(filtered)
    
    
# Upload file - form-enabled for select prompt in browsers
@app.route('/u/<user>/<room_id>/upload', methods=['GET', 'POST'])
def upload_file(user, room_id):
    if request.method == 'GET':
        # Simple HTML form to trigger file select prompt in browser
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

    # Save file in storage with the original filename and content
    content = file.read()
    if user not in storage:
        storage[user] = {}
    if room_id not in storage[user]:
        storage[user][room_id] = {}

    uid = unique_id()[:8]
    storage[user][room_id][uid] = {
        "filename": file.filename,
        "content": content,
        "time": time.strftime('%Y-%m-%d %H:%M:%S')
    }
    return jsonify({"status": "file uploaded and saved", "user": user, "room": room_id, "id": uid})

# Download a specific file by UID
@app.route('/u/<user>/<room_id>/download/<uid>')
def download_file(user, room_id, uid):
    chat_data = storage.get(user, {}).get(room_id, {})
    file_entry = chat_data.get(uid)
    if not file_entry:
        return jsonify({"error": "File not found"}), 404

    return send_file(
        io.BytesIO(file_entry['content']),
        as_attachment=True,
        download_name=file_entry.get('filename', 'file'),
        mimetype='application/octet-stream'
    )
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    server = pywsgi.WSGIServer(('0.0.0.0', port), app)
    server.serve_forever()
