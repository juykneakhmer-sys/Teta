import { StatusBar } from 'expo-status-bar';
import * as SecureStore from 'expo-secure-store';
import React, { useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  AppState,
  AppStateStatus,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';

const PASSWORD_KEY = 'pitou_lock_password_v1';
const ATTEMPTS_KEY = 'pitou_lock_failed_attempts_v1';
const LOCK_UNTIL_KEY = 'pitou_lock_until_v1';
const FIRST_RUN_PASSWORD = 'Pitou007';
const MAX_ATTEMPTS = 5;
const LOCKOUT_MS = 30_000;

export default function App() {
  const [ready, setReady] = useState(false);
  const [unlocked, setUnlocked] = useState(false);
  const [password, setPassword] = useState('');
  const [savedPassword, setSavedPassword] = useState(FIRST_RUN_PASSWORD);
  const [attempts, setAttempts] = useState(0);
  const [lockUntil, setLockUntil] = useState(0);
  const [message, setMessage] = useState('');
  const [changingPassword, setChangingPassword] = useState(false);
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [secondsLeft, setSecondsLeft] = useState(0);
  const appState = useRef(AppState.currentState);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        let storedPassword = await SecureStore.getItemAsync(PASSWORD_KEY);
        if (!storedPassword) {
          storedPassword = FIRST_RUN_PASSWORD;
          await SecureStore.setItemAsync(PASSWORD_KEY, storedPassword);
        }
        const storedAttempts = Number((await SecureStore.getItemAsync(ATTEMPTS_KEY)) ?? '0');
        const storedLockUntil = Number((await SecureStore.getItemAsync(LOCK_UNTIL_KEY)) ?? '0');
        if (mounted) {
          setSavedPassword(storedPassword);
          setAttempts(Number.isFinite(storedAttempts) ? storedAttempts : 0);
          setLockUntil(Number.isFinite(storedLockUntil) ? storedLockUntil : 0);
          setReady(true);
        }
      } catch {
        if (mounted) {
          setMessage('មិនអាចបើក Secure Storage បានទេ។ សូមបិទហើយបើកកម្មវិធីម្ដងទៀត។');
          setReady(true);
        }
      }
    })();
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    const subscription = AppState.addEventListener('change', (nextState: AppStateStatus) => {
      if (appState.current === 'active' && nextState !== 'active') {
        setUnlocked(false);
        setChangingPassword(false);
        setPassword('');
      }
      appState.current = nextState;
    });
    return () => subscription.remove();
  }, []);

  useEffect(() => {
    if (!lockUntil || lockUntil <= Date.now()) {
      setSecondsLeft(0);
      return;
    }
    const update = () => setSecondsLeft(Math.max(0, Math.ceil((lockUntil - Date.now()) / 1000)));
    update();
    const timer = setInterval(update, 500);
    return () => clearInterval(timer);
  }, [lockUntil]);

  const submitPassword = async () => {
    if (secondsLeft > 0) return;
    setMessage('');
    if (password === savedPassword) {
      setUnlocked(true);
      setPassword('');
      setAttempts(0);
      setLockUntil(0);
      await SecureStore.setItemAsync(ATTEMPTS_KEY, '0');
      await SecureStore.setItemAsync(LOCK_UNTIL_KEY, '0');
      return;
    }

    const nextAttempts = attempts + 1;
    setAttempts(nextAttempts);
    setPassword('');
    if (nextAttempts >= MAX_ATTEMPTS) {
      const until = Date.now() + LOCKOUT_MS;
      setLockUntil(until);
      setAttempts(0);
      await SecureStore.setItemAsync(ATTEMPTS_KEY, '0');
      await SecureStore.setItemAsync(LOCK_UNTIL_KEY, String(until));
      setMessage('បញ្ចូលខុសច្រើនដង។ សូមរង់ចាំ ៣០ វិនាទី។');
    } else {
      await SecureStore.setItemAsync(ATTEMPTS_KEY, String(nextAttempts));
      setMessage(`ពាក្យសម្ងាត់មិនត្រឹមត្រូវ។ នៅសល់ ${MAX_ATTEMPTS - nextAttempts} ដង។`);
    }
  };

  const saveNewPassword = async () => {
    setMessage('');
    if (currentPassword !== savedPassword) {
      setMessage('ពាក្យសម្ងាត់បច្ចុប្បន្នមិនត្រឹមត្រូវទេ។');
      return;
    }
    if (newPassword.trim().length < 8) {
      setMessage('ពាក្យសម្ងាត់ថ្មីត្រូវមានយ៉ាងតិច ៨ តួអក្សរ។');
      return;
    }
    if (newPassword !== confirmPassword) {
      setMessage('ពាក្យសម្ងាត់ថ្មីទាំងពីរមិនដូចគ្នាទេ។');
      return;
    }
    try {
      await SecureStore.setItemAsync(PASSWORD_KEY, newPassword);
      setSavedPassword(newPassword);
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      setChangingPassword(false);
      setMessage('បានប្ដូរពាក្យសម្ងាត់ដោយជោគជ័យ។');
    } catch {
      setMessage('មិនអាចរក្សាទុកពាក្យសម្ងាត់បានទេ។');
    }
  };

  if (!ready) {
    return (
      <SafeAreaView style={styles.safeArea}>
        <StatusBar style="light" />
        <View style={styles.loading}><ActivityIndicator size="large" color="#68e0c0" /></View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safeArea}>
      <StatusBar style="light" />
      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      >
        <ScrollView contentContainerStyle={styles.scrollContent} keyboardShouldPersistTaps="handled">
          <View style={styles.header}>
            <View style={styles.logo}><Text style={styles.logoGlyph}>P</Text></View>
            <Text style={styles.brand}>PITOU<Text style={styles.brandAccent}> LOCK</Text></Text>
            <Text style={styles.tagline}>សុវត្ថិភាពសម្រាប់កម្មវិធីរបស់អ្នក</Text>
          </View>

          <View style={styles.card}>
            {!unlocked ? (
              <>
                <View style={styles.lockIcon}><Text style={styles.lockGlyph}>◆</Text></View>
                <Text style={styles.title}>កម្មវិធីត្រូវបានចាក់សោ</Text>
                <Text style={styles.subtitle}>បញ្ចូលពាក្យសម្ងាត់ ដើម្បីបន្ត</Text>
                <TextInput
                  value={password}
                  onChangeText={(value) => { setPassword(value); setMessage(''); }}
                  onSubmitEditing={submitPassword}
                  placeholder="ពាក្យសម្ងាត់"
                  placeholderTextColor="#718096"
                  secureTextEntry
                  autoCapitalize="none"
                  autoCorrect={false}
                  returnKeyType="go"
                  editable={secondsLeft === 0}
                  style={styles.input}
                  accessibilityLabel="ពាក្យសម្ងាត់ដោះសោ"
                />
                {secondsLeft > 0 ? (
                  <Text style={styles.warning}>សូមរង់ចាំ {secondsLeft} វិនាទី មុនសាកល្បងម្ដងទៀត</Text>
                ) : null}
                {message ? <Text style={styles.error}>{message}</Text> : null}
                <Pressable
                  onPress={submitPassword}
                  disabled={!password || secondsLeft > 0}
                  style={({ pressed }) => [styles.primaryButton, (!password || secondsLeft > 0) && styles.disabledButton, pressed && styles.pressed]}
                >
                  <Text style={styles.primaryButtonText}>ដោះសោ</Text>
                  <Text style={styles.buttonArrow}>→</Text>
                </Pressable>
                <Text style={styles.protectedHint}>🔒  ពាក្យសម្ងាត់រក្សាទុកក្នុង Secure Storage របស់ឧបករណ៍</Text>
              </>
            ) : changingPassword ? (
              <>
                <Text style={styles.title}>ប្ដូរពាក្យសម្ងាត់</Text>
                <Text style={styles.subtitle}>ជ្រើសរើសពាក្យសម្ងាត់ថ្មីដែលអ្នកអាចចងចាំបាន</Text>
                <TextInput value={currentPassword} onChangeText={setCurrentPassword} placeholder="ពាក្យសម្ងាត់បច្ចុប្បន្ន" placeholderTextColor="#718096" secureTextEntry autoCapitalize="none" style={styles.input} />
                <TextInput value={newPassword} onChangeText={setNewPassword} placeholder="ពាក្យសម្ងាត់ថ្មី (យ៉ាងតិច ៨ តួ)" placeholderTextColor="#718096" secureTextEntry autoCapitalize="none" style={styles.input} />
                <TextInput value={confirmPassword} onChangeText={setConfirmPassword} placeholder="បញ្ជាក់ពាក្យសម្ងាត់ថ្មី" placeholderTextColor="#718096" secureTextEntry autoCapitalize="none" style={styles.input} />
                {message ? <Text style={styles.error}>{message}</Text> : null}
                <Pressable onPress={saveNewPassword} style={({ pressed }) => [styles.primaryButton, pressed && styles.pressed]}>
                  <Text style={styles.primaryButtonText}>រក្សាទុកពាក្យសម្ងាត់ថ្មី</Text>
                  <Text style={styles.buttonArrow}>→</Text>
                </Pressable>
                <Pressable onPress={() => { setChangingPassword(false); setMessage(''); }} style={styles.secondaryButton}>
                  <Text style={styles.secondaryButtonText}>ត្រឡប់ក្រោយ</Text>
                </Pressable>
              </>
            ) : (
              <>
                <View style={[styles.lockIcon, styles.successIcon]}><Text style={styles.successGlyph}>✓</Text></View>
                <Text style={styles.title}>បានដោះសោហើយ</Text>
                <Text style={styles.subtitle}>Pitou Lock កំពុងដំណើរការលើឧបករណ៍នេះ</Text>
                <View style={styles.noticeBox}>
                  <Text style={styles.noticeTitle}>ចំណាំអំពីការការពារ</Text>
                  <Text style={styles.noticeText}>កម្មវិធីនេះចាក់សោតែផ្ទាំងកម្មវិធី Pitou Lock ប៉ុណ្ណោះ។ វាមិនអាចចាក់សោប្រព័ន្ធទូរសព្ទទាំងមូលបានទេ។</Text>
                </View>
                {message ? <Text style={styles.successMessage}>{message}</Text> : null}
                <Pressable onPress={() => { setChangingPassword(true); setMessage(''); }} style={styles.secondaryButton}>
                  <Text style={styles.secondaryButtonText}>ប្ដូរពាក្យសម្ងាត់</Text>
                </Pressable>
                <Pressable onPress={() => { setUnlocked(false); setMessage(''); }} style={({ pressed }) => [styles.primaryButton, pressed && styles.pressed]}>
                  <Text style={styles.primaryButtonText}>ចាក់សោកម្មវិធី</Text>
                  <Text style={styles.buttonArrow}>↗</Text>
                </Pressable>
              </>
            )}
          </View>

          <Text style={styles.footer}>PITOU LOCK  ·  ANDROID & iOS</Text>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: '#07111f' },
  flex: { flex: 1 },
  scrollContent: { flexGrow: 1, justifyContent: 'center', paddingHorizontal: 24, paddingVertical: 34 },
  loading: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  header: { alignItems: 'center', marginBottom: 30 },
  logo: { width: 58, height: 58, borderRadius: 19, backgroundColor: '#102b38', borderWidth: 1, borderColor: '#275c60', alignItems: 'center', justifyContent: 'center', marginBottom: 14 },
  logoGlyph: { color: '#68e0c0', fontSize: 31, fontWeight: '800' },
  brand: { color: '#f4f7fb', fontSize: 19, letterSpacing: 4, fontWeight: '800' },
  brandAccent: { color: '#68e0c0' },
  tagline: { color: '#90a0b5', fontSize: 13, marginTop: 8 },
  card: { width: '100%', maxWidth: 440, alignSelf: 'center', borderRadius: 26, padding: 24, backgroundColor: '#101c2b', borderWidth: 1, borderColor: '#203247' },
  lockIcon: { alignSelf: 'center', width: 62, height: 62, borderRadius: 22, backgroundColor: '#182d3e', alignItems: 'center', justifyContent: 'center', marginBottom: 19 },
  lockGlyph: { color: '#68e0c0', fontSize: 25 },
  successIcon: { backgroundColor: '#10332f' },
  successGlyph: { color: '#68e0c0', fontSize: 31, fontWeight: '700' },
  title: { color: '#f4f7fb', fontSize: 22, textAlign: 'center', fontWeight: '700', marginBottom: 8 },
  subtitle: { color: '#90a0b5', fontSize: 14, lineHeight: 22, textAlign: 'center', marginBottom: 23 },
  input: { height: 54, borderRadius: 14, borderWidth: 1, borderColor: '#2c4057', backgroundColor: '#0b1624', color: '#f4f7fb', paddingHorizontal: 16, marginBottom: 12, fontSize: 16, textAlign: 'center' },
  primaryButton: { minHeight: 54, borderRadius: 14, backgroundColor: '#68e0c0', alignItems: 'center', justifyContent: 'center', flexDirection: 'row', marginTop: 10, paddingHorizontal: 18 },
  disabledButton: { opacity: 0.45 },
  pressed: { opacity: 0.8, transform: [{ scale: 0.99 }] },
  primaryButtonText: { color: '#06211f', fontWeight: '800', fontSize: 16 },
  buttonArrow: { position: 'absolute', right: 18, color: '#06211f', fontSize: 20, fontWeight: '700' },
  protectedHint: { color: '#718096', fontSize: 11, textAlign: 'center', marginTop: 17, lineHeight: 18 },
  error: { color: '#ff8f8f', fontSize: 13, textAlign: 'center', marginBottom: 6 },
  warning: { color: '#f3c97a', fontSize: 13, textAlign: 'center', marginBottom: 8 },
  secondaryButton: { minHeight: 48, justifyContent: 'center', alignItems: 'center', marginTop: 8 },
  secondaryButtonText: { color: '#a8bad0', fontSize: 14, fontWeight: '600' },
  noticeBox: { backgroundColor: '#0b1624', borderRadius: 14, borderWidth: 1, borderColor: '#26394e', padding: 15, marginBottom: 14 },
  noticeTitle: { color: '#f3c97a', fontSize: 13, fontWeight: '700', marginBottom: 6 },
  noticeText: { color: '#a8bad0', fontSize: 13, lineHeight: 20 },
  successMessage: { color: '#68e0c0', textAlign: 'center', fontSize: 13, marginBottom: 8 },
  footer: { color: '#54657a', textAlign: 'center', fontSize: 10, letterSpacing: 2, marginTop: 26 },
});
