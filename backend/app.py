from flask import Flask
from flask_cors import CORS
from config import Config
from api.routes import api_bp
import os

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Configure CORS - allow all origins for development
    CORS(app, origins=[
        "http://localhost:3000", 
        "https://museum-collection-explorer.vercel.app", 
        "https://museum-collection-explorer-*.vercel.app"
    ], supports_credentials=True,
    allow_headers=["Content-Type", "Authorization"],
    methods=["GET", "POST", "OPTIONS"])
    
    # Register blueprints
    app.register_blueprint(api_bp, url_prefix='/api')

    app.config["PROPAGATE_EXCEPTIONS"] = True
    app.config["DEBUG"] = False  # Changed from True to False
    
    return app

# MOVED THIS LINE OUTSIDE THE IF BLOCK
app = create_app()

if __name__ == '__main__':
    # REMOVED app = create_app() from here
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)