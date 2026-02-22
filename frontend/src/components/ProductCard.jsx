import React from 'react';
import { ShoppingCart, Mail, Tag, Star, ExternalLink } from 'lucide-react';

const ProductCard = ({ product, onPurchase, onEmail, loading }) => {
  // Render filled/half/empty stars for customerRating
  const renderStars = (rating) => {
    if (!rating) return null;
    const full = Math.floor(rating);
    const half = rating % 1 >= 0.5;
    const empty = 5 - full - (half ? 1 : 0);
    return (
      <div className="flex items-center gap-0.5">
        {Array.from({ length: full }).map((_, i) => (
          <Star key={`f${i}`} className="w-3.5 h-3.5 fill-amber-400 text-amber-400" />
        ))}
        {half && (
          <span className="relative w-3.5 h-3.5">
            <Star className="absolute w-3.5 h-3.5 text-gray-300" />
            <span className="absolute overflow-hidden w-1/2">
              <Star className="w-3.5 h-3.5 fill-amber-400 text-amber-400" />
            </span>
          </span>
        )}
        {Array.from({ length: empty }).map((_, i) => (
          <Star key={`e${i}`} className="w-3.5 h-3.5 text-gray-300" />
        ))}
        <span className="ml-1 text-xs text-gray-500">{rating.toFixed(1)}</span>
      </div>
    );
  };

  const hasSavings = product.isOnSale && product.regularPrice > product.salePrice;

  return (
    <div className="bg-white rounded-xl shadow-md overflow-hidden hover:shadow-lg transition-shadow duration-200 flex flex-col">

      {/* Product Image */}
      {product.highResImage ? (
        <div className="w-full h-48 bg-gray-100 flex items-center justify-center overflow-hidden">
          <img
            src={product.highResImage}
            alt={product.name}
            className="w-full h-full object-contain p-2"
            onError={(e) => {
              e.target.parentElement.style.display = 'none';
            }}
          />
        </div>
      ) : (
        <div className="w-full h-48 bg-gradient-to-br from-gray-100 to-gray-200 flex items-center justify-center">
          <ShoppingCart className="w-12 h-12 text-gray-300" />
        </div>
      )}

      <div className="p-4 flex flex-col flex-1">

        {/* Sale badge */}
        {product.isOnSale && (
          <span className="self-start mb-2 px-2 py-0.5 text-xs font-semibold bg-red-100 text-red-600 rounded-full uppercase tracking-wide">
            On Sale
          </span>
        )}

        {/* Product name */}
        <h3 className="text-sm font-semibold text-gray-900 mb-1 line-clamp-2 leading-snug">
          {product.name}
        </h3>

        {/* Category */}
        <div className="flex items-center gap-1.5 mb-2">
          <Tag className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
          <span className="text-xs text-gray-500 truncate">{product.categoryName}</span>
        </div>

        {/* Star rating */}
        {product.customerRating && (
          <div className="mb-2">
            {renderStars(product.customerRating)}
          </div>
        )}

        {/* Short description */}
        <p className="text-xs text-gray-600 mb-3 line-clamp-2 flex-1">
          {product.shortDescription}
        </p>

        {/* Pricing block */}
        <div className="mb-3">
          <div className="flex items-baseline gap-2">
            <span className="text-xl font-bold text-blue-600">
              ${product.salePrice?.toFixed(2)}
            </span>
            {hasSavings && (
              <span className="text-sm text-gray-400 line-through">
                ${product.regularPrice?.toFixed(2)}
              </span>
            )}
          </div>
          {hasSavings && (
            <p className="text-xs font-medium text-green-600 mt-0.5">
              Save ${(product.regularPrice - product.salePrice).toFixed(2)} CAD
            </p>
          )}
          {!product.isOnSale && (
            <p className="text-xs text-gray-400 mt-0.5">Regular price</p>
          )}
        </div>

        {/* BestBuy link */}
        {product.productUrl && (
          <a
            href={product.productUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-xs text-blue-500 hover:text-blue-700 hover:underline mb-3 w-fit"
          >
            <ExternalLink className="w-3 h-3" />
            View on BestBuy
          </a>
        )}

        {/* Action buttons */}
        <div className="flex gap-2 mt-auto">
          <button
            onClick={() => onPurchase(product.sku)}
            disabled={loading}
            className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
          >
            <ShoppingCart className="w-4 h-4" />
            Purchase
          </button>
          <button
            onClick={() => onEmail(product.sku)}
            disabled={loading}
            className="px-3 py-2 border border-blue-600 text-blue-600 rounded-lg hover:bg-blue-50 disabled:border-gray-300 disabled:text-gray-300 disabled:cursor-not-allowed transition-colors"
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
