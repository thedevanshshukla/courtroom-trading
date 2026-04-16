// Configuration template for Courtroom Trading Frontend
// Copy this file to config.js and fill in your values

window.COURTROOM_CONFIG = {
  // Backend API URL - where your Python FastAPI server is running
  API_BASE_URL: "http://127.0.0.1:8000",
  
  // Google OAuth Configuration
  // Get these from: https://console.developers.google.com/
  // 1. Create a project
  // 2. Enable Google+ API
  // 3. Create an OAuth 2.0 Client ID (Web application)
  // 4. Add authorized JavaScript origins: http://127.0.0.1:3000, your-domain.com
  // 5. Add authorized redirect URIs: http://127.0.0.1:3000/auth/callback
  GOOGLE_CLIENT_ID: "YOUR_GOOGLE_CLIENT_ID_HERE",
  
  // Theme preference (aurora-day or midnight-lagoon)
  DEFAULT_THEME: "aurora-day"
};
