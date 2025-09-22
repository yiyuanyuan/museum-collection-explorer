import torch
import timm
from PIL import Image
import io
import base64
from typing import Dict, List, Optional
import requests
import json

class AnimalIdentifierService:
    def __init__(self, model_choice: str = "efficientnet_b7"):
        """
        Initialize with a specific model choice
        
        Args:
            model_choice: Key from AVAILABLE_MODELS dict (e.g., "efficientnet_b7", "vit_inat2021", etc.)
        """
        # Dictionary of available models with their properties
        self.AVAILABLE_MODELS = {
            # Current model (ImageNet)
            "efficientnet_b7": {
                "name": "tf_efficientnet_b7",
                "pretrained": True,
                "description": "EfficientNet-B7 trained on ImageNet (1000 classes)",
                "labels_url": "https://raw.githubusercontent.com/anishathalye/imagenet-simple-labels/master/imagenet-simple-labels.json"
            },
            
            # iNaturalist 2021 models (10,000 species)
            "vit_inat2021": {
                "name": "vit_base_patch16_224.inat2021",
                "pretrained": True,
                "description": "Vision Transformer trained on iNaturalist 2021 (10,000 species)",
                "labels_url": None  # Would need iNat 2021 labels
            },
            
            # Models you can try (check availability with timm.list_models())
            "convnext_inat": {
                "name": "convnext_base.fb_in22k_ft_in1k",
                "pretrained": True,
                "description": "ConvNeXT trained on ImageNet-22K then fine-tuned",
                "labels_url": "https://raw.githubusercontent.com/anishathalye/imagenet-simple-labels/master/imagenet-simple-labels.json"
            },
            
            "resnet50": {
                "name": "resnet50",
                "pretrained": True,
                "description": "ResNet-50 trained on ImageNet (baseline model)",
                "labels_url": "https://raw.githubusercontent.com/anishathalye/imagenet-simple-labels/master/imagenet-simple-labels.json"
            },
            
            # Add more models as needed
            "mobilenet": {
                "name": "mobilenetv3_large_100",
                "pretrained": True,
                "description": "MobileNet V3 - lightweight model for faster inference",
                "labels_url": "https://raw.githubusercontent.com/anishathalye/imagenet-simple-labels/master/imagenet-simple-labels.json"
            }
        }
        
        # Set the chosen model
        self.model_choice = model_choice
        if model_choice not in self.AVAILABLE_MODELS:
            print(f"Model '{model_choice}' not found. Available models: {list(self.AVAILABLE_MODELS.keys())}")
            print(f"Defaulting to 'efficientnet_b7'")
            self.model_choice = "efficientnet_b7"
        
        self.model_config = self.AVAILABLE_MODELS[self.model_choice]
        self.model = None
        self.transform = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model_loaded = False
        self.labels = None
        
        print(f"Initialized with model: {self.model_config['description']}")
        
    def list_available_models(self) -> Dict:
        """Return information about all available models"""
        return self.AVAILABLE_MODELS
    
    def switch_model(self, model_choice: str):
        """
        Switch to a different model
        
        Args:
            model_choice: Key from AVAILABLE_MODELS dict
        """
        if model_choice not in self.AVAILABLE_MODELS:
            raise ValueError(f"Model '{model_choice}' not available. Choose from: {list(self.AVAILABLE_MODELS.keys())}")
        
        # Clear current model
        if self.model_loaded:
            del self.model
            self.model = None
            self.model_loaded = False
            torch.cuda.empty_cache()  # Clear GPU memory if using CUDA
        
        # Set new model
        self.model_choice = model_choice
        self.model_config = self.AVAILABLE_MODELS[model_choice]
        print(f"Switched to model: {self.model_config['description']}")
        
    def load_model(self):
        """Load the selected model"""
        if not self.model_loaded:
            try:
                model_name = self.model_config["name"]
                print(f"Loading model: {model_name}...")
                
                # Check if model is available
                available_models = timm.list_models()
                if model_name not in available_models:
                    # Try to find similar models
                    similar = [m for m in available_models if 'inat' in m.lower()]
                    print(f"Warning: {model_name} not found in timm.")
                    if similar:
                        print(f"Found similar iNaturalist models: {similar[:5]}")
                        # Use the first similar model
                        if similar:
                            model_name = similar[0]
                            print(f"Using {model_name} instead")
                    else:
                        # Fallback to basic efficientnet
                        model_name = "tf_efficientnet_b7"
                        print(f"Falling back to {model_name}")
                
                # Load the model
                self.model = timm.create_model(model_name, pretrained=True)
                self.model = self.model.to(self.device)
                self.model.eval()
                
                # Get the preprocessing transform
                data_config = timm.data.resolve_model_data_config(self.model)
                self.transform = timm.data.create_transform(**data_config, is_training=False)
                
                # Load labels if URL is provided
                self.labels = self._get_model_labels()
                
                self.model_loaded = True
                print(f"Model loaded successfully! Using: {model_name}")
                print(f"Can identify {self.model_config['num_classes']} classes")
                
            except Exception as e:
                print(f"Error loading model: {str(e)}")
                raise Exception(f"Could not load model: {str(e)}")
    
    def _get_model_labels(self):
        """Get the labels for the current model"""
        try:
            labels_url = self.model_config.get("labels_url")
            if not labels_url:
                print(f"No labels URL for {self.model_choice}, will use class indices")
                return None
                
            response = requests.get(labels_url)
            if response.status_code == 200:
                return response.json()
            else:
                return None
        except Exception as e:
            print(f"Could not load labels: {e}")
            return None
    
    def identify_animal(self, image_data: str) -> Dict:
        """
        Identify an animal from base64 encoded image data
        
        Args:
            image_data: Base64 encoded image string
            
        Returns:
            Dictionary with identification results and confidence scores
        """
        try:
            # Ensure model is loaded
            self.load_model()
            
            # Decode and preprocess image
            image = self._decode_image(image_data)
            
            # Transform image for model input
            input_tensor = self.transform(image).unsqueeze(0).to(self.device)
            
            # Get predictions from model
            with torch.no_grad():
                outputs = self.model(input_tensor)
                probabilities = torch.nn.functional.softmax(outputs, dim=1)
                
            # Get top 5 predictions
            top5_prob, top5_class = torch.topk(probabilities, 5)
            
            # Prepare results
            predictions = []
            for i in range(5):
                class_idx = top5_class[0][i].item()
                confidence = top5_prob[0][i].item() * 100
                
                # Get species name if labels are available
                if self.labels:
                    if isinstance(self.labels, dict) and class_idx in self.labels:
                        species_name = self.labels[class_idx]
                    elif isinstance(self.labels, list) and class_idx < len(self.labels):
                        species_name = self.labels[class_idx]
                    else:
                        species_name = f"Unknown Species (Class {class_idx})"
                else:
                    species_name = f"Species/Class {class_idx}"
                
                predictions.append({
                    "name": species_name,
                    "confidence": round(confidence, 2),
                    "rank": i + 1,
                    "class_id": class_idx
                })
            
            # Determine confidence level and response
            highest_confidence = predictions[0]["confidence"]
            
            if highest_confidence >= 85:
                confidence_level = "high"
                message = f"I'm quite confident this is a **{predictions[0]['name']}** (confidence: {predictions[0]['confidence']}%)"
                suggestions = [predictions[0]]
            elif highest_confidence >= 60:
                confidence_level = "medium"
                top_3 = predictions[:3]
                message = (f"I'm moderately confident (highest: {highest_confidence}%) this could be one of these species:\n"
                          f"1. **{top_3[0]['name']}** ({top_3[0]['confidence']}%)\n"
                          f"2. **{top_3[1]['name']}** ({top_3[1]['confidence']}%)\n"
                          f"3. **{top_3[2]['name']}** ({top_3[2]['confidence']}%)\n\n"
                          f"The varying confidence is due to similar visual features among these species.")
                suggestions = top_3
            else:
                confidence_level = "low"
                message = (f"I'm not very confident about the exact species (highest confidence: {highest_confidence}%). "
                          f"The top possibility is **{predictions[0]['name']}**.")
                suggestions = predictions[:3]
            
            # Add model info to response
            message += f"\n\n*Using model: {self.model_config['description']}*"
            
            return {
                "success": True,
                "confidence_level": confidence_level,
                "message": message,
                "predictions": predictions,
                "suggestions": suggestions,
                "highest_confidence": highest_confidence,
                "model_type": self.model_config['description'],
                "model_used": self.model_choice
            }
            
        except Exception as e:
            print(f"Error in animal identification: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": "I'm having trouble analyzing this image. Please make sure it's a clear photo of an animal and try again."
            }
    
    def _decode_image(self, image_data: str) -> Image.Image:
        """Decode base64 image to PIL Image"""
        # Remove data URL prefix if present
        if ',' in image_data:
            image_data = image_data.split(',')[1]
        
        # Decode base64
        image_bytes = base64.b64decode(image_data)
        image = Image.open(io.BytesIO(image_bytes))
        
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        return image


# Usage example:
if __name__ == "__main__":
    # Initialize with a specific model
    identifier = AnimalIdentifierService(model_choice="vit_inat2021")
    
    # List available models
    print("Available models:")
    for key, config in identifier.list_available_models().items():
        print(f"  {key}: {config['description']}")
    
    # Switch to a different model if needed
    # identifier.switch_model("efficientnet_b7")