from flask import Flask
from flask_cors import CORS
from config import Config
from api.routes import api_bp
import os

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # COMPREHENSIVE CORS Configuration
    CORS(app, 
         resources={r"/api/*": {
             "origins": [
                 "http://localhost:3000",
                 "http://localhost:3001",
                 "https://museum-collection-explorer.vercel.app",
                 "https://museum-collection-explorer-*.vercel.app"
             ],
             "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
             "allow_headers": ["Content-Type", "Authorization", "Accept"],
             "supports_credentials": True,
             "max_age": 3600
         }})
    
    # Register blueprints
    app.register_blueprint(api_bp, url_prefix='/api')

    app.config["PROPAGATE_EXCEPTIONS"] = True
    app.config["DEBUG"] = False
    
    return app

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)