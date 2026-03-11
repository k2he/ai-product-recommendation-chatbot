import React from 'react';
import { Mail, Phone, Shield } from 'lucide-react';

/**
 * Fallback: parse the plain-text user info message from the LLM.
 * Used only when the structured userInfo prop is not provided.
 *
 * Expected format from user_info_tool.py:
 *   "User Account Information:\nName: Kai He\nEmail: kai@…\nPhone: +1…"
 */
const parseUserInfoText = (text) => {
  if (!text) return { name: null, email: null, phone: null };
  const get = (label) => {
    const match = text.match(new RegExp(`${label}:\\s*(.+)`));
    return match ? match[1].trim() : null;
  };
  return { name: get('Name'), email: get('Email'), phone: get('Phone') };
};

/**
 * UserInfoCard
 *
 * Matches the ProductCard design language:
 *   bg-white · rounded-xl · shadow-md · hover:shadow-lg · blue-600 accent
 *
 * Props:
 *   userInfo        — { firstName, lastName, email, phone } from backend (preferred)
 *   messageContent  — raw LLM text fallback
 */
const UserInfoCard = ({ userInfo, messageContent }) => {
  let name, email, phone;
  if (userInfo) {
    name  = [userInfo.firstName, userInfo.lastName].filter(Boolean).join(' ') || null;
    email = userInfo.email || null;
    phone = userInfo.phone || null;
  } else {
    const parsed = parseUserInfoText(messageContent);
    name  = parsed.name;
    email = parsed.email;
    phone = parsed.phone;
  }

  const initial = name ? name.charAt(0).toUpperCase() : '?';

  return (
    <div className="bg-white rounded-xl shadow-md overflow-hidden hover:shadow-lg transition-shadow duration-200 flex flex-col max-w-xs">

      {/* ── Card body ──────────────────────────────────────────────────── */}
      <div className="p-4 flex flex-col flex-1">

        {/* "Account" badge — mirrors the "On Sale" badge position */}
        <span className="self-start mb-2 px-2 py-0.5 text-xs font-semibold bg-blue-100 text-blue-600 rounded-full uppercase tracking-wide">
          My Account
        </span>

        {/* Full name — mirrors product name */}
        <h3 className="text-sm font-semibold text-gray-900 mb-3 leading-snug">
          {name || 'Unknown User'}
        </h3>

        {/* Email row — mirrors category row */}
        <div className="flex items-center gap-1.5 mb-2">
          <Mail className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
          <span className="text-xs text-gray-500 truncate">
            {email || <span className="italic text-gray-400">No email</span>}
          </span>
        </div>

        {/* Phone row */}
        <div className="flex items-center gap-1.5 mb-4">
          <Phone className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
          <span className="text-xs text-gray-500">
            {phone || <span className="italic text-gray-400">No phone</span>}
          </span>
        </div>

        {/* Security note — mirrors "Regular price" label */}
        <div className="flex items-center gap-1 mt-auto">
          <Shield className="w-3 h-3 text-gray-400" />
          <p className="text-xs text-gray-400">Your information is secure</p>
        </div>

      </div>
    </div>
  );
};

export default UserInfoCard;
