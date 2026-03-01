import React from 'react';
import { Mail, Phone, Shield, Sparkles } from 'lucide-react';

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
 * Props:
 *   userInfo        — structured object { firstName, lastName, email, phone }
 *                     sent directly from the backend (preferred)
 *   messageContent  — raw LLM message string (fallback when userInfo is null)
 */
const UserInfoCard = ({ userInfo, messageContent }) => {
  // Prefer structured data; fall back to parsing the LLM text
  let name, email, phone;
  if (userInfo) {
    name  = [userInfo.firstName, userInfo.lastName].filter(Boolean).join(' ') || null;
    email = userInfo.email  || null;
    phone = userInfo.phone  || null;
  } else {
    const parsed = parseUserInfoText(messageContent);
    name  = parsed.name;
    email = parsed.email;
    phone = parsed.phone;
  }

  const initial = name ? name.charAt(0).toUpperCase() : '?';

  return (
    <div className="mt-3 max-w-sm">
      <div className="rounded-2xl overflow-hidden shadow-md border border-indigo-100">

        {/* Gradient header */}
        <div className="bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 px-6 py-5 flex items-center gap-4">
          <div className="w-14 h-14 rounded-full bg-white/30 backdrop-blur-sm flex items-center justify-center text-white text-2xl font-bold shadow-inner flex-shrink-0">
            {initial}
          </div>
          <div>
            <p className="text-white/80 text-xs font-medium uppercase tracking-widest mb-0.5">
              Account Profile
            </p>
            <h3 className="text-white text-lg font-bold leading-tight">
              {name || 'Unknown User'}
            </h3>
          </div>
          <Sparkles className="w-5 h-5 text-white/40 ml-auto flex-shrink-0" />
        </div>

        {/* Info rows */}
        <div className="bg-white divide-y divide-gray-100">
          <div className="flex items-center gap-3 px-5 py-3.5">
            <div className="w-8 h-8 rounded-full bg-indigo-50 flex items-center justify-center flex-shrink-0">
              <Mail className="w-4 h-4 text-indigo-500" />
            </div>
            <div className="min-w-0">
              <p className="text-xs text-gray-400 font-medium">Email Address</p>
              <p className="text-sm font-semibold text-gray-800 truncate">
                {email || <span className="text-gray-400 font-normal italic">Not provided</span>}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3 px-5 py-3.5">
            <div className="w-8 h-8 rounded-full bg-purple-50 flex items-center justify-center flex-shrink-0">
              <Phone className="w-4 h-4 text-purple-500" />
            </div>
            <div className="min-w-0">
              <p className="text-xs text-gray-400 font-medium">Phone Number</p>
              <p className="text-sm font-semibold text-gray-800">
                {phone || <span className="text-gray-400 font-normal italic">Not provided</span>}
              </p>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="bg-indigo-50 px-5 py-2.5 flex items-center gap-2">
          <Shield className="w-3.5 h-3.5 text-indigo-400" />
          <p className="text-xs text-indigo-400 font-medium">Your information is secure</p>
        </div>
      </div>
    </div>
  );
};

export default UserInfoCard;

