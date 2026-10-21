import 'dart:convert';

import 'package:http/http.dart' as http;

import '../core/constants.dart';
import 'api_exception.dart';
import 'token_storage_service.dart';

/// Authenticated requests for dashboard and trend data.
class AuthenticatedClient {
  final TokenStorageService _tokenStorage = TokenStorageService();

  Future<http.Response> get(Uri uri) async {
    var response = await _send(uri);
    if (response.statusCode == 401) {
      if (await _refresh()) {
        response = await _send(uri);
      } else {
        throw ApiException(401, 'Your session expired. Please log in again.');
      }
    }
    if (response.statusCode == 401) {
      await _tokenStorage.clear();
      throw ApiException(401, 'Your session expired. Please log in again.');
    }
    return response;
  }

  Future<http.Response> _send(Uri uri) async {
    final token = await _tokenStorage.getAccessToken();
    return http.get(
      uri,
      headers: {if (token != null) 'Authorization': 'Bearer $token'},
    );
  }

  Future<bool> _refresh() async {
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
    final data = jsonDecode(response.body) as Map<String, dynamic>;
    await _tokenStorage.saveTokens(
      accessToken: data['access_token'] as String,
      refreshToken: data['refresh_token'] as String,
    );
    return true;
  }
}