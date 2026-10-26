# Pitou Lock

A cross-platform Expo/React Native starter for an **in-app lock screen** with a Khmer interface. The initial unlock password is `Pitou007`, as requested. The password can be changed from the unlocked screen.

## Important limitation

Pitou Lock protects access to this app's own screen only. A normal app cannot lock the entire Android or iOS device, survive a factory reset, prevent the owner from uninstalling it, or guarantee that nobody can bypass it. Do not rely on this prototype to protect the whole phone. For device-wide anti-theft protection, use Android Find My Device / Factory Reset Protection, Apple Find My / Activation Lock, or an authorized Android Enterprise/Apple MDM enrollment.

The first-run password is included in the app source to meet the requested prototype behavior. Anyone with access to the source or a modified app build can discover or bypass it. Change it after first launch; do not use this prototype to protect sensitive data. SecureStore protects the locally stored value at rest, but does not make a hard-coded first-run password secret.

## Run locally

1. Install Node.js and Expo Go on a development phone, or configure Android Studio / Xcode for a simulator.
2. In this folder run:

   ```sh
   npm install
   npx expo start
   ```

3. Scan the QR code with Expo Go, or press `a` for Android / `i` for iOS in the Expo terminal.

Native builds may require the current Expo-compatible Android SDK / Xcode toolchain. This workspace does not include Java or the Android SDK, so APK compilation must run on a build runner. The GitHub Actions workflow at `.github/workflows/build-android-apk.yml` builds an installable **debug APK** on pushes to this branch (and can also be started manually from the repository's Actions tab). Download `pitou-lock-android-debug-apk` from the completed workflow run's Artifacts section. This is a debug/test build, not a Play Store release.

## Included prototype features

- One shared React Native codebase for Android and iOS.
- Khmer-language lock and unlocked screens.
- Initial passcode `Pitou007` stored via Expo SecureStore on first launch.
- Relocks the app when it goes into the background.
- Five failed attempts trigger a 30-second cooldown.
- Change-password screen (minimum 8 characters).
