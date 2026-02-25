import React, { useEffect, useRef, useState } from 'react';
import { Bot, User, AlertCircle, CheckCircle, Loader2, UserCircle, Package, ChevronDown, ChevronUp, ShoppingBag } from 'lucide-react';
import ProductCard from './ProductCard';

/**
 * OrderCard component - Displays a single order with collapsible line items
 */
const OrderCard = ({ order }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const orderDate = new Date(order.orderDate);
  const formattedDate = orderDate.toLocaleDateString('en-US', {
    month: 'long',
    day: '2-digit',
    year: 'numeric'
  });

  const itemCount = order.lineItems.length;
  const itemWord = itemCount === 1 ? 'item' : 'items';

  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-sm mb-3">
      {/* Order Header - Clickable to expand/collapse */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <Package className="w-5 h-5 text-gray-600" />
          <div className="text-left">
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-gray-900">{formattedDate}</span>
              <span className="text-xs text-gray-500">•</span>
              <span className="text-xs text-gray-500">Order #{order.orderNumber}</span>
            </div>
            <div className="text-xs text-gray-600 mt-0.5">
              {itemCount} {itemWord} • ${order.totalPrice.toFixed(2)}
            </div>
          </div>
        </div>
        {isExpanded ? (
          <ChevronUp className="w-5 h-5 text-gray-400" />
        ) : (
          <ChevronDown className="w-5 h-5 text-gray-400" />
        )}
      </button>

      {/* Line Items - Collapsible */}
      {isExpanded && (
        <div className="px-4 pb-3 border-t border-gray-100">
          <div className="mt-3 space-y-2">
            {order.lineItems.map((item, idx) => (
              <div key={idx} className="flex items-center gap-3 p-2 hover:bg-gray-50 rounded">
                <img
                  src={item.imgUrl}
                  alt={item.name}
                  className="w-16 h-16 object-contain rounded border border-gray-200"
                  onError={(e) => {
                    e.target.src = 'https://via.placeholder.com/150?text=No+Image';
                  }}
                />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">{item.name}</p>
                  <p className="text-xs text-gray-500 mt-0.5">
                    SKU: {item.sku}
                  </p>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-xs text-gray-600">Qty: {item.quantity}</span>
                    <span className="text-xs text-gray-400">•</span>
                    <span className="text-sm font-semibold text-gray-900">${item.total.toFixed(2)}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

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
                        : message.source === 'user_info'
                        ? 'User Account'
                        : message.source === 'purchase_history'
                        ? 'Order History'
                        : 'N/A'}
                    </p>
                  )}
                </div>

                {/* User Info Card */}
                {message.userInfo && (
                  <div className="bg-gradient-to-br from-blue-50 to-indigo-50 border border-blue-200 rounded-lg p-4 mt-2">
                    <div className="flex items-start gap-3">
                      <div className="flex-shrink-0 w-10 h-10 bg-blue-500 rounded-full flex items-center justify-center">
                        <UserCircle className="w-6 h-6 text-white" />
                      </div>
                      <div className="flex-1">
                        <h3 className="text-sm font-semibold text-gray-900 mb-2">Account Information</h3>
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-gray-600 font-medium w-16">Name:</span>
                            <span className="text-sm text-gray-900">{message.userInfo.firstName} {message.userInfo.lastName}</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-gray-600 font-medium w-16">Email:</span>
                            <span className="text-sm text-gray-900">{message.userInfo.email}</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-gray-600 font-medium w-16">Phone:</span>
                            <span className="text-sm text-gray-900">{message.userInfo.phone}</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* Purchase History */}
                {message.purchaseHistory && message.purchaseHistory.length > 0 && (
                  <div className="mt-2">
                    <div className="flex items-center gap-2 mb-3">
                      <ShoppingBag className="w-5 h-5 text-gray-700" />
                      <h3 className="text-sm font-semibold text-gray-900">
                        Your Purchase History ({message.purchaseHistory.length} {message.purchaseHistory.length === 1 ? 'order' : 'orders'})
                      </h3>
                    </div>
                    {message.purchaseHistory.map((order) => (
                      <OrderCard key={order.orderNumber} order={order} />
                    ))}
                  </div>
                )}

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
