import React from 'react';
import { ShoppingCart, Mail, Tag, Package } from 'lucide-react';

const ProductCard = ({ product, onPurchase, onEmail, loading }) => {
  return (
    <div className="bg-white rounded-lg shadow-md overflow-hidden hover:shadow-lg transition-shadow duration-200">
      {/* Product Image */}
      {product.image_url && (
        <div className="w-full h-48 bg-gray-200">
          <img
            src={product.image_url}
            alt={product.name}
            className="w-full h-full object-cover"
            onError={(e) => {
              e.target.style.display = 'none';
            }}
          />
        </div>
      )}

      <div className="p-4">
        {/* Product Name and Category */}
        <div className="flex items-start justify-between mb-2">
          <h3 className="text-lg font-semibold text-gray-900 flex-1">
            {product.name}
          </h3>
          {product.relevance_score && (
            <span className="ml-2 px-2 py-1 text-xs bg-primary-100 text-primary-700 rounded-full">
              {Math.round(product.relevance_score * 100)}% match
            </span>
          )}
        </div>

        <div className="flex items-center gap-2 mb-3">
          <Tag className="w-4 h-4 text-gray-500" />
          <span className="text-sm text-gray-600">{product.category}</span>
        </div>

        {/* Description */}
        <p className="text-sm text-gray-600 mb-3 line-clamp-2">
          {product.description}
        </p>

        {/* Price and Stock */}
        <div className="flex items-center justify-between mb-4">
          <span className="text-2xl font-bold text-primary-600">
            ${product.price?.toFixed(2)}
          </span>
          <div className="flex items-center gap-1 text-sm text-gray-600">
            <Package className="w-4 h-4" />
            <span>{product.stock} in stock</span>
          </div>
        </div>

        {/* Specifications */}
        {product.specifications && Object.keys(product.specifications).length > 0 && (
          <div className="mb-4 p-3 bg-gray-50 rounded">
            <h4 className="text-xs font-semibold text-gray-700 mb-2">
              Key Features:
            </h4>
            <div className="text-xs text-gray-600 space-y-1">
              {Object.entries(product.specifications).slice(0, 3).map(([key, value]) => (
                <div key={key} className="flex justify-between">
                  <span className="capitalize">{key.replace(/_/g, ' ')}:</span>
                  <span className="font-medium">{String(value)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex gap-2">
          <button
            onClick={() => onPurchase(product.product_id)}
            disabled={loading || product.stock === 0}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
          >
            <ShoppingCart className="w-4 h-4" />
            <span>{product.stock === 0 ? 'Out of Stock' : 'Purchase'}</span>
          </button>

          <button
            onClick={() => onEmail(product.product_id)}
            disabled={loading}
            className="px-4 py-2 border border-primary-600 text-primary-600 rounded-lg hover:bg-primary-50 disabled:border-gray-300 disabled:text-gray-300 disabled:cursor-not-allowed transition-colors"
            title="Email product details"
          >
            <Mail className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};

export default ProductCard;
