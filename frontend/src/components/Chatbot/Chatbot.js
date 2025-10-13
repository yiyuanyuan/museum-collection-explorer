import React, { useState, useEffect, useRef } from 'react';
import './Chatbot.css';
import { sendChatMessage, getChatSuggestions } from '../../services/api';

function Chatbot() {
  const [messages, setMessages] = useState([
    {
      type: 'assistant',
      text: 'Welcome to the Australian Museum Collection Explorer! I can help you learn about specimens in our collection and identify animals from photos. Try uploading an image or asking me a question!'
    }
  ]);
  const [inputMessage, setInputMessage] = useState('');
  const [suggestions, setSuggestions] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedImage, setSelectedImage] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [showCamera, setShowCamera] = useState(false);
  const [sessionId] = useState(() => {
    // Generate a unique session ID for this chat session
    return 'session_' + Math.random().toString(36).substr(2, 9);
  });

  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);

  useEffect(() => {
    loadSuggestions();
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Cleanup camera stream on unmount
  useEffect(() => {
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
      }
    };
  }, []);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const loadSuggestions = async () => {
    try {
      const data = await getChatSuggestions();
      // Always limit to 3 suggestions
      const limitedSuggestions = (data.suggestions || [
        "Upload an animal photo to identify",
        "Tell me about Australian wildlife",
        "What museum specimens do you have?"
      ]).slice(0, 3);
      setSuggestions(limitedSuggestions);
    } catch (error) {
      console.error('Error loading suggestions:', error);
      // Default 3 suggestions
      setSuggestions([
        "Upload an animal photo to identify",
        "Tell me about Australian wildlife",
        "What museum specimens do you have?"
      ]);
    }
  };

  const handleImageSelect = (event) => {
    const file = event.target.files[0];
    if (file) {
      // Validate file size (max 10MB)
      if (file.size > 10 * 1024 * 1024) {
        alert('Please select an image smaller than 10MB');
        return;
      }

      const reader = new FileReader();
      reader.onloadend = () => {
        setSelectedImage(reader.result);
        setImagePreview(reader.result);
      };
      reader.readAsDataURL(file);
    }
  };

  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        video: { facingMode: 'environment' } // Use back camera on mobile
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
      setShowCamera(true);
    } catch (error) {
      console.error('Error accessing camera:', error);
      alert('Unable to access camera. Please make sure you have granted camera permissions.');
    }
  };

  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
    setShowCamera(false);
  };

  const capturePhoto = () => {
    if (videoRef.current && canvasRef.current) {
      const video = videoRef.current;
      const canvas = canvasRef.current;
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      const context = canvas.getContext('2d');
      context.drawImage(video, 0, 0);
      
      // Get image data from canvas
      const imageData = canvas.toDataURL('image/jpeg');
      setSelectedImage(imageData);
      setImagePreview(imageData);
      
      // Stop camera after capturing
      stopCamera();
    }
  };

  const handleSendMessage = async (message = inputMessage) => {
    if (!message.trim() && !selectedImage) return;

    // Create user message
    const userMessage = {
      type: 'user',
      text: message || (selectedImage ? 'Please analyse this image' : ''),
      image: imagePreview
    };
    
    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    
    // Clear image immediately after adding to messages
    const imageToSend = selectedImage;
    clearImage();
    
    setIsLoading(true);

    try {
      // Send message to backend
      const response = await sendChatMessage(
        message, 
        { session_id: sessionId }, 
        imageToSend
      );

      // Handle response
      if (response.success) {
        const assistantMessage = {
          type: 'assistant',
          text: response.response
        };
        setMessages(prev => [...prev, assistantMessage]);

        // Update suggestions if provided - limit to 3
        if (response.suggestions) {
          setSuggestions(response.suggestions.slice(0, 3));
        }
      } else {
        throw new Error(response.error || 'Unknown error');
      }
    } catch (error) {
      console.error('Error sending message:', error);
      const errorMessage = {
        type: 'assistant',
        text: "I apologize, but I encountered an error. Please try again."
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const clearImage = () => {
    setSelectedImage(null);
    setImagePreview(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleSuggestionClick = (suggestion) => {
    if (suggestion.toLowerCase().includes("upload")) {
      fileInputRef.current?.click();
    } else {
      handleSendMessage(suggestion);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const formatMessageText = (text) => {
    // Handle bold text
    text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    // Handle line breaks
    text = text.replace(/\n/g, '<br>');
    return text;
  };

  const clearConversation = async () => {
    if (window.confirm('Are you sure you want to clear the conversation?')) {
      setMessages([{
        type: 'assistant',
        text: 'Conversation cleared. How can I help you today?'
      }]);
      // You could also call an API to clear server-side history here
    }
  };

  return (
    <div className="chatbot-container">
      <div className="chatbot-header">
        <div className="header-content">
          <h3 className="chatbot-title">AI Assistant</h3>
          <p className="chatbot-subtitle">Ask questions or upload animal photos</p>
        </div>
        <button 
          onClick={clearConversation} 
          className="clear-btn"
          title="Clear conversation"
        >
          🗑️
        </button>
      </div>

      <div className="chatbot-messages">
        {messages.map((message, index) => (
          <div key={index} className={`message ${message.type}`}>
            {message.type === 'assistant' && (
              <div className="message-icon">
                <svg className="icon-museum" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M3 21h18"></path>
                  <path d="M5 21V7l7-4 7 4v14"></path>
                  <path d="M9 21v-6h6v6"></path>
                </svg>
              </div>
            )}
            <div className="message-bubble">
              {message.image && (
                <div className="message-image">
                  <img src={message.image} alt="User uploaded" />
                </div>
              )}
              <div 
                className="message-text"
                dangerouslySetInnerHTML={{ __html: formatMessageText(message.text) }} 
              />
            </div>
            {message.type === 'user' && (
              <div className="message-icon user-icon">
                <span>U</span>
              </div>
            )}
          </div>
        ))}
        
        {isLoading && (
          <div className="message assistant">
            <div className="message-icon">
              <svg className="icon-museum" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M3 21h18"></path>
                <path d="M5 21V7l7-4 7 4v14"></path>
                <path d="M9 21v-6h6v6"></path>
              </svg>
            </div>
            <div className="message-bubble loading">
              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
              <span>{selectedImage ? 'Analyzing image...' : 'Thinking...'}</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Image preview */}
      {imagePreview && !showCamera && (
        <div className="image-preview">
          <img src={imagePreview} alt="Preview" />
          <button onClick={clearImage} className="remove-image-btn">✕</button>
        </div>
      )}

      {/* Camera view */}
      {showCamera && (
        <div className="camera-view">
          <video 
            ref={videoRef} 
            autoPlay 
            playsInline
            className="camera-video"
          />
          <canvas 
            ref={canvasRef} 
            style={{ display: 'none' }}
          />
          <div className="camera-controls">
            <button onClick={capturePhoto} className="capture-btn">
              📸 Capture
            </button>
            <button onClick={stopCamera} className="cancel-btn">
              ✕ Cancel
            </button>
          </div>
        </div>
      )}

      {/* Suggestions - Show only when no user messages exist
      {messages.filter(msg => msg.type === 'user').length === 0 && (
        <div className="suggestions-section">
          <div className="suggestions-list">
            {suggestions.map((suggestion, index) => (
              <button
                key={index}
                className="suggestion-btn"
                onClick={() => handleSuggestionClick(suggestion)}
                disabled={isLoading}
              >
                {suggestion}
              </button>
            ))}
          </div>
        </div>
      )}
      */}

      {/* Input area */}
      <div className="chatbot-input-area">
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleImageSelect}
          accept="image/*"
          style={{ display: 'none' }}
        />
        <button 
          onClick={() => fileInputRef.current?.click()} 
          className="upload-btn" 
          title="Upload image"
          disabled={isLoading || showCamera}
        >
          📁
        </button>
        <button 
          onClick={startCamera} 
          className="camera-btn" 
          title="Take photo"
          disabled={isLoading || showCamera}
        >
          📷
        </button>
        <input
          type="text"
          placeholder={selectedImage ? "Add a message about this image..." : "Ask me anything..."}
          value={inputMessage}
          onChange={(e) => setInputMessage(e.target.value)}
          onKeyPress={handleKeyPress}
          disabled={isLoading || showCamera}
          className="chat-input"
        />
        <button 
          onClick={() => handleSendMessage()} 
          disabled={isLoading || showCamera || (!inputMessage.trim() && !selectedImage)} 
          className="send-btn"
        >
          {isLoading ? '...' : 'Send'}
        </button>
      </div>
    </div>
  );
}

export default Chatbot;