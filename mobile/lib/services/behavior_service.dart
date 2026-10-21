import 'dart:convert';

import 'package:http/http.dart' as http;

import '../core/constants.dart';
import '../models/checkin_model.dart';
import 'api_exception.dart';
import 'authenticated_client.dart';
import 'token_storage_service.dart';

class BehaviorService {
  final TokenStorageService _tokenStorage = TokenStorageService();
  final AuthenticatedClient _authenticatedClient = AuthenticatedClient();

  Future<Map<String, String>> _authHeaders() async {
    final token = await _tokenStorage.getAccessToken();
    return {
      'Content-Type': 'application/json',
      if (token != null) 'Authorization': 'Bearer $token',
    };
  }

  Future<CheckinModel> submitCheckin({
    required int stress,
    required int workload,
    required double sleepHours,
    required int activityScore,
  }) async {
    final response = await http.post(
      Uri.parse(ApiConstants.checkin),
      headers: await _authHeaders(),
      body: jsonEncode({
        'self_rated_stress': stress,
        'workload': workload,
        'sleep_hours': sleepHours,
        'activity_score': activityScore,
      }),
    );

    if (response.statusCode != 200) {
      throw ApiException(response.statusCode, _extractDetail(response));
    }
    return CheckinModel.fromJson(jsonDecode(response.body));
  }

  /// Returns null if the student hasn't checked in today yet (backend 404)
  /// -- callers treat that as "show the check-in prompt," not an error.
  Future<CheckinModel?> getTodayCheckin() async {
    final response = await http.get(
      Uri.parse(ApiConstants.checkinToday),
      headers: await _authHeaders(),
    );

    if (response.statusCode == 404) return null;
    if (response.statusCode != 200) {
      throw ApiException(response.statusCode, _extractDetail(response));
    }
    return CheckinModel.fromJson(jsonDecode(response.body));
  }

  Future<int> getStreak() async {
    final response = await http.get(
      Uri.parse(ApiConstants.checkinStreak),
      headers: await _authHeaders(),
    );

    if (response.statusCode != 200) {
      throw ApiException(response.statusCode, _extractDetail(response));
    }
    return jsonDecode(response.body)['streak'] as int;
  }

  Future<List<CheckinModel>> getHistory({int days = 7}) async {
    final response = await _authenticatedClient.get(
      Uri.parse(ApiConstants.checkinHistory(days)),
    );

    if (response.statusCode != 200) {
      throw ApiException(response.statusCode, _extractDetail(response));
    }
    final List<dynamic> data = jsonDecode(response.body);
    return data.map((e) => CheckinModel.fromJson(e)).toList();
  }

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
