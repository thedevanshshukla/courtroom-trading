# Courtroom Trading - UI Setup Guide

## Features

✨ **Attractive Home Page** - Beautiful landing page with feature highlights
🔐 **Google OAuth Authentication** - Secure login with Google
📊 **Real Data Dashboard** - Live charts and market analysis
💡 **AI-Powered Verdicts** - Bull vs Bear arguments with reasoning
🎯 **Agent Details Toggle** - Show/hide agent reasoning with one click
📈 **Real-time Graphs** - Price, RSI, Moving Averages, Volume analysis
📝 **Analysis History** - Track last 10 analyses with outcome tracking
⚖️ **Disclaimers** - Clear warnings about agent limitations
👤 **User Profile** - Display logged-in user info
🌙 **Dark/Light Themes** - Switch between Aurora Day and Midnight Lagoon

## Setup Instructions

### 1. Frontend Configuration

```bash
cd frontend
cp config.example.js config.js
```

Edit `config.js` and set:
```javascript
window.COURTROOM_CONFIG = {
  API_BASE_URL: "http://127.0.0.1:8000",  // Your backend URL
  GOOGLE_CLIENT_ID: "YOUR_GOOGLE_CLIENT_ID",  // From Google Cloud Console
  DEFAULT_THEME: "aurora-day"
};
```

### 2. Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable Google+ API
4. Create OAuth 2.0 Client ID (Web Application):
   - Add Authorized JavaScript Origins:
     - `http://127.0.0.1:3000`
     - `http://localhost:3000`
     - Your production domain
   - Add Authorized Redirect URIs:
     - `http://127.0.0.1:3000`
     - Your production domain
5. Copy the Client ID to `config.js` and `.env`

### 3. Backend Configuration

Update `.env` with your Google Client ID:
```
GOOGLE_CLIENT_ID=YOUR_GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET=YOUR_GOOGLE_CLIENT_SECRET
AUTH_MODE=google
```

Or for demo mode (no OAuth):
```
AUTH_MODE=demo
```

### 4. Environment Variables

```env
# Frontend
FRONTEND_ORIGIN=http://127.0.0.1:3000

# Backend
API_BASE_URL=http://127.0.0.1:8000
GOOGLE_CLIENT_ID=your-client-id
JWT_SECRET=change-this-to-something-secure
USE_MONGODB=true
MONGODB_URI=mongodb://127.0.0.1:27017
```

### 5. Run the Application

#### Backend
```bash
cd backend
python -m pip install -r requirements.txt
python app.py
# Server runs on http://127.0.0.1:8000
```

#### Frontend
```bash
cd frontend
python -m http.server 3000
# Frontend runs on http://127.0.0.1:3000
```

Or use any HTTP server (Node http-server, Live Server VSCode extension, etc.)

## UI Overview

### Home Page
- Attractive hero section with feature highlights
- Call-to-action button to sign in
- Feature cards explaining the platform
- Disclaimer about agent limitations
- Made by Devansh footer

### Auth Page
- Google OAuth sign-in button
- Demo mode login option
- Clear instructions
- Responsive design

### Dashboard
- **Left Sidebar**: Market input form with all technical indicators
- **Main Area**:
  - Verdict & Confidence display with reasoning
  - 4 Real-time Charts (Price, RSI, MA, Volume)
  - Bull vs Bear arguments (up to 10 each)
  - Agent Details section (collapsible)
  - Recent Analysis history (last 10)

### Charts
- **Price Movement**: Line chart showing price trends
- **RSI Indicator**: RSI values over time
- **Moving Averages**: MA20 and MA50 comparison
- **Volume Analysis**: Volume bar chart

### Arguments Display
- Each argument shows: Claim, Evidence, Rule Used, Strength
- Bull and Bear arguments side by side
- Color-coded for easy differentiation
- Up to 10 arguments each

### Agent Details Section
- Collapsible section with "Show Details" button
- Full JSON payload display
- Copy to clipboard functionality
- Syntax-highlighted code block

### History & Outcomes
- Shows last 10 analyses
- Verdict, Price, RSI, Confidence displayed
- Mark as Profit/Loss/Break-Even
- Timestamp for each analysis

## Styling

The UI uses two beautiful themes:
- **Aurora Day**: Warm colors with peach, pink, and teal accents
- **Midnight Lagoon**: Cool blue/teal dark theme

Colors adapt throughout the interface for consistency.

## Responsive Design

- Desktop: Full dashboard with sidebar and charts
- Tablet: Sidebar moves above main content
- Mobile: Single column layout, collapsible sections

## API Integration

The UI connects to these backend endpoints:

```
GET  /api/config              - Get backend configuration
GET  /api/health              - Health check
POST /api/auth/google         - Google OAuth login
POST /api/auth/demo           - Demo login
GET  /api/auth/me             - Get current user
POST /api/auth/logout         - Logout
POST /api/decision            - Run market analysis
POST /api/outcomes            - Update analysis outcome
GET  /api/history             - Get analysis history
```

## Disclaimers

The following disclaimers are prominently displayed:
- ⚠️ "Agents can make mistakes"
- 📋 "Not SEBI registered" (or equivalent for your jurisdiction)
- 📚 "For educational purposes only"
- "Made with ❤️ by Devansh"

## Browser Support

- Chrome/Chromium (recommended)
- Firefox
- Safari
- Edge

Requires JavaScript enabled and ES6 support.

## Troubleshooting

### Google OAuth not working
- Check GOOGLE_CLIENT_ID in config.js
- Verify authorized origins in Google Cloud Console
- Check browser console for CORS errors

### Backend connection issues
- Verify API_BASE_URL in config.js
- Check if backend server is running
- Check CORS settings in backend

### Charts not rendering
- Ensure Chart.js library loaded (check network tab)
- Check browser console for errors
- Verify canvas elements exist in DOM

## Future Enhancements

- Real market data integration (via API)
- Portfolio tracking
- Custom indicators
- Export analysis reports
- Mobile app version
- Real-time notifications
- Advanced charting library
