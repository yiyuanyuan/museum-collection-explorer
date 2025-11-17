import React, { useState, useEffect, useRef } from 'react';
import './Chatbot.css';
import { sendChatMessage, getChatSuggestions } from '../../services/api';
import posthog from 'posthog-js';

function Chatbot() {
  const [messages, setMessages] = useState([
    {
      type: 'assistant',
      text: 'Welcome to the Australian Museum Collection Explorer! I can help you learn about specimens in our collection and identify animals from photos. I can search specimens by scientific or common name, location, date, or catalog number. Try uploading an image or asking me a question!'
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
    const id = 'session_' + Math.random().toString(36).substr(2, 9);
    
    // Track new conversation session started
    posthog.capture('chatbot_session_started', {
      session_id: id,
      timestamp: new Date().toISOString()
    });
    
    return id;
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
        
        // Track image upload error
        posthog.capture('chatbot_image_error', {
          error: 'File too large',
          file_size_mb: (file.size / 1024 / 1024).toFixed(2),
          session_id: sessionId
        });
        
        return;
      }

      const reader = new FileReader();
      reader.onloadend = () => {
        setSelectedImage(reader.result);
        setImagePreview(reader.result);
        
        // Track image upload
        posthog.capture('chatbot_image_uploaded', {
          file_size_mb: (file.size / 1024 / 1024).toFixed(2),
          file_type: file.type,
          upload_method: 'file_select',
          session_id: sessionId
        });
      };
      reader.readAsDataURL(file);
    }
  };

  const startCamera = async () => {
    try {
      // Request camera with fallback options
      let constraints = { 
        video: { 
          facingMode: 'environment',
          width: { ideal: 1280 },
          height: { ideal: 720 }
        } 
      };
      
      let stream;
      try {
        stream = await navigator.mediaDevices.getUserMedia(constraints);
      } catch (err) {
        // Fallback: try without facingMode (for desktop)
        console.log('Trying fallback camera constraints...');
        stream = await navigator.mediaDevices.getUserMedia({ video: true });
      }
      
      streamRef.current = stream;
      setShowCamera(true);
      
      // Track camera opened
      posthog.capture('chatbot_camera_opened', {
        session_id: sessionId
      });
      
      // Wait for next tick to ensure video element is rendered
      setTimeout(() => {
        if (videoRef.current && stream) {
          videoRef.current.srcObject = stream;
          // Explicitly play the video
          videoRef.current.play().catch(e => {
            console.error('Error playing video:', e);
          });
        }
      }, 100);
      
    } catch (error) {
      console.error('Error accessing camera:', error);
      let errorMessage = 'Unable to access camera. ';
      
      if (error.name === 'NotAllowedError' || error.name === 'PermissionDeniedError') {
        errorMessage += 'Please grant camera permissions in your browser settings.';
      } else if (error.name === 'NotFoundError') {
        errorMessage += 'No camera found on this device.';
      } else if (error.name === 'NotReadableError') {
        errorMessage += 'Camera is already in use by another application.';
      } else {
        errorMessage += 'Please check your camera settings and try again.';
      }
      
      // Track camera error
      posthog.capture('chatbot_camera_error', {
        error_type: error.name,
        error_message: errorMessage,
        session_id: sessionId
      });
      
      alert(errorMessage);
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
      
      // Check if video is actually playing and has dimensions
      if (video.videoWidth === 0 || video.videoHeight === 0) {
        alert('Camera feed not ready. Please wait a moment and try again.');
        return;
      }
      
      // Set canvas dimensions to match video
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      
      const context = canvas.getContext('2d');
      
      // Draw the current video frame to canvas
      context.drawImage(video, 0, 0, canvas.width, canvas.height);
      
      // Convert canvas to base64 image
      const imageData = canvas.toDataURL('image/jpeg', 0.9);
      
      // Verify we actually captured something
      if (imageData && imageData.length > 100) {
        setSelectedImage(imageData);
        setImagePreview(imageData);
        
        // Track photo captured
        posthog.capture('chatbot_photo_captured', {
          upload_method: 'camera',
          resolution: `${video.videoWidth}x${video.videoHeight}`,
          session_id: sessionId
        });
        
        // Stop camera after successful capture
        stopCamera();
      } else {
        alert('Failed to capture image. Please try again.');
      }
    }
  };

  const handleSendMessage = async (message = inputMessage) => {
    if (!message.trim() && !selectedImage) return;

    const messageText = message || (selectedImage ? 'Please analyse this image' : '');
    const hasImage = !!selectedImage;
    const messageStartTime = Date.now();

    // Track user message sent
    posthog.capture('chatbot_user_message', {
      message: messageText,
      message_length: messageText.length,
      has_image: hasImage,
      session_id: sessionId,
      timestamp: new Date().toISOString()
    });

    // Create user message
    const userMessage = {
      type: 'user',
      text: messageText,
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

      const responseTime = Date.now() - messageStartTime;

      // Handle response
      if (response.success) {
        const assistantMessage = {
          type: 'assistant',
          text: response.response
        };
        setMessages(prev => [...prev, assistantMessage]);

        // Track bot response received
        posthog.capture('chatbot_bot_response', {
          user_message: messageText,
          bot_response: response.response,
          response_length: response.response.length,
          response_time_ms: responseTime,
          had_image: hasImage,
          session_id: sessionId,
          timestamp: new Date().toISOString()
        });

        // Update suggestions if provided - limit to 3
        if (response.suggestions) {
          setSuggestions(response.suggestions.slice(0, 3));
        }
      } else {
        throw new Error(response.error || 'Unknown error');
      }
    } catch (error) {
      console.error('Error sending message:', error);
      
      // Track error
      posthog.capture('chatbot_error', {
        error_message: error.message,
        user_message: messageText,
        had_image: hasImage,
        session_id: sessionId,
        timestamp: new Date().toISOString()
      });
      
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
    // Track suggestion click
    posthog.capture('chatbot_suggestion_clicked', {
      suggestion: suggestion,
      session_id: sessionId
    });
    
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

  const parseUrlsWithQuotedParams = (text) => {
    const urlRegex = /https?:\/\/[^\s]+/g;
    const matches = [...text.matchAll(urlRegex)];
    
    if (matches.length === 0) {
      return [{ type: 'text', content: text }];
    }
    
    let result = [];
    let currentPos = 0;
    
    for (const match of matches) {
      const startIndex = match.index;
      
      // Add text before URL
      if (startIndex > currentPos) {
        result.push({
          type: 'text',
          content: text.substring(currentPos, startIndex)
        });
      }
      
      // Parse the URL character by character
      let i = startIndex;
      let inQuotedSection = false;
      let quoteCount = 0;
      
      while (i < text.length) {
        const char = text[i];
        const nextChar = i + 1 < text.length ? text[i + 1] : '';
        const next2Chars = i + 2 < text.length ? text.substring(i, i + 3) : '';
        
        // Check for %22 (URL-encoded quote)
        if (next2Chars === '%22') {
          quoteCount++;
          inQuotedSection = (quoteCount % 2 === 1);
          i += 3;
          continue;
        }
        
        // If we're in a quoted section, allow spaces and continue
        if (inQuotedSection) {
          i++;
          continue;
        }
        
        // Outside quoted sections, stop at whitespace or sentence-ending punctuation
        if (char === ' ' || char === '\n' || char === '\t' || char === '\r') {
          break;
        }
        
        // Stop at characters that typically end a URL in text
        // Note: Don't stop at [ or ] as they're valid in URLs (e.g., year ranges)
        if (char === ')' || char === '"' || char === "'" || char === '<' || char === '>') {
          break;
        }
        
        i++;
      }
      
      // Extract the complete URL
      const url = text.substring(startIndex, i);
      
      // Clean up trailing punctuation (but keep it if part of URL structure)
      let cleanUrl = url;
      if (/[.,;!?]+$/.test(cleanUrl) && !cleanUrl.includes('?')) {
        cleanUrl = cleanUrl.replace(/[.,;!?]+$/, '');
      }
      
      result.push({
        type: 'url',
        content: cleanUrl
      });
      
      currentPos = startIndex + url.length;
    }
    
    // Add remaining text
    if (currentPos < text.length) {
      result.push({
        type: 'text',
        content: text.substring(currentPos)
      });
    }
    
    return result;
  };

  const formatMessageText = (text) => {
    // Handle bold text first
    text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    
    // Handle line breaks
    text = text.replace(/\n/g, '<br>');
    
    // Parse URLs with our custom parser
    const parsed = parseUrlsWithQuotedParams(text);
    
    // Convert parsed segments to HTML
    return parsed.map(segment => {
      if (segment.type === 'url') {
        return `<a href="${segment.content}" target="_blank" rel="noopener noreferrer" style="color: #0066cc; text-decoration: underline;">${segment.content}</a>`;
      } else {
        return segment.content;
      }
    }).join('');
  };

  const clearConversation = async () => {
    if (window.confirm('Are you sure you want to clear the conversation?')) {
      // Track conversation cleared
      posthog.capture('chatbot_conversation_cleared', {
        message_count: messages.length,
        session_id: sessionId,
        timestamp: new Date().toISOString()
      });
      
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

      {/* Suggestions - always show 3 */}
      {suggestions.length > 0 && messages.length <= 2 && (
        <div className="suggestions">
          {suggestions.map((suggestion, index) => (
            <button 
              key={index}
              onClick={() => handleSuggestionClick(suggestion)}
              className="suggestion-chip"
              disabled={isLoading}
            >
              {suggestion}
            </button>
          ))}
        </div>
      )}

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
            muted
            className="camera-video"
            onLoadedMetadata={(e) => {
              // Ensure video starts playing once metadata is loaded
              e.target.play().catch(err => console.error('Play error:', err));
            }}
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
          📎
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