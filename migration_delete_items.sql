-- Run this in Supabase SQL Editor
-- Allow users to delete their own items (replaces archive-only approach)
CREATE POLICY "Users can delete own items" ON public.items FOR DELETE USING (auth.uid() = user_id);
