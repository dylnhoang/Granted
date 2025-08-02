import React from 'react';
import { useAuth } from '../contexts/AuthContext';
import { CheckCircleIcon } from '@heroicons/react/24/outline';

const WelcomeBanner = () => {
  const { user, profile } = useAuth();

  if (!user) return null;

  const isNewUser = !profile?.full_name;
  const profileCompletion = profile ? 
    Math.round(([
      profile.full_name,
      profile.gpa,
      profile.major,
      profile.state,
      profile.interests?.length > 0,
      profile.demographic_tags?.length > 0
    ].filter(Boolean).length / 6) * 100) : 0;

  return (
    <div className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white p-6 mb-6">
      <div className="max-w-7xl mx-auto">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold mb-2">
              Welcome{profile?.full_name ? `, ${profile.full_name.split(' ')[0]}` : ''}!
            </h1>
            <p className="text-blue-100">
              {isNewUser 
                ? "Let's get started by completing your profile to find the best scholarships for you."
                : `Your profile is ${profileCompletion}% complete. Keep it updated for better matches!`
              }
            </p>
          </div>
          {!isNewUser && (
            <div className="flex items-center space-x-2 bg-white/20 rounded-lg px-4 py-2">
              <CheckCircleIcon className="w-5 h-5" />
              <span className="font-medium">{profileCompletion}% Complete</span>
            </div>
          )}
        </div>
        
        {isNewUser && (
          <div className="mt-4">
            <a
              href="/profile"
              className="inline-flex items-center px-4 py-2 bg-white text-blue-600 font-medium rounded-md hover:bg-gray-50 transition-colors"
            >
              Complete Your Profile
            </a>
          </div>
        )}
      </div>
    </div>
  );
};

export default WelcomeBanner; 