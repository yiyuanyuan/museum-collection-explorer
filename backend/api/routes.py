from flask import Blueprint, request, jsonify, session
from api.biocache import BiocacheService
from api.chatbot import ChatbotService
import uuid

# Blueprint setup
api_bp = Blueprint("api", __name__)
biocache_service = BiocacheService()
chatbot_service = ChatbotService()

# Your existing biocache routes remain unchanged
@api_bp.route("/occurrences", methods=["GET"])
def get_occurrences():
    """Get occurrences with optional filters and viewport bounds"""
    try:
        page = int(request.args.get("page", 0))
        page_size = int(request.args.get("pageSize", 500))

        # Viewport bounds
        bounds = None
        if all(key in request.args for key in ["north", "south", "east", "west"]):
            bounds = {
                "north": float(request.args.get("north")),
                "south": float(request.args.get("south")),
                "east": float(request.args.get("east")),
                "west": float(request.args.get("west")),
            }

        # Filters
        filters = {}
        if request.args.get("collectionName"):
            filters["collection_name"] = request.args.get("collectionName")
        if request.args.get("stateProvince"):
            filters["state_province"] = request.args.get("stateProvince")
        if request.args.get("year"):
            filters["year"] = request.args.get("year")

        # Image filter option - DEBUG LOGGING
        show_only_with_images_str = request.args.get("showOnlyWithImages", "true")
        show_only_with_images = show_only_with_images_str.lower() in ['true', '1', 'yes']
        
        print(f"[ROUTES DEBUG] showOnlyWithImages parameter received: '{show_only_with_images_str}'")
        print(f"[ROUTES DEBUG] Converted to boolean: {show_only_with_images}")

        # Spatial parameters
        lat = request.args.get("lat", type=float)
        lon = request.args.get("lon", type=float)
        radius = request.args.get("radius", type=float)

        results = biocache_service.search_occurrences(
            filters=filters,
            page=page,
            page_size=page_size,
            bounds=bounds,
            lat=lat,
            lon=lon,
            radius=radius,
            show_only_with_images=show_only_with_images,
        )
        return jsonify(results), 200

    except Exception as e:
        print(f"Error in /occurrences route: {e}")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/statistics", methods=["GET"])
def get_statistics():
    """Return dataset statistics"""
    try:
        stats = biocache_service.get_statistics()
        return jsonify(stats), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============ SIMPLIFIED CHATBOT ROUTES ============

@api_bp.route("/chat", methods=["POST"])
def chat():
    """
    Handle chat messages with optional image upload
    Supports both JSON and multipart/form-data
    """
    try:
        # Get or create session ID
        if 'session_id' not in session:
            session['session_id'] = str(uuid.uuid4())
        session_id = session['session_id']
        
        # Handle JSON request
        if request.is_json:
            data = request.json
            message = data.get("message", "")
            image_data = data.get("image")
            custom_session_id = data.get("session_id", session_id)
        
        # Handle multipart/form-data request
        else:
            message = request.form.get("message", "")
            image_data = None
            custom_session_id = request.form.get("session_id", session_id)
            
            if "image" in request.files:
                file = request.files["image"]
                import base64
                image_data = base64.b64encode(file.read()).decode("utf-8")
        
        # Validate input
        if not message and not image_data:
            return jsonify({
                "success": False,
                "error": "Either a message or an image is required"
            }), 400
        
        # Process the message
        response = chatbot_service.process_message(
            message=message,
            session_id=custom_session_id,
            image_data=image_data
        )
        
        return jsonify(response), 200
        
    except Exception as e:
        print(f"Chat error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e),
            "response": "I apologize, but I encountered an error. Please try again."
        }), 500


@api_bp.route("/chat/suggestions", methods=["GET"])
def get_suggestions():
    """Get chat suggestions"""
    try:
        suggestions = chatbot_service.get_default_suggestions()
        return jsonify({
            "success": True,
            "suggestions": suggestions
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@api_bp.route("/chat/clear", methods=["POST"])
def clear_chat():
    """Clear chat history for current session"""
    try:
        session_id = session.get('session_id', 'default')
        if request.is_json and request.json.get('session_id'):
            session_id = request.json.get('session_id')
        
        result = chatbot_service.clear_session(session_id)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@api_bp.route("/chat/history", methods=["GET"])
def get_chat_history():
    """Get chat history for current session"""
    try:
        session_id = request.args.get('session_id', session.get('session_id', 'default'))
        result = chatbot_service.get_session_history(session_id)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@api_bp.route("/health", methods=["GET"])
def health_check():
    """Simple health check"""
    return jsonify({"status": "healthy", "service": "museum-explorer-api"}), 200