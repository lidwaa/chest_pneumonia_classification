import os
import cv2
import numpy as np

IMG_SIZE = 128
classes = ["NORMAL", "PNEUMONIA"]

def load_data(data_dir, classes):
    data = []
    total_images = 0
    for label, class_name in enumerate(classes):
        class_dir = os.path.join(data_dir, class_name)
        for img_name in os.listdir(class_dir):
            img_path = os.path.join(class_dir, img_name)
            try:
                img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
                if img is not None:
                    img_resized = cv2.resize(img, (IMG_SIZE, IMG_SIZE))
                    data.append([img_resized, label])
                    total_images += 1
                else:
                    print(f"Image non lue (NoneType) : {img_path}")
            except Exception as e:
                print(f"Erreur lors du chargement de l'image : {img_path}, {e}")
    
    print(f"Nombre total d'images chargées : {total_images}")
    return data

def preprocess_data(data_dir):
    data = load_data(data_dir, classes)

    X, y = zip(*data)
    X = np.array(X).reshape(-1, IMG_SIZE, IMG_SIZE, 1) / 255.0
    y = np.array(y)

    return X, y
