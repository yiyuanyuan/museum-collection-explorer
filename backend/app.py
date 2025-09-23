from flask import Flask, request, make_response
from flask_cors import CORS
from config import Config
from api.routes import api_bp
import os

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # TEMPORARY: Allow ALL origins to fix CORS issues
    # Once working, we'll restrict this to specific domains
    CORS(app, 
         resources={r"/*": {"origins": "*"}},
         allow_headers=["Content-Type", "Authorization", "Accept"],
         methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
         supports_credentials=False)  # Set to False when using "*"
    
    # Handle preflight OPTIONS requests
    @app.before_request
    def handle_preflight():
        if request.method == "OPTIONS":
            response = make_response()
            response.headers.add("Access-Control-Allow-Origin", "*")
            response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization,Accept")
            response.headers.add("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS")
            return response
    
    # Add CORS headers to every response
    @app.after_request
    def after_request(response):
        origin = request.headers.get('Origin')
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization,Accept'
        response.headers['Access-Control-Allow-Methods'] = 'GET,POST,PUT,DELETE,OPTIONS'
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