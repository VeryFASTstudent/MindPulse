import 'dart:convert';

import 'package:http/http.dart' as http;

import '../core/constants.dart';
import '../models/daily_sentiment_model.dart';
import 'api_exception.dart';
import 'token_storage_service.dart';

class SentimentService {
  final TokenStorageService _tokenStorage = TokenStorageService();

  Future<List<DailySentimentModel>> getDailySentiment({int days = 30}) async {
    final token = await _tokenStorage.getAccessToken();
    final response = await http.get(
      Uri.parse('${ApiConstants.dailySentiment}?days=$days'),
      headers: {if (token != null) 'Authorization': '******'},
    );
    if (response.statusCode != 200) {
      throw ApiException(
        response.statusCode,
        _extractDetail(response),
      );
    }
    final data = jsonDecode(response.body) as List<dynamic>;
    return data
        .map((item) =>
            DailySentimentModel.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  String _extractDetail(http.Response response) {
    try {
      return jsonDecode(response.body)['detail']?.toString() ??
          'Could not load sentiment history.';
    } catch (_) {
      return 'Could not load sentiment history.';
    }
  }
}
