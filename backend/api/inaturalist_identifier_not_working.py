import requests
import base64
import io
from PIL import Image
from typing import Dict, List, Optional
import json

class INaturalistIdentifierService:
    def __init__(self):
        """Initialize the iNaturalist API service for animal identification"""
        # Try different endpoints - Seek API is more reliable for public use
        self.seek_api_url = "https://api.inaturalist.org/v1/computervision/score_image"
        self.taxa_url = "https://api.inaturalist.org/v1/taxa"
        
    def identify_animal(self, image_data: str) -> Dict:
        """
        Identify an animal using iNaturalist's Computer Vision API
        
        Args:
            image_data: Base64 encoded image string
            
        Returns:
            Dictionary with identification results and confidence scores
        """
        try:
            # Decode and prepare image
            image_file = self._prepare_image_for_api(image_data)
            
            # Try the public endpoint with proper parameters
            print("Calling iNaturalist Computer Vision API...")
            
            # Add parameters that might be required
            params = {
                'observed_on_string': '',  # No specific date
                'lat': '',  # No specific location
                'lng': '',
                'radius': ''
            }
            
            response = requests.post(
                self.seek_api_url,
                files={'image': ('image.jpg', image_file, 'image/jpeg')},
                data=params,
                timeout=30
            )
            
            print(f"API Response Status: {response.status_code}")
            
            if response.status_code == 401:
                # If unauthorized, provide fallback message
                return {
                    "success": False,
                    "message": "The iNaturalist API requires authentication. Let's try Microsoft's API instead (Option 3), or you can use the pre-trained model (Option 1).",
                    "error": "Authentication required"
                }
            
            if response.status_code != 200:
                print(f"API Response: {response.text}")
                raise Exception(f"API returned status code {response.status_code}")
            
            data = response.json()
            
            # Process results
            if 'results' not in data or len(data['results']) == 0:
                return {
                    "success": False,
                    "message": "Could not identify the animal in this image. Please try a clearer photo."
                }
            
            # Parse predictions from iNaturalist
            predictions = []
            for idx, result in enumerate(data['results'][:5]):  # Top 5 results
                taxon = result.get('taxon', {})
                
                # Get names
                common_name = taxon.get('preferred_common_name', taxon.get('name', 'Unknown'))
                scientific_name = taxon.get('name', 'Unknown')
                
                # Handle combined_score vs score
                if 'combined_score' in result:
                    score = result['combined_score'] * 100
                elif 'vision_score' in result:
                    score = result['vision_score'] * 100  
                elif 'score' in result:
                    score = result['score'] * 100
                else:
                    score = 0
                
                # Get taxonomic rank (species, genus, family, etc.)
                rank = taxon.get('rank', 'unknown')
                
                # Get additional info
                wikipedia_url = taxon.get('wikipedia_url', '')
                default_photo = taxon.get('default_photo', {})
                photo_url = default_photo.get('square_url', '') if default_photo else ''
                
                predictions.append({
                    "name": f"{common_name} ({scientific_name})",
                    "common_name": common_name,
                    "scientific_name": scientific_name,
                    "confidence": round(score, 2),
                    "rank": idx + 1,
                    "taxonomic_rank": rank,
                    "taxon_id": taxon.get('id'),
                    "wikipedia_url": wikipedia_url,
                    "photo_url": photo_url,
                    "observations_count": taxon.get('observations_count', 0)
                })
            
            # Determine confidence level and create response
            highest_confidence = predictions[0]["confidence"] if predictions else 0
            
            if highest_confidence >= 85:
                confidence_level = "high"
                species = predictions[0]
                message = (f"I'm quite confident this is a **{species['common_name']}** "
                          f"(*{species['scientific_name']}*) with {species['confidence']}% confidence.")
                
                # Add observation count for context
                if species['observations_count'] > 0:
                    message += f"\n\nThis species has been observed {species['observations_count']:,} times on iNaturalist."
                
                suggestions = [predictions[0]]
                
            elif highest_confidence >= 60:
                confidence_level = "medium"
                top_3 = predictions[:3]
                message = f"I'm moderately confident (highest: {highest_confidence}%) this could be one of these species:\n\n"
                
                for i, species in enumerate(top_3, 1):
                    message += (f"{i}. **{species['common_name']}** "
                               f"(*{species['scientific_name']}*) - {species['confidence']}%\n")
                
                message += "\nThe varying confidence is due to similar visual features among these species."
                suggestions = top_3
                
            else:
                confidence_level = "low"
                # Check if we at least got a higher taxonomic level
                if predictions and predictions[0]['taxonomic_rank'] != 'species':
                    rank = predictions[0]['taxonomic_rank']
                    name = predictions[0]['common_name']
                    message = (f"I can identify this to the {rank} level as likely **{name}** "
                              f"({predictions[0]['confidence']}% confidence), but I'm not confident "
                              f"about the exact species. Try uploading a clearer or closer photo.")
                else:
                    message = (f"I'm not very confident about the exact species "
                              f"(highest confidence: {highest_confidence}%). "
                              f"The top possibility is **{predictions[0]['common_name']}**, "
                              f"but please consider uploading a clearer image.")
                suggestions = predictions[:3]
            
            return {
                "success": True,
                "confidence_level": confidence_level,
                "message": message,
                "predictions": predictions,
                "suggestions": suggestions,
                "highest_confidence": highest_confidence,
                "model_type": "iNaturalist Computer Vision API",
                "total_results": len(data.get('results', []))
            }
            
        except requests.exceptions.RequestException as e:
            print(f"Network error calling iNaturalist API: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": "Unable to connect to iNaturalist. Please check your internet connection and try again."
            }
        except Exception as e:
            print(f"Error in animal identification: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": "I'm having trouble analyzing this image. The iNaturalist API might be temporarily unavailable. Please try again later or use the pre-trained model option."
            }
    
    def _prepare_image_for_api(self, image_data: str) -> io.BytesIO:
        """Prepare image for API upload"""
        # Remove data URL prefix if present
        if ',' in image_data:
            image_data = image_data.split(',')[1]
        
        # Decode base64
        image_bytes = base64.b64decode(image_data)
        image = Image.open(io.BytesIO(image_bytes))
        
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Resize if too large (iNaturalist recommends max 2048px)
        max_size = 2048
        if max(image.size) > max_size:
            image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        
        # Save to bytes buffer
        buffer = io.BytesIO()
        image.save(buffer, format='JPEG', quality=95)
        buffer.seek(0)
        
        return buffer
    
    def get_species_info(self, taxon_id: int) -> Optional[Dict]:
        """
        Get detailed information about a species from iNaturalist
        
        Args:
            taxon_id: The iNaturalist taxon ID
            
        Returns:
            Dictionary with species information or None
        """
        try:
            response = requests.get(f"{self.taxa_url}/{taxon_id}")
            if response.status_code == 200:
                data = response.json()
                return data.get('results', [{}])[0] if data.get('results') else None
            return None
        except:
            return None