// Backend API configuration
// In development, the FastAPI backend runs on localhost:8000
// For device testing, use your machine's local IP address
export const API_BASE_URL = process.env.EXPO_PUBLIC_API_URL || 'http://localhost:8000';
