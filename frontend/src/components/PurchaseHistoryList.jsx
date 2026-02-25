import React from 'react';
import { Package, Calendar, DollarSign } from 'lucide-react';

const PurchaseHistoryList = ({ orders }) => {
  if (!orders || orders.length === 0) {
    return null;
  }

  // Format date to readable string
  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  return (
    <div className="mt-3 space-y-4">
      <div className="text-sm text-gray-600 font-medium mb-3">
        {orders.length} {orders.length === 1 ? 'order' : 'orders'} found
      </div>

      {orders.map((order) => (
        <div
          key={order.orderNumber}
          className="border border-gray-200 rounded-lg bg-white shadow-sm hover:shadow-md transition-shadow"
        >
          {/* Order Header */}
          <div className="px-4 py-3 border-b border-gray-200 bg-gray-50 rounded-t-lg">
            <div className="flex justify-between items-start">
              <div className="flex items-center gap-2 text-sm text-gray-700">
                <Calendar className="w-4 h-4 text-gray-500" />
                <span className="font-medium">{formatDate(order.orderDate)}</span>
              </div>
              <div className="text-right">
                <div className="text-sm text-gray-600">
                  ({order.lineItems.length} {order.lineItems.length === 1 ? 'item' : 'items'})
                </div>
                <div className="text-base font-semibold text-gray-900">
                  ${order.totalPrice.toFixed(2)}
                </div>
              </div>
            </div>
          </div>

          {/* Line Items */}
          <div className="divide-y divide-gray-100">
            {order.lineItems
              .filter((item) => !item.name.toLowerCase().includes('environmental handling fee'))
              .map((item, index) => (
                <div key={`${item.sku}-${index}`} className="px-4 py-3 flex gap-3 hover:bg-gray-50 transition-colors">
                  {/* Product Image */}
                  <div className="flex-shrink-0">
                    <img
                      src={item.imgUrl.replace('//', 'https://')}
                      alt={item.name}
                      className="w-20 h-20 object-contain rounded border border-gray-200"
                      onError={(e) => {
                        e.target.src = 'https://via.placeholder.com/80?text=No+Image';
                      }}
                    />
                  </div>

                  {/* Product Info */}
                  <div className="flex-1 min-w-0">
                    <h4 className="text-sm font-medium text-gray-900 line-clamp-2 mb-1">
                      {item.name}
                    </h4>
                    <div className="flex items-center gap-4 text-xs text-gray-600">
                      <span>Quantity: {item.quantity}</span>
                      <span className="flex items-center gap-1">
                        <DollarSign className="w-3 h-3" />
                        {item.total.toFixed(2)}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
          </div>

          {/* Order Footer */}
          <div className="px-4 py-3 bg-gray-50 rounded-b-lg border-t border-gray-200">
            <div className="flex justify-between items-center">
              <div className="flex items-center gap-2">
                <Package className="w-4 h-4 text-gray-500" />
                <div>
                  <div className="text-xs text-gray-500">Order Number</div>
                  <div className="text-sm font-mono font-medium text-gray-900">
                    {order.orderNumber}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span
                  className={`px-2 py-1 text-xs font-medium rounded ${
                    order.status === 'InProcess'
                      ? 'bg-blue-100 text-blue-700'
                      : order.status === 'Delivered'
                      ? 'bg-green-100 text-green-700'
                      : order.status === 'Shipped'
                      ? 'bg-purple-100 text-purple-700'
                      : 'bg-gray-100 text-gray-700'
                  }`}
                >
                  {order.status}
                </span>
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};

export default PurchaseHistoryList;

