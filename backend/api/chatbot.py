"""
Enhanced chatbot service with OpenAI tools API for ALA Biocache integration
Compatible with gpt-5-mini model
"""
import base64
from typing import Dict, List, Optional, Any
import json
from openai import OpenAI
from config import Config
from api.biocache import BiocacheService


class ChatbotService:
    def __init__(self):
        """Initialize the chatbot with OpenAI client and tool definitions"""
        self.client = OpenAI(api_key=Config.OPENAI_API_KEY)
        self.biocache_service = BiocacheService()
        
        # Model configuration
        self.model = "gpt-5-mini"
        
        # Conversation history storage
        self.conversations = {}
        self.max_history_length = 20
        
        # System prompt for the assistant with function calling context
        self.system_prompt = """You are an AI assistant for the Australian Museum Collection Explorer. 
        You help users learn about museum specimens from the OZCAM dataset and can identify animals from photos.
        
        You have access to the Australian Museum's OZCAM specimen dataset through the Atlas of Living Australia (ALA) Biocache API.
        When users ask questions about specimens, species occurrences, or collection data, you can search the actual dataset.
        
        Important guidelines:
        - Use the search_specimens function when users ask about specific species, locations, time periods, or collection information
        - All specimen data you provide MUST come from actual ALA queries - never make up specimen information
        - Be clear when no data is found for a query
        - You can combine multiple searches to answer complex questions
        - Provide interesting facts and educational context alongside the data
        
        Be friendly, informative, and educational. Answer in a maximum of 3 sentences unless providing detailed specimen data."""
        
        # Define the tools schema for OpenAI (new format)
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "search_specimens",
                    "description": "Search the OZCAM specimen dataset from the Australian Museum via ALA Biocache API",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "scientific_name": {
                                "type": "string",
                                "description": "Scientific name to search for (genus, species, family, order, etc.)"
                            },
                            "common_name": {
                                "type": "string", 
                                "description": "Common/vernacular name of the organism"
                            },
                            "state_province": {
                                "type": "string",
                                "description": "Australian state or territory (e.g., 'New South Wales', 'Queensland')"
                            },
                            "year": {
                                "type": "integer",
                                "description": "Year of collection/observation"
                            },
                            "year_range": {
                                "type": "object",
                                "properties": {
                                    "start_year": {"type": "integer"},
                                    "end_year": {"type": "integer"}
                                },
                                "description": "Range of years for temporal queries"
                            },
                            "bounds": {
                                "type": "object",
                                "properties": {
                                    "north": {"type": "number"},
                                    "south": {"type": "number"},
                                    "east": {"type": "number"},
                                    "west": {"type": "number"}
                                },
                                "description": "Geographic bounding box for spatial queries"
                            },
                            "collection_name": {
                                "type": "string",
                                "description": "Name of the museum collection"
                            },
                            "basis_of_record": {
                                "type": "string",
                                "enum": ["PRESERVED_SPECIMEN", "HUMAN_OBSERVATION", "LIVING_SPECIMEN", "MACHINE_OBSERVATION"],
                                "description": "Type of specimen record"
                            },
                            "has_image": {
                                "type": "boolean",
                                "description": "Filter for specimens with images"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results to return (default 10, max 100)"
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_specimen_statistics",
                    "description": "Get statistical summary of specimens matching the search criteria",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "scientific_name": {
                                "type": "string",
                                "description": "Scientific name to get statistics for"
                            },
                            "state_province": {
                                "type": "string",
                                "description": "State to get statistics for"  
                            },
                            "facets": {
                                "type": "array",
                                "items": {
                                    "type": "string",
                                    "enum": ["year", "state_province", "collection_name", "family", "order", "class"]
                                },
                                "description": "Fields to get faceted counts for"
                            }
                        }
                    }
                }
            }
        ]

    def get_or_create_session(self, session_id: str) -> List[Dict]:
        """Get existing session or create new one"""
        if session_id not in self.conversations:
            self.conversations[session_id] = [
                {"role": "system", "content": self.system_prompt}
            ]
        return self.conversations[session_id]

    def execute_function(self, function_name: str, arguments: Dict) -> Dict:
        """Execute the requested function and return results"""
        try:
            if function_name == "search_specimens":
                return self._search_specimens(**arguments)
            elif function_name == "get_specimen_statistics":
                return self._get_specimen_statistics(**arguments)
            else:
                return {"error": f"Unknown function: {function_name}"}
        except Exception as e:
            return {"error": str(e)}

    def _search_specimens(self, **kwargs) -> Dict:
        """Execute specimen search using Biocache service"""
        try:
            # Build filters from function arguments
            filters = {}
            
            # Handle scientific name - this could be at any taxonomic level
            if kwargs.get('scientific_name'):
                filters['scientific_name'] = kwargs['scientific_name']
            
            # Handle common name
            if kwargs.get('common_name'):
                filters['common_name'] = kwargs['common_name']
            
            # Handle other filters
            if kwargs.get('state_province'):
                filters['state_province'] = kwargs['state_province']
            if kwargs.get('year'):
                filters['year'] = kwargs['year']
            if kwargs.get('collection_name'):
                filters['collection_name'] = kwargs['collection_name']
            if kwargs.get('has_image'):
                filters['has_image'] = kwargs['has_image']
            
            # Handle year range
            if kwargs.get('year_range'):
                year_range = kwargs['year_range']
                if year_range.get('start_year') and year_range.get('end_year'):
                    filters['year_range'] = f"[{year_range['start_year']} TO {year_range['end_year']}]"
            
            # Determine page size
            limit = kwargs.get('limit', 10)
            if limit is not None:
                limit = min(limit, 100)
            else:
                limit = 10
            
            # Call biocache service
            results = self.biocache_service.search_occurrences(
                filters=filters if filters else None,
                page=0,
                page_size=limit,
                bounds=kwargs.get('bounds')
            )
            
            # Format results for GPT
            formatted_results = {
                "total_records": results.get('totalRecords', 0),
                "returned_records": len(results.get('occurrences', [])),
                "specimens": []
            }
            
            # Add specimen details
            for occ in results.get('occurrences', [])[:limit]:
                specimen = {
                    "scientific_name": occ.get('scientificName'),
                    "common_name": occ.get('commonName'),
                    "catalog_number": occ.get('catalogNumber'),
                    "collection_name": occ.get('collectionName'),
                    "location": {
                        "state": occ.get('stateProvince'),
                        "locality": occ.get('locality'),
                        "coordinates": {
                            "latitude": occ.get('latitude'),
                            "longitude": occ.get('longitude')
                        }
                    },
                    "date": occ.get('eventDate'),
                    "year": occ.get('year'),
                    "institution": occ.get('institutionName'),
                    "basis_of_record": occ.get('basisOfRecord'),
                    "taxonomic_info": {
                        "family": occ.get('family'),
                        "order": occ.get('order'),
                        "class": occ.get('class')
                    },
                    "has_image": bool(occ.get('imageUrl')),
                    "image_url": occ.get('thumbnailUrl')
                }
                formatted_results["specimens"].append(specimen)
            
            # Add facets if available
            if results.get('facets'):
                formatted_results['facets'] = results['facets']
            
            return formatted_results
            
        except Exception as e:
            return {
                "error": f"Error searching specimens: {str(e)}",
                "total_records": 0,
                "specimens": []
            }

    def _get_specimen_statistics(self, **kwargs) -> Dict:
        """Get statistical summary of specimens"""
        try:
            filters = {}
            if kwargs.get('scientific_name'):
                filters['scientific_name'] = kwargs['scientific_name']
            if kwargs.get('state_province'):
                filters['state_province'] = kwargs['state_province']
            
            # Get data with facets
            results = self.biocache_service.search_occurrences(
                filters=filters if filters else None,
                page=0,
                page_size=0  # We only want facets, not actual records
            )
            
            statistics = {
                "total_records": results.get('totalRecords', 0),
                "faceted_counts": results.get('facets', {})
            }
            
            return statistics
            
        except Exception as e:
            return {
                "error": f"Error getting statistics: {str(e)}",
                "total_records": 0,
                "faceted_counts": {}
            }

    def process_message(
        self, 
        message: str, 
        session_id: str = "default",
        image_data: Optional[str] = None
    ) -> Dict:
        """
        Process a chat message with optional image and function calling
        
        Args:
            message: Text message from user
            session_id: Session identifier for conversation history
            image_data: Base64 encoded image data (optional)
            
        Returns:
            Response dictionary with assistant's reply
        """
        try:
            # Get conversation history for this session
            conversation = self.get_or_create_session(session_id)
            
            # Prepare the user message
            user_message = {"role": "user", "content": []}
            
            # Add text content if provided
            if message:
                user_message["content"].append({
                    "type": "text",
                    "text": message
                })
            
            # Add image content if provided
            if image_data:
                # Clean base64 data if it has data URL prefix
                if image_data.startswith('data:image'):
                    image_data = image_data.split(',')[1]
                
                user_message["content"].append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{image_data}",
                        "detail": "high"
                    }
                })
                
                # If no text message provided with image, add default
                if not message:
                    user_message["content"].insert(0, {
                        "type": "text",
                        "text": "Please analyse this image and tell me what you see. If it's an animal, please try to identify it."
                    })
            
            # Add user message to conversation history
            conversation.append(user_message)
            
            # Trim conversation history if too long
            if len(conversation) > self.max_history_length:
                conversation = [conversation[0]] + conversation[-(self.max_history_length-1):]
                self.conversations[session_id] = conversation
            
            # Make API call to OpenAI with tools
            response = self.client.chat.completions.create(
                model=self.model,
                messages=conversation,
                tools=self.tools,
                tool_choice="auto"  # Let the model decide when to call functions
            )
            
            # Get the initial response
            message_response = response.choices[0].message
            
            # Check if the model wants to call a tool
            if message_response.tool_calls:
                # Process all tool calls
                tool_results = []
                
                for tool_call in message_response.tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    
                    print(f"Executing function: {function_name} with args: {function_args}")
                    
                    # Execute the function
                    function_result = self.execute_function(function_name, function_args)
                    
                    tool_results.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": json.dumps(function_result)
                    })
                
                # Add assistant's message with tool calls to conversation
                conversation.append({
                    "role": "assistant",
                    "content": message_response.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        } for tc in message_response.tool_calls
                    ]
                })
                
                # Add tool results to conversation
                for tool_result in tool_results:
                    conversation.append(tool_result)
                
                # Get final response from the model with tool results
                final_response = self.client.chat.completions.create(
                    model=self.model,
                    messages=conversation
                )
                
                assistant_message = final_response.choices[0].message.content
                response_type = "data_response" if not image_data else "image_and_data_response"
                
            else:
                # No tool call, use regular response
                assistant_message = message_response.content
                response_type = "image_analysis" if image_data else "text_response"
            
            # Add assistant's final response to conversation history
            conversation.append({
                "role": "assistant",
                "content": assistant_message
            })
            
            # Prepare response
            return {
                "success": True,
                "response": assistant_message,
                "session_id": session_id,
                "type": response_type,
                "suggestions": self.get_contextual_suggestions(image_data is not None)
            }
            
        except Exception as e:
            print(f"Error processing message: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "response": f"I apologize, but I encountered an error: {str(e)}. Please try again.",
                "error": str(e),
                "suggestions": self.get_default_suggestions()
            }

    def get_contextual_suggestions(self, had_image: bool) -> List[str]:
        """Get suggestions based on conversation context"""
        if had_image:
            return [
                "Search for this species in our collection",
                "Where has this species been found in Australia?",
                "Show me similar specimens with images"
            ]
        else:
            return [
                "Search for kangaroo specimens",
                "What species were collected in 2020?",
                "Show me specimens from Queensland with images"
            ]

    def get_default_suggestions(self) -> List[str]:
        """Get default suggestions"""
        return [
            "What species were collected in 2020?",
            "What are the most-collected fish species in NSW?",
            "Give me a link to the image of the oldest bird specimen in the collection."
        ]

    def clear_session(self, session_id: str = "default") -> Dict:
        """Clear conversation history for a session"""
        if session_id in self.conversations:
            del self.conversations[session_id]
        return {
            "success": True,
            "message": "Conversation history cleared",
            "session_id": session_id
        }

    def get_session_history(self, session_id: str = "default") -> Dict:
        """Get conversation history for a session"""
        conversation = self.get_or_create_session(session_id)
        # Filter out function-related messages for display
        display_history = []
        for msg in conversation[1:]:  # Skip system message
            if msg.get("role") in ["user", "assistant"] and msg.get("content"):
                display_history.append(msg)
        
        return {
            "success": True,
            "history": display_history,
            "session_id": session_id,
            "message_count": len(display_history)
        }