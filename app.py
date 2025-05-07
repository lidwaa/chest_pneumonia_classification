from flask import Flask, render_template, request, redirect, url_for
import os
import numpy as np
import cv2
from keras.models import load_model
from tensorflow.keras.preprocessing.image import img_to_array


app = Flask(__name__)

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Chargement du modèle binaire
model = load_model("static/chest_xray_model.keras")

IMG_SIZE = 128
classes = ["NORMAL", "PNEUMONIA"]

def prepare_image(image_file):
    img = cv2.imread(image_file, cv2.IMREAD_GRAYSCALE)
    img_resized = cv2.resize(img, (IMG_SIZE, IMG_SIZE))  
    img_resized = img_to_array(img_resized)
    img_resized = np.expand_dims(img_resized, axis=0)
    img_resized = img_resized / 255.0
    return img_resized

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_image():
    if 'file' not in request.files:
        return redirect(request.url)
    
    file = request.files['file']
    if file.filename == '':
        return redirect(request.url)

    image_path = os.path.join(app.config['UPLOAD_FOLDER'], 'uploaded_image.jpg')
    file.save(image_path)

    img = prepare_image(image_path)
    prediction = model.predict(img)[0][0]

    predicted_class = classes[1] if prediction > 0.5 else classes[0]
    
    return render_template('index.html', prediction=predicted_class, image_path=image_path)

if __name__ == '__main__':
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    
    app.run(debug=True)
