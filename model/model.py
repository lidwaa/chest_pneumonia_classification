import tensorflow as tf
from keras import layers, models
from data_preprocessing import preprocess_data  # Ton fichier adapté au dataset Chest X-ray
import os
import cv2
import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics import classification_report, confusion_matrix
import seaborn as sns
from sklearn.model_selection import train_test_split

import tensorflow as tf

# Sélectionner le GPU
physical_devices = tf.config.list_physical_devices('GPU')
if physical_devices:
    tf.config.set_visible_devices(physical_devices[0], 'GPU')  # Utiliser le premier GPU
    print("GPU utilisé :", physical_devices[0].name)
else:
    print("Aucun GPU détecté.")


# Chargement des données
data_dir = "data"  # Doit contenir les sous-dossiers "NORMAL" et "PNEUMONIA"
X, y = preprocess_data(data_dir)

# Split en training et test
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Création du modèle
def create_advanced_model():
    model = models.Sequential([
        layers.Conv2D(32, (3, 3), activation='relu', input_shape=(128, 128, 1)),
        layers.BatchNormalization(),
        layers.MaxPooling2D((2, 2)),
        layers.Dropout(0.25),

        layers.Conv2D(64, (3, 3), activation='relu'),
        layers.BatchNormalization(),
        layers.MaxPooling2D((2, 2)),
        layers.Dropout(0.25),

        layers.Conv2D(128, (3, 3), activation='relu'),
        layers.BatchNormalization(),
        layers.MaxPooling2D((2, 2)),
        layers.Dropout(0.3),

        layers.Conv2D(256, (3, 3), activation='relu'),
        layers.BatchNormalization(),
        layers.MaxPooling2D((2, 2)),
        layers.Dropout(0.4),

        layers.Flatten(),
        layers.Dense(256, activation='relu'),
        layers.BatchNormalization(),
        layers.Dropout(0.5),
        layers.Dense(128, activation='relu'),
        layers.BatchNormalization(),
        layers.Dropout(0.5),

        layers.Dense(1, activation='sigmoid')  # 1 sortie pour binaire
    ])
    return model

model = create_advanced_model()
model.summary()

model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
              loss='binary_crossentropy',
              metrics=['accuracy'])

# Entraînement
history = model.fit(X_train, y_train, epochs=20, batch_size=64, validation_data=(X_test, y_test))

# Évaluation
test_loss, test_acc = model.evaluate(X_test, y_test, verbose=2)
print(f"\nTest accuracy: {test_acc}")

# Prédictions
predictions = (model.predict(X_test) > 0.5).astype("int32").flatten()

# Rapport de classification
print("\nClassification Report:")
print(classification_report(y_test, predictions, target_names=["NORMAL", "PNEUMONIA"]))

# Matrice de confusion
conf_matrix = confusion_matrix(y_test, predictions)
sns.heatmap(conf_matrix, annot=True, fmt='d', cmap='Blues', xticklabels=["NORMAL", "PNEUMONIA"], yticklabels=["NORMAL", "PNEUMONIA"])
plt.title("Matrice de confusion")
plt.xlabel("Prédictions")
plt.ylabel("Vérités")
plt.show()

# Courbes d'apprentissage
def plot_learning_curves(history):
    plt.figure(figsize=(12, 5))

    # Perte
    plt.subplot(1, 2, 1)
    plt.plot(history.history['loss'], label='Perte - Entraînement')
    plt.plot(history.history['val_loss'], label='Perte - Validation')
    plt.title("Évolution de la perte")
    plt.xlabel("Époque")
    plt.ylabel("Perte")
    plt.legend()

    # Précision
    plt.subplot(1, 2, 2)
    plt.plot(history.history['accuracy'], label='Précision - Entraînement')
    plt.plot(history.history['val_accuracy'], label='Précision - Validation')
    plt.title("Évolution de la précision")
    plt.xlabel("Époque")
    plt.ylabel("Précision")
    plt.legend()

    plt.show()

plot_learning_curves(history)

# Sauvegarde du modèle
model.save("static/chest_xray_model.keras")

# Prédiction d'une image
def predict_image(image_path):
    image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    image_resized = cv2.resize(image, (128, 128))
    image_input = np.array(image_resized).reshape(1, 128, 128, 1) / 255.0
    prediction = model.predict(image_input)
    predicted_class = "PNEUMONIA" if prediction[0][0] > 0.5 else "NORMAL"
    print(f"Classe prédite : {predicted_class}")

# Exemple
# predict_image("path/to/image.jpeg")
