import React from 'react';
import { Trash2, User as UserIcon } from 'lucide-react';
import { useChat } from '../hooks/useChat';
import MessageList from './MessageList';
import InputBox from './InputBox';

// Map userId → display name (mirrors the options in the dropdown)
const USER_NAMES = {
  user_001: 'Kai',
  user_002: 'Jane',
  user_003: 'Bob',
};

const ChatInterface = () => {
  const [userId, setUserId] = React.useState(
    localStorage.getItem('userId') || 'user_001'
  );

  // Derive first name for the greeting message
  const userName = USER_NAMES[userId] || 'there';

  const { messages, loading, sendMessage, executeAction, clearMessages } = useChat(userName);

  React.useEffect(() => {
    localStorage.setItem('userId', userId);
  }, [userId]);

  const handleSend = async (message) => {
    try {
      await sendMessage(message);
    } catch (error) {
      console.error('Error sending message:', error);
    }
  };

  const handlePurchase = async (productId) => {
    try {
      await executeAction('purchase', productId);
    } catch (error) {
      console.error('Error purchasing product:', error);
    }
  };

  const handleEmail = async (productId) => {
    try {
      await executeAction('email', productId);
    } catch (error) {
      console.error('Error emailing product:', error);
    }
  };

  const handleUserChange = (e) => {
    setUserId(e.target.value);
    clearMessages();
  };

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                Product Recommendation Assistant - Bestbuy
              </h1>
              <p className="text-sm text-gray-600 mt-1">
                Powered by AI • Find your perfect product
              </p>
            </div>

            <div className="flex items-center gap-4">
              {/* User Selector */}
              <div className="flex items-center gap-2">
                <UserIcon className="w-5 h-5 text-gray-500" />
                <select
                  value={userId}
                  onChange={handleUserChange}
                  className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                >
                  <option value="user_001">Kai He</option>
                  <option value="user_002">Jane Smith</option>
                  <option value="user_003">Bob Johnson</option>
                </select>
              </div>

              {/* Clear Chat */}
              <button
                onClick={clearMessages}
                className="flex items-center gap-2 px-4 py-2 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
                title="Clear chat history"
              >
                <Trash2 className="w-4 h-4" />
                <span className="hidden sm:inline">Clear Chat</span>
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Chat Messages */}
      <div className="flex-1 overflow-hidden">
        <div className="max-w-7xl mx-auto h-full flex flex-col">
          <MessageList
            messages={messages}
            onPurchase={handlePurchase}
            onEmail={handleEmail}
            loading={loading}
          />
        </div>
      </div>

      {/* Input */}
      <InputBox onSend={handleSend} loading={loading} disabled={false} />

      {/* Footer */}
      <footer className="bg-white border-t py-2">
        <div className="max-w-7xl mx-auto px-4">
          <p className="text-xs text-gray-500 text-center">
            This is a demo application. Product recommendations are based on AI analysis.
          </p>
        </div>
      </footer>
    </div>
  );
};

export default ChatInterface;
