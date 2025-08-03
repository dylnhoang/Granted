import React, { createContext, useContext, useEffect, useState } from 'react';
import { supabase } from '../supabaseClient';

const AuthContext = createContext({});

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [profile, setProfile] = useState(null);

  useEffect(() => {
    // Get initial session
    const getInitialSession = async () => {
      const { data: { session } } = await supabase.auth.getSession();
      setUser(session?.user ?? null);
      setLoading(false);
    };

    getInitialSession();

    // Listen for auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        setUser(session?.user ?? null);
        setLoading(false);
      }
    );

    return () => subscription.unsubscribe();
  }, []);

  // Fetch user profile when user changes
  useEffect(() => {
    const fetchProfile = async () => {
      if (user) {
        try {
          const { data, error } = await supabase
            .from('profiles')
            .select('*')
            .eq('id', user.id)
            .single();

          if (error) {
            console.error('Error fetching profile:', error);
          } else {
            setProfile(data);
          }
        } catch (error) {
          console.error('Error fetching profile:', error);
        }
      } else {
        setProfile(null);
      }
    };

    fetchProfile();
  }, [user]);

  const signOut = async () => {
    try {
      const { error } = await supabase.auth.signOut();
      if (error) throw error;
    } catch (error) {
      console.error('Error signing out:', error);
    }
  };

  const updateProfile = async (updates) => {
    if (!user) return;

    try {
      console.log('AuthContext: Updating profile with:', updates);
      
      // First, try to update the existing profile
      let { data, error } = await supabase
        .from('profiles')
        .update(updates)
        .eq('id', user.id)
        .select()
        .single();

      // If no rows were updated, the profile doesn't exist, so create it
      if (error && error.code === 'PGRST116') {
        console.log('AuthContext: Profile not found, creating new one');
        const { data: newData, error: insertError } = await supabase
          .from('profiles')
          .insert([{ id: user.id, ...updates }])
          .select()
          .single();

        if (insertError) throw insertError;
        console.log('AuthContext: New profile created:', newData);
        setProfile(newData);
        return newData;
      }

      if (error) throw error;
      console.log('AuthContext: Profile updated successfully:', data);
      setProfile(data);
      return data;
    } catch (error) {
      console.error('Error updating profile:', error);
      throw error;
    }
  };

  const value = {
    user,
    profile,
    loading,
    signOut,
    updateProfile,
    isAuthenticated: !!user,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}; 