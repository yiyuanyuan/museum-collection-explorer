from flask import Flask
from flask_cors import CORS
from config import Config
from api.routes import api_bp
import os

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # TEMPORARY: Allow ALL origins to test
    CORS(app)  # This allows ALL origins - we'll restrict it later
    
    # Register blueprints
    app.register_blueprint(api_bp, url_prefix='/api')

    app.config["PROPAGATE_EXCEPTIONS"] = True
    app.config["DEBUG"] = False
    
    return app

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)