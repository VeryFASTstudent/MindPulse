import 'dart:convert';

import 'package:http/http.dart' as http;

import '../core/constants.dart';
import '../models/consent_model.dart';
import '../services/api_exception.dart';
import 'token_storage_service.dart';

class ConsentService {
  final TokenStorageService _tokenStorage = TokenStorageService();

  Future<ConsentModel> getMine() async {
    final response = await http.get(
      Uri.parse(ApiConstants.myConsent),
      headers: await _authHeaders(),
    );
    return _parseResponse(response);
  }

  Future<ConsentModel> updateMine(ConsentModel consent) async {
    final response = await http.put(
      Uri.parse(ApiConstants.myConsent),
      headers: await _authHeaders(),
      body: jsonEncode(consent.toJson()),
    );
    return _parseResponse(response);
  }

  Future<Map<String, String>> _authHeaders() async {
    final token = await _tokenStorage.getAccessToken();
    return {
      'Content-Type': 'application/json',
      if (token != null) 'Authorization': 'Bearer $token',
    };
  }

  ConsentModel _parseResponse(http.Response response) {
    if (response.statusCode != 200) {
      String message = 'Could not save your privacy settings.';
      try {
        message = jsonDecode(response.body)['detail']?.toString() ?? message;
      } catch (_) {}
      throw ApiException(response.statusCode, message);
    }
    return ConsentModel.fromJson(jsonDecode(response.body));
  }
}
