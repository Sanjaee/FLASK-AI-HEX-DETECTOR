from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image
import io
import numpy as np
from sklearn.cluster import KMeans
import cloudinary.uploader
import threading
import time
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

cloudinary.config(
    cloud_name=os.getenv('CLOUD_NAME'),
    api_key=os.getenv('API_KEY'),
    api_secret=os.getenv('API_SECRET')
)

MAX_CONTENT_LENGTH = 3 * 1024 * 1024
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

def get_dominant_color(image_bytes, num_colors=1):
    image = Image.open(io.BytesIO(image_bytes))
    image = image.convert('RGB')
    image_array = np.array(image)
    reshaped_image = image_array.reshape(-1, 3)
    
    kmeans = KMeans(n_clusters=num_colors, random_state=42)
    kmeans.fit(reshaped_image)
    
    dominant_colors = kmeans.cluster_centers_
    hex_colors = ['#{:02x}{:02x}{:02x}'.format(int(color[0]), int(color[1]), int(color[2])) for color in dominant_colors]
    
    return hex_colors[0] if hex_colors else None

def delete_cloudinary_image(public_id):
    time.sleep(60)  # Tunggu 1 menit
    try:
        cloudinary.uploader.destroy(public_id)
        print(f"Gambar {public_id} berhasil dihapus")
    except Exception as e:
        print(f"Gagal menghapus gambar {public_id}: {e}")

@app.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if len(file.read()) > MAX_CONTENT_LENGTH:
        return jsonify({"error": "File is too large, maximum size is 3MB"}), 400
    
    file.seek(0)

    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'bmp'}
    file_ext = file.filename.lower().split('.')[-1]
    if file_ext not in allowed_extensions:
        return jsonify({"error": "File type not allowed"}), 400

    try:
        file_bytes = file.read()
        
        upload_result = cloudinary.uploader.upload(
            file_bytes, 
            folder="temp_uploads",
            resource_type="image"
        )
        
        hex_color = get_dominant_color(file_bytes)
        
        threading.Thread(
            target=delete_cloudinary_image,
            args=(upload_result['public_id'],)
        ).start()
        
        return jsonify({
            "hex_color": hex_color,
            "filename": file.filename,
            "cloudinary_url": upload_result['secure_url']
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)