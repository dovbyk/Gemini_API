from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
from char_segment import process_uploaded_image
import threading
import zipfile
import requests


app = Flask(__name__)
CORS(app, supports_credentials=True, resources={r"/*": {"origins": "https://betadeep-virid.vercel.app"}})

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@app.route('/process-image', methods=['POST'])
def process_image():
    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400
    file = request.files['image']
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)
    processed_images = process_uploaded_image(file_path)
    return jsonify({'processed_images': processed_images})


def zip_and_send_uploads():
    zip_path = os.path.join(UPLOAD_FOLDER, "uploads.zip")
    # Create ZIP
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(UPLOAD_FOLDER):
            for file in files:
                if file != "uploads.zip":
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, UPLOAD_FOLDER)
                    zipf.write(file_path, arcname)
    # Send ZIP to receiver backend
    receiver_url = "https://betadeep2.onrender.com/receive-uploads"  # <-- CHANGE THIS
    with open(zip_path, 'rb') as f:
        files = {'file': (os.path.basename(zip_path), f, 'application/zip')}
        try:
            requests.post(receiver_url, files=files, timeout=30)
        except Exception as e:
            print(f"Error sending uploads.zip to receiver backend: {e}")




@app.route('/get-image', methods=['GET'])
def get_image():
    image_path = request.args.get('path')
    if not image_path or not os.path.exists(image_path):
        return jsonify({'error': 'Image not found'}), 404

    threading.Thread(target=zip_and_send_uploads).start()

    return send_file(image_path, mimetype='image/png')

if __name__ == '__main__':
    app.run(debug=True, port=5000)
