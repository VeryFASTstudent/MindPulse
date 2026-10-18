import 'dart:convert';

import 'package:http/http.dart' as http;

import '../core/constants.dart';
import '../models/risk_status_model.dart';
import 'api_exception.dart';
import 'token_storage_service.dart';

class RiskService {
  final TokenStorageService _tokenStorage = TokenStorageService();

  Future<RiskStatusModel> getStatus() async {
    final token = await _tokenStorage.getAccessToken();
    final response = await http.get(
      Uri.parse(ApiConstants.riskStatus),
      headers: {if (token != null) 'Authorization': 'Bearer $token'},
    );
    if (response.statusCode != 200) {
      String message = 'Could not load your well-being status.';
      try {
        message = jsonDecode(response.body)['detail']?.toString() ?? message;
      } catch (_) {}
      throw ApiException(response.statusCode, message);
    }
    return RiskStatusModel.fromJson(jsonDecode(response.body));
  }
}