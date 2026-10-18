import 'package:flutter/foundation.dart';

/// App-wide constants.
///
/// [apiBaseUrl] is the one thing you WILL need to change per environment:
/// - Android emulator talking to a backend running on your own machine:
///   use 10.0.2.2 instead of localhost (Android emulator's alias for the
///   host machine's localhost).
/// - iOS simulator: localhost works as-is.
/// - Physical device: use your machine's LAN IP (e.g. 192.168.x.x) and make
///   sure your firewall allows the connection.
/// - Once deployed (Phase 15), point this at your Render/Railway URL.
class ApiConstants {
  static const String apiBaseUrl = kIsWeb ? 'http://127.0.0.1:8000' : 'http://10.0.2.2:8000';

  static const String register = '$apiBaseUrl/auth/register';
  static const String login = '$apiBaseUrl/auth/login';
  static const String refresh = '$apiBaseUrl/auth/refresh';
  static const String me = '$apiBaseUrl/auth/me';

  static const String chatMessage = '$apiBaseUrl/chat/message';

  static const String checkin = '$apiBaseUrl/behavior/checkin';
  static const String checkinToday = '$apiBaseUrl/behavior/checkin/today';
  static const String checkinStreak = '$apiBaseUrl/behavior/streak';
  static String checkinHistory(int days) => '$apiBaseUrl/behavior/history?days=$days';
  static const String riskStatus = '$apiBaseUrl/risk/status';
  static const String myConsent = '$apiBaseUrl/consent/me';
}

/// Keys used for secure token storage. Centralized so no other file needs
/// to hardcode the string keys.
class StorageKeys {
  static const String accessToken = 'access_token';
  static const String refreshToken = 'refresh_token';
}
