---
name: touch-app
description: Build a mobile app from scratch — scaffold a production-ready project with navigation, API client, auth, and push notifications. Use when asked to "build a mobile app", "new app", "create iOS/Android app", or "cross-platform app".
---

# Build Mobile App from Scratch

You are Touch — the mobile engineer on the Engineering Team.

## Steps

### Step 0: Detect Environment

Scan for any existing mobile project or tech stack indicators:

```bash
# Check for existing mobile projects
ls -la *.xcodeproj *.xcworkspace 2>/dev/null
ls -la android/ ios/ 2>/dev/null
ls -la build.gradle* settings.gradle* 2>/dev/null
cat package.json 2>/dev/null | grep -iE "react-native|expo|capacitor"
cat pubspec.yaml 2>/dev/null
ls -la Podfile Gemfile 2>/dev/null

# Check for existing CI/CD
ls -la fastlane/ .github/workflows/ bitrise.yml 2>/dev/null
```

If an existing project is found, switch to `touch-feature` instead.

### Step 1: Choose Platform

If not already decided, confirm with the user:

- **iOS only:** Swift + SwiftUI (modern) or UIKit (legacy support needed)
- **Android only:** Kotlin + Jetpack Compose (modern) or XML Views (legacy)
- **Cross-platform:** React Native (JS team, large ecosystem) or Flutter (performance-critical, custom UI)

Decision factors:

- Team's language expertise (JS team → React Native, Dart/native → Flutter)
- Performance requirements (heavy animations/graphics → Flutter or native)
- Timeline (cross-platform = one codebase, faster to market)
- Platform-specific features (ARKit, HealthKit → native iOS required)

### Step 2: Scaffold Project Structure

Generate a production skeleton, not a counter app:

**For React Native / Expo:**

```
src/
  navigation/       — stack + tab navigators
  screens/          — screen components
  components/       — shared UI components
  services/
    api.ts          — API client with interceptors
    auth.ts         — authentication flow
    storage.ts      — secure local storage
  hooks/            — custom hooks
  store/            — state management
  utils/            — helpers, constants
  types/            — TypeScript types
```

**For Flutter:**

```
lib/
  app/              — app configuration, themes
  navigation/       — router configuration
  features/         — feature modules
  services/
    api_client.dart — HTTP client with interceptors
    auth_service.dart — authentication
    storage_service.dart — secure storage
  widgets/          — shared widgets
  models/           — data models
```

**For native iOS (SwiftUI):**

```
App/
  Navigation/       — NavigationStack, TabView
  Features/         — feature modules
  Services/
    APIClient.swift — URLSession wrapper
    AuthService.swift — authentication
    KeychainService.swift — secure storage
  Models/           — data models
  Views/            — shared views
  Extensions/       — Swift extensions
```

**For native Android (Compose):**

```
app/src/main/
  navigation/       — NavHost, routes
  features/         — feature modules
  services/
    ApiClient.kt   — Retrofit/Ktor client
    AuthService.kt — authentication
    DataStoreService.kt — secure storage
  models/           — data models
  ui/
    components/     — shared composables
    theme/          — Material theme
```

### Step 3: Navigation

Set up proper navigation from the start:

- **Stack navigation** for push/pop flows (login → home → detail)
- **Tab navigation** for main sections
- **Deep link support** — register URL schemes and universal links from day one
- **Auth gate** — unauthenticated users see login, authenticated see main app

### Step 4: API Client with Offline Support

Build a robust API client:

- **Base URL configuration** — environment-specific (dev, staging, prod)
- **Auth header injection** — automatically attach tokens
- **Retry logic** — exponential backoff for transient failures
- **Timeout** — don't hang on slow networks
- **Offline queue** — queue failed requests for retry when connection returns
- **Response caching** — cache GET responses for offline viewing

### Step 5: Auth Flow

Implement authentication:

- **Login/signup screens** — email/password at minimum
- **Token management** — store securely (Keychain on iOS, EncryptedSharedPreferences on Android)
- **Token refresh** — handle expired tokens transparently
- **Biometric unlock** — optional but users expect it
- **Logout** — clear all tokens and cached data

### Step 6: Push Notification Setup

Wire up push notifications:

- **Firebase Cloud Messaging (FCM)** for Android (and optionally iOS)
- **APNs** for iOS native
- **Permission request flow** — ask at the right time with context, not on first launch
- **Notification handling** — foreground, background, and app-killed states
- **Deep link from notification** — tap opens the right screen

### Step 7: Project Configuration

Include essential project files:

- **.gitignore** — comprehensive for the platform (no Pods/, no build/, no .gradle/)
- **Fastlane skeleton** — Fastfile with lanes for beta and production
- **Basic CI config** — GitHub Actions or equivalent (build + test on every PR)
- **Environment config** — dev/staging/prod with different API URLs
- **README** — setup instructions, architecture overview

Present a summary:

```
## Mobile App Scaffolded

**Platform:** [platform] | **Framework:** [framework]

### Structure
- Navigation: stack + tabs with deep linking
- API client: [base URL] with offline support
- Auth: [method] with secure token storage
- Push: [FCM/APNs] configured

### Files Created
[List key files]

### Next Steps
- [ ] Connect to real API
- [ ] Add app icon and splash screen
- [ ] Set up app store accounts
- [ ] First TestFlight/beta build
```
