from flask import Flask, request, make_response, jsonify
from flask_cors import CORS
from config import Config
from api.routes import api_bp
import os

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Configure CORS with explicit POST support
    CORS(app, 
         resources={r"/api/*": {
             "origins": "*",
             "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
             "allow_headers": ["Content-Type", "Authorization", "Accept", "Origin", "X-Requested-With"],
             "expose_headers": ["Content-Range", "X-Content-Range"],
             "supports_credentials": False,
             "max_age": 3600
         }})
    
    # Handle preflight requests
    @app.before_request
    def handle_preflight():
        if request.method == "OPTIONS":
            response = make_response()
            response.headers.add("Access-Control-Allow-Origin", "*")
            response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization,Accept,Origin,X-Requested-With")
            response.headers.add("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS")
            response.headers.add("Access-Control-Max-Age", "3600")
            return response
    
    # Ensure CORS headers on all responses
    @app.after_request
    def after_request(response):
        if request.method == "OPTIONS":
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization,Accept,Origin,X-Requested-With"
        else:
            response.headers["Access-Control-Allow-Origin"] = "*"
        return response
    
    # Register blueprints
    app.register_blueprint(api_bp, url_prefix='/api')

    app.config["PROPAGATE_EXCEPTIONS"] = True
    app.config["DEBUG"] = False
    
    return app

# Create app instance at module level for Gunicorn
app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)