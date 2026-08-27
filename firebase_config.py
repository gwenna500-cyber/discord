import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import os

def get_db():
    # Check if Firebase is already initialized
    if not firebase_admin._apps:
        # Requires a firebase_key.json file in the same directory
        key_path = os.path.join(os.path.dirname(__file__), 'firebase_key.json')
        if not os.path.exists(key_path):
            raise FileNotFoundError(f"Firebase key file not found at {key_path}. Please download it from Firebase Console.")
        
        cred = credentials.Certificate(key_path)
        firebase_admin.initialize_app(cred)
    
    return firestore.client()
