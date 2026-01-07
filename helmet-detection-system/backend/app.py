from flask import Flask
from flask_cors import CORS
import os

def create_app():
    app = Flask(__name__)
    CORS(app)
    
    # Ensure static directories exist
    os.makedirs(os.path.join(app.root_path, 'static', 'crops'), exist_ok=True)
    os.makedirs(os.path.join(app.root_path, 'logs'), exist_ok=True)

    from routes import api
    app.register_blueprint(api)

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
