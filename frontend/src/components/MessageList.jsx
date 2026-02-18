import React, { useEffect, useRef } from 'react';
import { Bot, User, AlertCircle, CheckCircle } from 'lucide-react';
import ProductCard from './ProductCard';

const MessageList = ({ messages, onPurchase, onEmail, loading }) => {
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const renderMessage = (message) => {
    switch (message.type) {
      case 'user':
        return (
          <div key={message.id} className="flex justify-end mb-4">
            <div className="flex items-start gap-2 max-w-[80%]">
              <div className="bg-primary-600 text-white rounded-lg rounded-tr-none px-4 py-3">
                <p className="text-sm">{message.content}</p>
              </div>
              <div className="flex-shrink-0 w-8 h-8 bg-primary-600 rounded-full flex items-center justify-center">
                <User className="w-5 h-5 text-white" />
              </div>
            </div>
          </div>
        );

      case 'assistant':
        return (
          <div key={message.id} className="flex justify-start mb-4">
            <div className="flex items-start gap-2 max-w-[85%]">
              <div className="flex-shrink-0 w-8 h-8 bg-gray-200 rounded-full flex items-center justify-center">
                <Bot className="w-5 h-5 text-gray-600" />
              </div>
              <div className="flex-1">
                <div className="bg-gray-100 rounded-lg rounded-tl-none px-4 py-3 mb-3">
                  <p className="text-sm text-gray-800 whitespace-pre-wrap">
                    {message.content}
                  </p>
                  {message.source && (
                    <p className="text-xs text-gray-500 mt-2">
                      Source: {message.source === 'vector_db' ? 'Product Database' : 
                               message.source === 'web_search' ? 'Web Search' : 'N/A'}
                    </p>
                  )}
                </div>

                {/* Product Cards */}
                {message.products && message.products.length > 0 && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-3">
                    {message.products.map((product) => (
                      <ProductCard
                        key={product.product_id}
                        product={product}
                        onPurchase={onPurchase}
                        onEmail={onEmail}
                        loading={loading}
                      />
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        );

      case 'action_result':
        return (
          <div key={message.id} className="flex justify-center mb-4">
            <div className={`flex items-center gap-2 px-4 py-2 rounded-lg ${
              message.success 
                ? 'bg-green-100 text-green-800' 
                : 'bg-red-100 text-red-800'
            }`}>
              {message.success ? (
                <CheckCircle className="w-4 h-4" />
              ) : (
                <AlertCircle className="w-4 h-4" />
              )}
              <span className="text-sm">{message.content}</span>
            </div>
          </div>
        );

      case 'error':
        return (
          <div key={message.id} className="flex justify-center mb-4">
            <div className="flex items-center gap-2 px-4 py-2 bg-red-100 text-red-800 rounded-lg">
              <AlertCircle className="w-4 h-4" />
              <span className="text-sm">{message.content}</span>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4">
      {messages.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-full text-gray-500">
          <Bot className="w-16 h-16 mb-4 text-gray-400" />
          <h3 className="text-xl font-semibold mb-2">Welcome to Product Assistant!</h3>
          <p className="text-center text-sm max-w-md">
            I'm here to help you find the perfect products. Just tell me what you're looking for!
          </p>
        </div>
      ) : (
        <>
          {messages.map(renderMessage)}
          <div ref={messagesEndRef} />
        </>
      )}
    </div>
  );
};

export default MessageList;
