import 'dart:convert';

import 'package:http/http.dart' as http;

import '../core/constants.dart';
import '../models/user_model.dart';
import 'api_exception.dart';
import 'token_storage_service.dart';

/// Talks to the backend's /auth routes (Phase 2). Deliberately kept
/// separate from other future services (chat_service, behavior_service,
/// etc. in later phases) so each backend module has one matching
/// frontend service file.
class AuthService {
  final TokenStorageService _tokenStorage = TokenStorageService();

  Future<UserModel> register({
    required String email,
    required String password,
    required String fullName,
    required String role,
    String? universityId,
    String? program,
    int? semester,
  }) async {
    final response = await http.post(
      Uri.parse(ApiConstants.register),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'email': email,
        'password': password,
        'full_name': fullName,
        'role': role,
        if (universityId != null) 'university_id': universityId,
        if (program != null) 'program': program,
        if (semester != null) 'semester': semester,
      }),
    );

    if (response.statusCode != 201) {
      throw ApiException(response.statusCode, _extractDetail(response));
    }
    return UserModel.fromJson(jsonDecode(response.body));
  }

  /// Logs in and persists both tokens to secure storage.
  Future<void> login({required String email, required String password}) async {
    final response = await http.post(
      Uri.parse(ApiConstants.login),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'email': email, 'password': password}),
    );

    if (response.statusCode != 200) {
      throw ApiException(response.statusCode, _extractDetail(response));
    }

    final data = jsonDecode(response.body);
    await _tokenStorage.saveTokens(
      accessToken: data['access_token'],
      refreshToken: data['refresh_token'],
    );
  }

  /// Fetches the current user using the stored access token.
  /// Returns null if there's no token or it's invalid/expired -- callers
  /// (SplashScreen, AuthProvider) treat null as "not logged in."
  Future<UserModel?> getCurrentUser() async {
    final accessToken = await _tokenStorage.getAccessToken();
    if (accessToken == null) return null;

    final response = await http.get(
      Uri.parse(ApiConstants.me),
      headers: {'Authorization': 'Bearer $accessToken'},
    );

    if (response.statusCode == 200) {
      return UserModel.fromJson(jsonDecode(response.body));
    }

    if (response.statusCode == 401) {
      // Access token expired -- try refreshing once before giving up.
      final refreshed = await _tryRefresh();
      if (!refreshed) return null;
      return getCurrentUser();
    }

    throw ApiException(response.statusCode, _extractDetail(response));
  }

  Future<bool> _tryRefresh() async {
    final refreshToken = await _tokenStorage.getRefreshToken();
    if (refreshToken == null) return false;

    final response = await http.post(
      Uri.parse(ApiConstants.refresh),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'refresh_token': refreshToken}),
    );

    if (response.statusCode != 200) {
      await _tokenStorage.clear();
      return false;
    }

    final data = jsonDecode(response.body);
    await _tokenStorage.saveTokens(
      accessToken: data['access_token'],
      refreshToken: data['refresh_token'],
    );
    return true;
  }

  Future<void> logout() => _tokenStorage.clear();

  String _extractDetail(http.Response response) {
    try {
      final body = jsonDecode(response.body);
      return body['detail']?.toString() ??
          'Something went wrong. Please try again.';
    } catch (_) {
      return 'Something went wrong. Please try again.';
    }
  }
}
