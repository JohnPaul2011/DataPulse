from flask import Flask, jsonify, request, send_file, render_template_string
import time, os
from gevent import pywsgi
import io, random,uuid
from zipfile import ZipFile

app = Flask(__name__)
storage = {}

def unique_id():
    return uuid.uuid4().hex

@app.route('/')
def index():
    return "Status --> OK " + str(random.randint(1000,9999))

@app.route('/u/<user>/<room_id>/clear')
def clear_room(user, room_id):
    storage[room_id] = {}
    return jsonify({"status":"cleared","room":room_id})

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
    return jsonify({"status":"posted","id":uid})

@app.route('/u/<user>/<room_id>/get')
def get_data(user, room_id):
    room = storage.get(room_id, {})
    out = {}
    for k, v in room.items():
        d = v.copy()
        d.pop("content",None)
        out[k] = d
    return jsonify(out)

@app.route('/u/<user>/<room_id>/upload/', methods=['GET','POST'])
def upload_file(user, room_id):
    if request.method == 'GET':
        return render_template_string('''
        <form id="uploadForm" method="post" enctype="multipart/form-data">
            <input type="file" name="file" multiple />
            <input type="submit" value="Upload" />
        </form>
        <div id="progress"></div>

        <script>
        const form = document.getElementById('uploadForm');
        const progressDiv = document.getElementById('progress');

        form.addEventListener('submit', e => {
            e.preventDefault();
            const files = form.querySelector('input[type=file]').files;
            progressDiv.innerHTML='';

            for(let i=0;i<files.length;i++){
                const file = files[i];
                const formData = new FormData();
                formData.append('file', file);

                let id='p_'+i;
                let bar=document.createElement("div");
                bar.id=id;
                bar.innerHTML=file.name+": 0%";
                progressDiv.appendChild(bar);

                const xhr=new XMLHttpRequest();
                xhr.open('POST', window.location.href, true);

                xhr.upload.onprogress=function(e){
                    if(e.lengthComputable){
                        const percent=Math.round((e.loaded/e.total)*100);
                        document.getElementById(id).innerHTML=file.name+": "+percent+"%";
                    }
                };

                xhr.onload=function(){
                    document.getElementById(id).innerHTML=file.name+": ✔";
                };

                xhr.send(formData);
            }
        });
        </script>
        ''')

    if 'file' not in request.files:
        return jsonify({"error":"no file"}),400

    files = request.files.getlist('file')
    if not files:
        return jsonify({"error":"empty"}),400

    if room_id not in storage:
        storage[room_id] = {}

    uploaded = []
    for file in files:
        if file.filename == '':
            continue

        uid = unique_id()[:8]
        storage[room_id][uid] = {
            "user": user,
            "filename": file.filename,
            "content": file.read(),
            "time": time.strftime('%Y-%m-%d %H:%M:%S')
        }
        uploaded.append({"id":uid,"filename":file.filename})

    if not uploaded:
        return jsonify({"error":"no upload"}),400

    return jsonify({"status":"ok","files":uploaded})

@app.route('/u/<user>/<room_id>/download/<uid>')
def download_file(user, room_id, uid):
    entry = storage.get(room_id, {}).get(uid)
    if not entry:
        return jsonify({"error":"not found"}),404

    return send_file(
        io.BytesIO(entry['content']),
        as_attachment=True,
        download_name=entry.get('filename','file'),
        mimetype='application/octet-stream'
    )



@app.route('/u/<user>/<room_id>/download_all')
def download_all(user, room_id):
    room = storage.get(room_id, {})
    if not room:
        return jsonify({"error":"empty"}),404

    buffer = io.BytesIO()
    with ZipFile(buffer, 'w') as z:
        for uid, entry in room.items():
            if "content" in entry:
                name = entry.get("filename", uid)
                z.writestr(name, entry["content"])

    buffer.seek(0)
    return send_file(buffer,
        as_attachment=True,
        download_name=f"{room_id}.zip",
        mimetype="application/zip")
        
if __name__ == '__main__':
    port=int(os.environ.get('PORT',10000))
    server=pywsgi.WSGIServer(('0.0.0.0',port),app)
    server.serve_forever()
