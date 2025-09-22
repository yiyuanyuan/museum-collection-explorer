"""
Test script to demonstrate the chatbot's function calling capabilities
Run this script to test various queries against the ALA Biocache API
"""

from api.chatbot import ChatbotService
import json

def test_chatbot_queries():
    """Test various types of queries that should trigger function calling"""
    
    # Initialize the chatbot
    chatbot = ChatbotService()
    session_id = "test_session"
    
    # Test queries that should trigger function calling
    test_queries = [
        # Species-specific queries
        "Show me all kangaroo specimens in the collection",
        "What platypus specimens do you have from New South Wales?",
        "Find specimens of Acacia collected in 2020",
        
        # Location-based queries
        "What specimens were collected in Queensland?",
        "Show me birds from Sydney",
        
        # Temporal queries
        "What was collected in 2019?",
        "Show me the oldest specimens in the collection",
        "What specimens were collected between 2015 and 2020?",
        
        # Collection queries
        "How many specimen records are in the OZCAM dataset?",
        "What families are most represented in the collection?",
        
        # Complex queries
        "Show me all butterfly specimens from Queensland with images",
        "What mammals were collected in New South Wales in the last 5 years?",
        
        # Statistical queries
        "Give me statistics on spider specimens by state",
        "What's the temporal distribution of bird specimens?",
        
        # Queries that should NOT trigger function calling
        "What is a kangaroo?",
        "Tell me about Australian wildlife",
        "How do I identify a spider?"
    ]
    
    print("=" * 80)
    print("TESTING CHATBOT FUNCTION CALLING CAPABILITIES")
    print("=" * 80)
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{i}. USER QUERY: {query}")
        print("-" * 40)
        
        try:
            # Process the message
            response = chatbot.process_message(
                message=query,
                session_id=session_id
            )
            
            if response['success']:
                print(f"Response Type: {response['type']}")
                print(f"Assistant Response:\n{response['response'][:500]}...")
                if len(response['response']) > 500:
                    print("... [truncated]")
            else:
                print(f"Error: {response['error']}")
                
        except Exception as e:
            print(f"Exception occurred: {str(e)}")
        
        print("-" * 40)
        
        # Clear session after each query for testing
        if i % 5 == 0:
            chatbot.clear_session(session_id)
            print("Session cleared for fresh context")

def test_direct_function_execution():
    """Test direct function execution to verify the functions work"""
    
    chatbot = ChatbotService()
    
    print("\n" + "=" * 80)
    print("TESTING DIRECT FUNCTION EXECUTION")
    print("=" * 80)
    
    # Test 1: Search for kangaroos
    print("\n1. Testing search_specimens for kangaroos:")
    result = chatbot.execute_function("search_specimens", {
        "scientific_name": "Macropus",
        "limit": 5
    })
    print(f"Found {result.get('total_records', 0)} records")
    if result.get('specimens'):
        print(f"First specimen: {json.dumps(result['specimens'][0], indent=2)}")
    
    # Test 2: Search by location
    print("\n2. Testing search by state:")
    result = chatbot.execute_function("search_specimens", {
        "state_province": "New South Wales",
        "limit": 3
    })
    print(f"Found {result.get('total_records', 0)} records from NSW")
    
    # Test 3: Search with temporal filter
    print("\n3. Testing search by year:")
    result = chatbot.execute_function("search_specimens", {
        "year": 2020,
        "limit": 3
    })
    print(f"Found {result.get('total_records', 0)} records from 2020")
    
    # Test 4: Get statistics
    print("\n4. Testing get_specimen_statistics:")
    result = chatbot.execute_function("get_specimen_statistics", {
        "scientific_name": "Aves",
        "facets": ["state_province", "year"]
    })
    print(f"Total bird records: {result.get('total_records', 0)}")
    if result.get('faceted_counts'):
        print("Faceted counts available:", list(result['faceted_counts'].keys()))

def test_integration():
    """Test the full integration with sample conversation"""
    
    chatbot = ChatbotService()
    session_id = "integration_test"
    
    print("\n" + "=" * 80)
    print("TESTING FULL CONVERSATION FLOW")
    print("=" * 80)
    
    conversation = [
        "Hi! What can you tell me about the museum's collection?",
        "Show me some interesting kangaroo specimens",
        "Which states have the most kangaroo specimens?",
        "What about spiders? Do you have many spider specimens from Queensland?",
        "Show me the oldest specimens in the collection"
    ]
    
    for message in conversation:
        print(f"\nUSER: {message}")
        response = chatbot.process_message(message, session_id)
        print(f"ASSISTANT: {response['response'][:300]}...")
        print(f"Suggestions: {response['suggestions']}")
        print("-" * 40)

if __name__ == "__main__":
    # Run all tests
    print("Starting Chatbot Function Calling Tests")
    print("========================================")
    
    # Test direct function execution first
    test_direct_function_execution()
    
    # Test various query types
    test_chatbot_queries()
    
    # Test full conversation flow
    test_integration()
    
    print("\n" + "=" * 80)
    print("TESTS COMPLETED")
    print("=" * 80)