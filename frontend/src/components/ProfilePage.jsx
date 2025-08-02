import React, { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { useAuth } from '../contexts/AuthContext';
import { 
  UserIcon, 
  AcademicCapIcon, 
  MapPinIcon, 
  TagIcon,
  PencilIcon,
  CheckIcon,
  XMarkIcon,
  PhotoIcon
} from '@heroicons/react/24/outline';

const ProfilePage = () => {
  const { user, profile, updateProfile } = useAuth();
  const [isEditing, setIsEditing] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [profileData, setProfileData] = useState({
    fullName: '',
    email: '',
    gpa: '',
    major: '',
    state: '',
    interests: [],
    demographicTags: [],
    profilePhoto: null
  });

  const { register, handleSubmit, setValue, formState: { errors } } = useForm();

  // Available options
  const states = [
    'Alabama', 'Alaska', 'Arizona', 'Arkansas', 'California', 'Colorado', 'Connecticut',
    'Delaware', 'Florida', 'Georgia', 'Hawaii', 'Idaho', 'Illinois', 'Indiana', 'Iowa',
    'Kansas', 'Kentucky', 'Louisiana', 'Maine', 'Maryland', 'Massachusetts', 'Michigan',
    'Minnesota', 'Mississippi', 'Missouri', 'Montana', 'Nebraska', 'Nevada', 'New Hampshire',
    'New Jersey', 'New Mexico', 'New York', 'North Carolina', 'North Dakota', 'Ohio',
    'Oklahoma', 'Oregon', 'Pennsylvania', 'Rhode Island', 'South Carolina', 'South Dakota',
    'Tennessee', 'Texas', 'Utah', 'Vermont', 'Virginia', 'Washington', 'West Virginia',
    'Wisconsin', 'Wyoming'
  ];

  const interestOptions = [
    'AI & Machine Learning', 'Healthcare', 'Art & Design', 'Engineering', 'Business',
    'Education', 'Environmental Science', 'Computer Science', 'Psychology', 'Biology',
    'Chemistry', 'Physics', 'Mathematics', 'Literature', 'History', 'Political Science',
    'Economics', 'Sociology', 'Anthropology', 'Philosophy', 'Music', 'Theater',
    'Journalism', 'Law', 'Medicine', 'Nursing', 'Public Health', 'Social Work'
  ];

  const demographicOptions = [
    'First-generation college student', 'Low-income background', 'BIPOC', 'LGBTQ+',
    'Veteran', 'International student', 'Transfer student', 'Non-traditional student',
    'Student with disabilities', 'Rural background', 'Urban background'
  ];

  // Mock matched grants data
  const matchedGrants = [
    {
      id: 1,
      title: "Tech Innovation Scholarship",
      amount: "$5,000",
      deadline: "2024-03-15",
      matchScore: 95
    },
    {
      id: 2,
      title: "First-Gen Student Grant",
      amount: "$3,000",
      deadline: "2024-04-01",
      matchScore: 88
    },
    {
      id: 3,
      title: "STEM Excellence Award",
      amount: "$7,500",
      deadline: "2024-03-30",
      matchScore: 82
    }
  ];

  useEffect(() => {
    if (profile) {
      setProfileData({
        fullName: profile.full_name || '',
        email: user?.email || '',
        gpa: profile.gpa || '',
        major: profile.major || '',
        state: profile.state || '',
        interests: profile.interests || [],
        demographicTags: profile.demographic_tags || [],
        profilePhoto: profile.profile_photo
      });

      // Set form values
      setValue('fullName', profile.full_name || '');
      setValue('gpa', profile.gpa || '');
      setValue('major', profile.major || '');
      setValue('state', profile.state || '');
    } else if (user) {
      // Set default values for new users
      setProfileData(prev => ({
        ...prev,
        email: user.email || ''
      }));
    }
  }, [profile, user, setValue]);

  const onSubmit = async (data) => {
    try {
      setIsLoading(true);
      
      if (!user) return;

      const updatedProfile = await updateProfile({
        full_name: data.fullName,
        email: user.email,
        gpa: parseFloat(data.gpa),
        major: data.major,
        state: data.state,
        interests: profileData.interests,
        demographic_tags: profileData.demographicTags,
      });

      if (updatedProfile) {
        setProfileData(prev => ({
          ...prev,
          fullName: data.fullName,
          gpa: data.gpa,
          major: data.major,
          state: data.state
        }));
      }

      setIsEditing(false);
    } catch (error) {
      console.error('Error saving profile:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const toggleInterest = (interest) => {
    setProfileData(prev => ({
      ...prev,
      interests: prev.interests.includes(interest)
        ? prev.interests.filter(i => i !== interest)
        : [...prev.interests, interest]
    }));
  };

  const toggleDemographicTag = (tag) => {
    setProfileData(prev => ({
      ...prev,
      demographicTags: prev.demographicTags.includes(tag)
        ? prev.demographicTags.filter(t => t !== tag)
        : [...prev.demographicTags, tag]
    }));
  };

  const calculateProfileCompletion = () => {
    const fields = [
      profileData.fullName,
      profileData.gpa,
      profileData.major,
      profileData.state,
      profileData.interests.length > 0,
      profileData.demographicTags.length > 0
    ];
    
    const completedFields = fields.filter(Boolean).length;
    return Math.round((completedFields / fields.length) * 100);
  };

  const getInitials = (name) => {
    return name
      .split(' ')
      .map(word => word.charAt(0))
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  if (!user) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Profile</h1>
          <p className="text-gray-600 mt-2">Manage your scholarship profile and preferences</p>
        </div>

        {/* Profile Completion Bar */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-8">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">Profile Completion</h2>
            <span className="text-sm font-medium text-primary">{calculateProfileCompletion()}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div 
              className="bg-primary h-2 rounded-full transition-all duration-300"
              style={{ width: `${calculateProfileCompletion()}%` }}
            ></div>
          </div>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-8">
          {/* Profile Photo Section */}
          <div className="bg-white rounded-lg shadow-sm p-6">
            <div className="flex items-center space-x-6">
              <div className="relative">
                {profileData.profilePhoto ? (
                  <img
                    src={profileData.profilePhoto}
                    alt="Profile"
                    className="w-20 h-20 rounded-full object-cover"
                  />
                ) : (
                  <div className="w-20 h-20 rounded-full bg-primary/10 flex items-center justify-center">
                    {profileData.fullName ? (
                      <span className="text-2xl font-semibold text-primary">
                        {getInitials(profileData.fullName)}
                      </span>
                    ) : (
                      <UserIcon className="w-10 h-10 text-primary" />
                    )}
                  </div>
                )}
                <button
                  type="button"
                  className="absolute -bottom-1 -right-1 bg-primary text-white rounded-full p-1 hover:bg-primary/80 transition-colors"
                >
                  <PhotoIcon className="w-4 h-4" />
                </button>
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900">Profile Photo</h3>
                <p className="text-sm text-gray-600">Upload a photo to personalize your profile</p>
              </div>
            </div>
          </div>

          {/* Personal Information */}
          <div className="bg-white rounded-lg shadow-sm p-6">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center space-x-2">
                <UserIcon className="w-5 h-5 text-primary" />
                <h3 className="text-lg font-semibold text-gray-900">Personal Information</h3>
              </div>
              {!isEditing && (
                <button
                  type="button"
                  onClick={() => setIsEditing(true)}
                  className="flex items-center space-x-2 text-primary hover:text-primary/80 transition-colors"
                >
                  <PencilIcon className="w-4 h-4" />
                  <span>Edit</span>
                </button>
              )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Full Name
                </label>
                {isEditing ? (
                  <input
                    type="text"
                    {...register('fullName', { required: 'Full name is required' })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                    placeholder="Enter your full name"
                  />
                ) : (
                  <p className="text-gray-900">{profileData.fullName || 'Not provided'}</p>
                )}
                {errors.fullName && (
                  <p className="text-red-500 text-sm mt-1">{errors.fullName.message}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Email
                </label>
                <p className="text-gray-900">{profileData.email}</p>
                <p className="text-xs text-gray-500 mt-1">Email cannot be changed</p>
              </div>
            </div>
          </div>

          {/* Academic Information */}
          <div className="bg-white rounded-lg shadow-sm p-6">
            <div className="flex items-center space-x-2 mb-6">
              <AcademicCapIcon className="w-5 h-5 text-primary" />
              <h3 className="text-lg font-semibold text-gray-900">Academic Information</h3>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  GPA
                </label>
                {isEditing ? (
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    max="4"
                    {...register('gpa', { 
                      required: 'GPA is required',
                      min: { value: 0, message: 'GPA must be at least 0' },
                      max: { value: 4, message: 'GPA cannot exceed 4.0' }
                    })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                    placeholder="0.00 - 4.00"
                  />
                ) : (
                  <p className="text-gray-900">{profileData.gpa || 'Not provided'}</p>
                )}
                {errors.gpa && (
                  <p className="text-red-500 text-sm mt-1">{errors.gpa.message}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Major
                </label>
                {isEditing ? (
                  <input
                    type="text"
                    {...register('major', { required: 'Major is required' })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                    placeholder="Enter your major"
                  />
                ) : (
                  <p className="text-gray-900">{profileData.major || 'Not provided'}</p>
                )}
                {errors.major && (
                  <p className="text-red-500 text-sm mt-1">{errors.major.message}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  State
                </label>
                {isEditing ? (
                  <select
                    {...register('state', { required: 'State is required' })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
                  >
                    <option value="">Select a state</option>
                    {states.map(state => (
                      <option key={state} value={state}>{state}</option>
                    ))}
                  </select>
                ) : (
                  <p className="text-gray-900">{profileData.state || 'Not provided'}</p>
                )}
                {errors.state && (
                  <p className="text-red-500 text-sm mt-1">{errors.state.message}</p>
                )}
              </div>
            </div>
          </div>

          {/* Interests */}
          <div className="bg-white rounded-lg shadow-sm p-6">
            <div className="flex items-center space-x-2 mb-6">
              <TagIcon className="w-5 h-5 text-primary" />
              <h3 className="text-lg font-semibold text-gray-900">Interests</h3>
            </div>
            <p className="text-sm text-gray-600 mb-4">Select areas that interest you (this helps us match you with relevant scholarships)</p>
            
            <div className="flex flex-wrap gap-2">
              {interestOptions.map(interest => (
                <button
                  key={interest}
                  type="button"
                  onClick={() => toggleInterest(interest)}
                  className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
                    profileData.interests.includes(interest)
                      ? 'bg-primary text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  {interest}
                </button>
              ))}
            </div>
          </div>

          {/* Demographic Tags */}
          <div className="bg-white rounded-lg shadow-sm p-6">
            <div className="flex items-center space-x-2 mb-6">
              <UserIcon className="w-5 h-5 text-primary" />
              <h3 className="text-lg font-semibold text-gray-900">Demographic Information (Optional)</h3>
            </div>
            <p className="text-sm text-gray-600 mb-4">This information helps us find scholarships that match your background</p>
            
            <div className="flex flex-wrap gap-2">
              {demographicOptions.map(tag => (
                <button
                  key={tag}
                  type="button"
                  onClick={() => toggleDemographicTag(tag)}
                  className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
                    profileData.demographicTags.includes(tag)
                      ? 'bg-blue-100 text-blue-800 border border-blue-200'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  {tag}
                </button>
              ))}
            </div>
          </div>

          {/* Matched Grants */}
          <div className="bg-white rounded-lg shadow-sm p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-6">Recent Matched Grants</h3>
            <div className="space-y-4">
              {matchedGrants.map(grant => (
                <div key={grant.id} className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="font-medium text-gray-900">{grant.title}</h4>
                      <p className="text-sm text-gray-600">{grant.amount} • Due {grant.deadline}</p>
                    </div>
                    <div className="text-right">
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                        {grant.matchScore}% match
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Action Buttons */}
          {isEditing && (
            <div className="flex items-center justify-end space-x-4">
              <button
                type="button"
                onClick={() => setIsEditing(false)}
                className="flex items-center space-x-2 px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
              >
                <XMarkIcon className="w-4 h-4" />
                <span>Cancel</span>
              </button>
              <button
                type="submit"
                disabled={isLoading}
                className="flex items-center space-x-2 px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/80 transition-colors disabled:opacity-50"
              >
                {isLoading ? (
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                ) : (
                  <CheckIcon className="w-4 h-4" />
                )}
                <span>{isLoading ? 'Saving...' : 'Save Changes'}</span>
              </button>
            </div>
          )}
        </form>
      </div>
    </div>
  );
};

export default ProfilePage; 