import React, { useState } from 'react';
import {
  Package, Calendar, ChevronDown, ChevronUp,
  ShoppingBag, Truck, CheckCircle2, Clock, Receipt,
} from 'lucide-react';

/* ── Helpers ──────────────────────────────────────────────────────────────── */

const formatDate = (dateString) => {
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
};

const STATUS_CONFIG = {
  InProcess: { label: 'In Process', icon: Clock,        bg: 'bg-blue-50',   text: 'text-blue-700',   border: 'border-blue-200',   dot: 'bg-blue-500'   },
  Shipped:   { label: 'Shipped',    icon: Truck,         bg: 'bg-purple-50', text: 'text-purple-700', border: 'border-purple-200', dot: 'bg-purple-500' },
  Delivered: { label: 'Delivered',  icon: CheckCircle2,  bg: 'bg-green-50',  text: 'text-green-700',  border: 'border-green-200',  dot: 'bg-green-500'  },
  default:   { label: 'Processing', icon: Clock,         bg: 'bg-gray-50',   text: 'text-gray-600',   border: 'border-gray-200',   dot: 'bg-gray-400'   },
};

const StatusBadge = ({ status }) => {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.default;
  const Icon = cfg.icon;
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border ${cfg.bg} ${cfg.text} ${cfg.border}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot}`} />
      <Icon className="w-3 h-3" />
      {cfg.label}
    </span>
  );
};

/* ── Order Card ───────────────────────────────────────────────────────────── */

const OrderCard = ({ order, index }) => {
  const [expanded, setExpanded] = useState(index === 0); // first order open by default

  const visibleItems = order.lineItems.filter(
    (item) => !item.name.toLowerCase().includes('environmental handling fee')
  );

  const itemCount = visibleItems.length;

  return (
    <div className="rounded-xl border border-gray-200 bg-white shadow-sm hover:shadow-md transition-shadow duration-200 overflow-hidden">

      {/* ── Order header (always visible) ─────────────────────────────── */}
      <button
        onClick={() => setExpanded((v) => !v)}
        className="w-full text-left px-4 py-3.5 flex items-center gap-3 hover:bg-gray-50 transition-colors"
      >
        {/* Order icon */}
        <div className="w-10 h-10 rounded-full bg-indigo-50 flex items-center justify-center flex-shrink-0">
          <ShoppingBag className="w-5 h-5 text-indigo-500" />
        </div>

        {/* Order meta */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-mono text-gray-500">#{order.orderNumber}</span>
            <StatusBadge status={order.status} />
          </div>
          <div className="flex items-center gap-1.5 mt-0.5 text-xs text-gray-500">
            <Calendar className="w-3 h-3" />
            {formatDate(order.orderDate)}
            <span className="text-gray-300">·</span>
            <Package className="w-3 h-3" />
            {itemCount} {itemCount === 1 ? 'item' : 'items'}
          </div>
        </div>

        {/* Total + chevron */}
        <div className="flex items-center gap-3 flex-shrink-0">
          <div className="text-right">
            <p className="text-xs text-gray-400">Total</p>
            <p className="text-base font-bold text-gray-900">${order.totalPrice.toFixed(2)}</p>
          </div>
          {expanded
            ? <ChevronUp className="w-4 h-4 text-gray-400" />
            : <ChevronDown className="w-4 h-4 text-gray-400" />}
        </div>
      </button>

      {/* ── Expandable line items ──────────────────────────────────────── */}
      {expanded && (
        <div className="border-t border-gray-100">
          <div className="divide-y divide-gray-50">
            {visibleItems.map((item, idx) => (
              <div key={`${item.sku}-${idx}`} className="flex gap-3 px-4 py-3 hover:bg-gray-50 transition-colors">

                {/* Product image */}
                <div className="flex-shrink-0 w-16 h-16 rounded-lg border border-gray-100 bg-gray-50 overflow-hidden flex items-center justify-center">
                  {item.imgUrl ? (
                    <img
                      src={item.imgUrl.replace('//', 'https://')}
                      alt={item.name}
                      className="w-full h-full object-contain p-1"
                      onError={(e) => {
                        e.target.style.display = 'none';
                        e.target.parentElement.innerHTML = '<span class="text-2xl">📦</span>';
                      }}
                    />
                  ) : (
                    <span className="text-2xl">📦</span>
                  )}
                </div>

                {/* Product details */}
                <div className="flex-1 min-w-0 flex flex-col justify-center">
                  <p className="text-sm font-medium text-gray-900 line-clamp-2 leading-snug mb-1">
                    {item.name}
                  </p>
                  <div className="flex items-center gap-3">
                    <span className="text-xs text-gray-500">Qty: <span className="font-semibold text-gray-700">{item.quantity}</span></span>
                    <span className="text-xs font-bold text-indigo-600">${item.total.toFixed(2)}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Order total footer */}
          <div className="px-4 py-3 bg-gray-50 border-t border-gray-100 flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs text-gray-500">
              <Receipt className="w-3.5 h-3.5" />
              <span>{itemCount} {itemCount === 1 ? 'item' : 'items'} · Order #{order.orderNumber}</span>
            </div>
            <div className="text-sm font-bold text-gray-900">
              Total: <span className="text-indigo-600">${order.totalPrice.toFixed(2)} CAD</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

/* ── Purchase History List ────────────────────────────────────────────────── */

const PurchaseHistoryList = ({ orders }) => {
  if (!orders || orders.length === 0) return null;

  const totalSpent = orders.reduce((sum, o) => sum + o.totalPrice, 0);
  const totalItems = orders.reduce((sum, o) => sum + o.lineItems.filter(
    (i) => !i.name.toLowerCase().includes('environmental handling fee')
  ).length, 0);

  return (
    <div className="mt-3 space-y-3 max-w-2xl">

      {/* ── Summary banner ──────────────────────────────────────────────── */}
      <div className="rounded-xl bg-gradient-to-r from-indigo-500 to-purple-600 px-5 py-4 flex items-center gap-4 shadow-sm">
        <div className="w-10 h-10 rounded-full bg-white/20 flex items-center justify-center flex-shrink-0">
          <ShoppingBag className="w-5 h-5 text-white" />
        </div>
        <div className="flex-1">
          <p className="text-white/80 text-xs font-medium uppercase tracking-wider">Purchase History</p>
          <p className="text-white font-bold text-base leading-tight">
            {orders.length} {orders.length === 1 ? 'Order' : 'Orders'} · {totalItems} Items
          </p>
        </div>
        <div className="text-right">
          <p className="text-white/70 text-xs">Total Spent</p>
          <p className="text-white font-bold text-lg">${totalSpent.toFixed(2)}</p>
        </div>
      </div>

      {/* ── Order cards ─────────────────────────────────────────────────── */}
      {orders.map((order, index) => (
        <OrderCard key={order.orderNumber} order={order} index={index} />
      ))}
    </div>
  );
};

export default PurchaseHistoryList;

