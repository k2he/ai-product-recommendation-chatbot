import React, { useEffect, useRef } from 'react';
import { Bot, User, AlertCircle, CheckCircle, Loader2 } from 'lucide-react';
import ProductCard from './ProductCard';
import PurchaseHistoryList from './PurchaseHistoryList';

const MessageList = ({ messages, onPurchase, onEmail, loading }) => {
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const renderMessage = (message) => {
    switch (message.type) {

      /* ── User message ──────────────────────────────────────────────── */
      case 'user':
        return (
          <div key={message.id} className="flex justify-end mb-4">
            <div className="flex items-start gap-2 max-w-[80%]">
              <div className="bg-blue-600 text-white rounded-lg rounded-tr-none px-4 py-3">
                <p className="text-sm">{message.content}</p>
              </div>
              <div className="flex-shrink-0 w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center">
                <User className="w-5 h-5 text-white" />
              </div>
            </div>
          </div>
        );

      /* ── Optimistic "thinking" message ─────────────────────────────── */
      case 'thinking':
        return (
          <div key={message.id} className="flex justify-start mb-4">
            <div className="flex items-start gap-2 max-w-[85%]">
              <div className="flex-shrink-0 w-8 h-8 bg-gray-200 rounded-full flex items-center justify-center">
                <Bot className="w-5 h-5 text-gray-600" />
              </div>
              <div className="bg-gray-100 rounded-lg rounded-tl-none px-4 py-3 flex items-center gap-2">
                <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />
                <p className="text-sm text-gray-600 italic">{message.content}</p>
              </div>
            </div>
          </div>
        );

      /* ── Assistant message ─────────────────────────────────────────── */
      case 'assistant': {
        return (
          <div key={message.id} className="flex justify-start mb-4">
            <div className="flex items-start gap-2 max-w-[90%]">
              <div className="flex-shrink-0 w-8 h-8 bg-gray-200 rounded-full flex items-center justify-center">
                <Bot className="w-5 h-5 text-gray-600" />
              </div>
              <div className="flex-1">

                {/* Main response text */}
                <div className="bg-gray-100 rounded-lg rounded-tl-none px-4 py-3 mb-2">
                  <p className="text-sm text-gray-800 whitespace-pre-wrap">{message.content}</p>
                  {message.source && (
                    <p className="text-xs text-gray-400 mt-2">
                      Source:{' '}
                      {message.source === 'vector_db'
                        ? 'Pinecone Database'
                        : message.source === 'none'
                        ? 'No Results'
                        : message.source === 'action'
                        ? 'Action'
                        : message.source === 'general_chat'
                        ? 'Conversation'
                        : message.source === 'general_chat_with_search'
                        ? 'Conversation with Web Search (Tavily)'
                        : message.source === 'purchase_history'
                        ? 'Purchase History'
                        : 'N/A'}
                    </p>
                  )}
                </div>

                {/* Product cards grid */}
                {message.products && message.products.length > 0 && (
                  <>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mt-2">
                      {message.products.map((product) => (
                        <ProductCard
                          key={product.sku}
                          product={product}
                          onPurchase={onPurchase}
                          onEmail={onEmail}
                          loading={loading}
                        />
                      ))}
                    </div>

                    {/* CTA banner — always shown when products are present */}
                    <div className="flex items-start gap-2 bg-blue-50 border border-blue-200 rounded-lg px-4 py-3 mt-4">
                      <span className="text-lg leading-none mt-0.5">📬</span>
                      <p className="text-sm font-semibold text-blue-700 leading-snug">
                        Want to go further? <strong>Send these product details to your email</strong> or <strong>purchase one right now</strong> — just let me know!
                      </p>
                    </div>
                  </>
                )}

                {/* Purchase History List */}
                {message.purchaseHistory && message.purchaseHistory.length > 0 && (
                  <PurchaseHistoryList orders={message.purchaseHistory} />
                )}

              </div>
            </div>
          </div>
        );
      }

      /* ── Action result banner ──────────────────────────────────────── */
      case 'action_result':
        return (
          <div key={message.id} className="flex justify-center mb-4">
            <div
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm max-w-[80%] ${
                message.success
                  ? 'bg-green-100 text-green-800 border border-green-200'
                  : 'bg-red-100 text-red-800 border border-red-200'
              }`}
            >
              {message.success ? (
                <CheckCircle className="w-4 h-4 flex-shrink-0" />
              ) : (
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
              )}
              {/* Render **bold** from action confirmation messages */}
              <span
                dangerouslySetInnerHTML={{
                  __html: message.content.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>'),
                }}
              />
            </div>
          </div>
        );

      /* ── Error message ─────────────────────────────────────────────── */
      case 'error':
        return (
          <div key={message.id} className="flex justify-center mb-4">
            <div className="flex items-center gap-2 px-4 py-2 bg-red-100 text-red-800 border border-red-200 rounded-lg text-sm">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{message.content}</span>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="flex-1 overflow-y-auto px-4 py-6">
      {messages.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-full text-gray-500">
          <Bot className="w-16 h-16 mb-4 text-gray-300" />
          <h3 className="text-xl font-semibold mb-2 text-gray-700">Welcome to Product Assistant!</h3>
          <p className="text-center text-sm max-w-md text-gray-500">
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
