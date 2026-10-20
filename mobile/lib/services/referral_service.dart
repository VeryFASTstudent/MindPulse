import 'dart:convert';

import 'package:http/http.dart' as http;

import '../core/constants.dart';
import '../models/referral_model.dart';
import 'api_exception.dart';
import 'token_storage_service.dart';

class ReferralService {
  final TokenStorageService _tokenStorage = TokenStorageService();

  Future<List<CounselorModel>> getCounselors() async {
    final response = await http.get(
      Uri.parse(ApiConstants.counselors),
      headers: await _authHeaders(),
    );
    if (response.statusCode != 200) {
      throw ApiException(response.statusCode, _extractDetail(response));
    }
    final data = jsonDecode(response.body) as List<dynamic>;
    return data
        .map((item) => CounselorModel.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  Future<List<ExternalSupportResourceModel>> getExternalResources() async {
    final response = await http.get(
      Uri.parse(ApiConstants.externalSupportResources),
      headers: await _authHeaders(),
    );
    if (response.statusCode != 200) {
      throw ApiException(response.statusCode, _extractDetail(response));
    }
    final data = jsonDecode(response.body) as List<dynamic>;
    return data
        .map((item) =>
            ExternalSupportResourceModel.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  Future<List<ReferralModel>> getMyRequests() async {
    final response = await http.get(
      Uri.parse(ApiConstants.myReferrals),
      headers: await _authHeaders(),
    );
    if (response.statusCode != 200) {
      throw ApiException(response.statusCode, _extractDetail(response));
    }
    final data = jsonDecode(response.body) as List<dynamic>;
    return data
        .map((item) => ReferralModel.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  Future<ReferralModel> requestSupport(String counselorId) async {
    final response = await http.post(
      Uri.parse(ApiConstants.referralRequests),
      headers: await _authHeaders(),
      body: jsonEncode({
        'counselor_id': counselorId,
        'student_confirmed': true,
      }),
    );
    if (response.statusCode != 201) {
      throw ApiException(response.statusCode, _extractDetail(response));
    }
    return ReferralModel.fromJson(jsonDecode(response.body));
  }

  Future<List<ReferralModel>> getCounselorInbox() async {
    final response = await http.get(
      Uri.parse(ApiConstants.counselorInbox),
      headers: await _authHeaders(),
    );
    if (response.statusCode != 200) {
      throw ApiException(response.statusCode, _extractDetail(response));
    }
    final data = jsonDecode(response.body) as List<dynamic>;
    return data
        .map((item) => ReferralModel.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  Future<ReferralModel> updateRequestStatus(
    String requestId,
    String status,
  ) async {
    final response = await http.patch(
      Uri.parse('${ApiConstants.referralRequests}/$requestId'),
      headers: await _authHeaders(),
      body: jsonEncode({'status': status}),
    );
    if (response.statusCode != 200) {
      throw ApiException(response.statusCode, _extractDetail(response));
    }
    return ReferralModel.fromJson(jsonDecode(response.body));
  }

  Future<Map<String, String>> _authHeaders() async {
    final token = await _tokenStorage.getAccessToken();
    return {
      'Content-Type': 'application/json',
      if (token != null) 'Authorization': '******',
    };
  }

  String _extractDetail(http.Response response) {
    try {
      return jsonDecode(response.body)['detail']?.toString() ??
          'Could not complete the support request.';
    } catch (_) {
      return 'Could not complete the support request.';
    }
  }
}
