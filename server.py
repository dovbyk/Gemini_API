from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
from char_segment import process_uploaded_image


app = Flask(__name__)
CORS(app, supports_credentials=True, resources={r"/*": {"origins": "https://deepscript.vercel.app"}})

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



@app.route('/get-image', methods=['GET'])
def get_image():
    image_path = request.args.get('path')
    if not image_path or not os.path.exists(image_path):
        return jsonify({'error': 'Image not found'}), 404

    return send_file(image_path, mimetype='image/png')

if __name__ == '__main__':
    app.run(debug=True, port=5000)
