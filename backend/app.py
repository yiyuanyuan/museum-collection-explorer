from flask import Flask
from flask_cors import CORS
from config import Config
from api.routes import api_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Configure CORS - allow all origins for development
    CORS(app, origins=["http://localhost:3000", "http://localhost:3001"], supports_credentials=True)
    
    # Register blueprints
    app.register_blueprint(api_bp, url_prefix='/api')

    app.config["PROPAGATE_EXCEPTIONS"] = True
    app.config["DEBUG"] = True

    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000)