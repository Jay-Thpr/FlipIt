import AsyncStorage from '@react-native-async-storage/async-storage';
import { createClient } from '@supabase/supabase-js';
import { Database } from './types';

const SUPABASE_URL = 'https://fmcwulonjlmwffpkxekl.supabase.co';
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZtY3d1bG9uamxtd2ZmcGt4ZWtsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzUzMzM5MjgsImV4cCI6MjA5MDkwOTkyOH0.4fB3jwHNNRJiju5sUFJdnMNM0X30w4opgxUHICD7r_Y';

export const supabase = createClient<Database>(SUPABASE_URL, SUPABASE_ANON_KEY, {
  auth: {
    storage: AsyncStorage,
    autoRefreshToken: true,
    persistSession: true,
    detectSessionInUrl: false,
  },
});
