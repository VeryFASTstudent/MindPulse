import 'dart:convert';

import 'package:http/http.dart' as http;

import '../core/constants.dart';
import '../models/dashboard_models.dart';
import '../models/referral_model.dart';
import 'api_exception.dart';
import 'token_storage_service.dart';

class DashboardService {
  final TokenStorageService _tokenStorage = TokenStorageService();

  Future<List<ParentStudentSummary>> getParentStudents() async {
    final response = await http.get(
      Uri.parse(ApiConstants.parentStudents),
      headers: await _authHeaders(),
    );
    if (response.statusCode != 200) {
      throw ApiException(response.statusCode, _extractDetail(response));
    }
    final data = jsonDecode(response.body) as List<dynamic>;
    return data
        .map((item) =>
            ParentStudentSummary.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  Future<AdminOverview> getAdminOverview() async {
    final response = await http.get(
      Uri.parse(ApiConstants.adminOverview),
      headers: await _authHeaders(),
    );
    if (response.statusCode != 200) {
      throw ApiException(response.statusCode, _extractDetail(response));
    }
    return AdminOverview.fromJson(jsonDecode(response.body));
  }

  Future<List<EscalationModel>> getCounselorEscalations() async {
    final response = await http.get(
      Uri.parse(ApiConstants.counselorEscalations),
      headers: await _authHeaders(),
    );
    if (response.statusCode != 200) {
      throw ApiException(response.statusCode, _extractDetail(response));
    }
    final data = jsonDecode(response.body) as List<dynamic>;
    return data
        .map((item) => EscalationModel.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  Future<EscalationModel> updateEscalationStatus(
    String eventId,
    String status,
  ) async {
    final response = await http.patch(
      Uri.parse(ApiConstants.counselorEscalationStatus(eventId)),
      headers: await _authHeaders(),
      body: jsonEncode({'status': status}),
    );
    if (response.statusCode != 200) {
      throw ApiException(response.statusCode, _extractDetail(response));
    }
    return EscalationModel.fromJson(jsonDecode(response.body));
  }

  Future<List<AdminUserModel>> getAdminUsers() async {
    final response = await http.get(
      Uri.parse(ApiConstants.adminUsers),
      headers: await _authHeaders(),
    );
    if (response.statusCode != 200) {
      throw ApiException(response.statusCode, _extractDetail(response));
    }
    final data = jsonDecode(response.body) as List<dynamic>;
    return data
        .map((item) => AdminUserModel.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  Future<AdminUserModel> updateAdminUserStatus(
    String userId,
    bool isActive,
  ) async {
    final response = await http.patch(
      Uri.parse('${ApiConstants.adminUsers}/$userId'),
      headers: await _authHeaders(),
      body: jsonEncode({'is_active': isActive}),
    );
    if (response.statusCode != 200) {
      throw ApiException(response.statusCode, _extractDetail(response));
    }
    return AdminUserModel.fromJson(jsonDecode(response.body));
  }

  Future<List<AuditEventModel>> getAdminAudit() async {
    final response = await http.get(
      Uri.parse(ApiConstants.adminAudit),
      headers: await _authHeaders(),
    );
    if (response.statusCode != 200) {
      throw ApiException(response.statusCode, _extractDetail(response));
    }
    final data = jsonDecode(response.body) as List<dynamic>;
    return data
        .map((item) => AuditEventModel.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  Future<RiskConfigurationModel> getRiskConfiguration() async {
    final response = await http.get(
      Uri.parse(ApiConstants.adminRiskConfiguration),
      headers: await _authHeaders(),
    );
    if (response.statusCode != 200) {
      throw ApiException(response.statusCode, _extractDetail(response));
    }
    return RiskConfigurationModel.fromJson(jsonDecode(response.body));
  }

  Future<RiskConfigurationModel> updateRiskConfiguration(
    RiskConfigurationModel configuration,
  ) async {
    final response = await http.put(
      Uri.parse(ApiConstants.adminRiskConfiguration),
      headers: await _authHeaders(),
      body: jsonEncode(configuration.toJson()),
    );
    if (response.statusCode != 200) {
      throw ApiException(response.statusCode, _extractDetail(response));
    }
    return RiskConfigurationModel.fromJson(jsonDecode(response.body));
  }

  Future<List<ExternalSupportResourceModel>> getAdminSupportResources() async {
    final response = await http.get(
      Uri.parse(ApiConstants.adminSupportResources),
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

  Future<ExternalSupportResourceModel> createAdminSupportResource({
    required String name,
    required String specialization,
    required String costDescription,
    String? contactEmail,
    String? websiteUrl,
  }) async {
    final response = await http.post(
      Uri.parse(ApiConstants.adminSupportResources),
      headers: {
        'Content-Type': 'application/json',
        ...await _authHeaders(),
      },
      body: jsonEncode({
        'name': name,
        'specialization': specialization,
        'cost_description': costDescription,
        'contact_email': contactEmail,
        'website_url': websiteUrl,
      }),
    );
    if (response.statusCode != 201) {
      throw ApiException(response.statusCode, _extractDetail(response));
    }
    return ExternalSupportResourceModel.fromJson(jsonDecode(response.body));
  }

  Future<ExternalSupportResourceModel> updateAdminSupportResourceStatus(
    String resourceId,
    bool isActive,
  ) async {
    final response = await http.patch(
      Uri.parse('${ApiConstants.adminSupportResources}/$resourceId'),
      headers: {
        'Content-Type': 'application/json',
        ...await _authHeaders(),
      },
      body: jsonEncode({'is_active': isActive}),
    );
    if (response.statusCode != 200) {
      throw ApiException(response.statusCode, _extractDetail(response));
    }
    return ExternalSupportResourceModel.fromJson(jsonDecode(response.body));
  }

  Future<Map<String, String>> _authHeaders() async {
    final token = await _tokenStorage.getAccessToken();
    return {
      if (token != null) 'Authorization': '******',
    };
  }

  String _extractDetail(http.Response response) {
    try {
      return jsonDecode(response.body)['detail']?.toString() ??
          'Could not load dashboard data.';
    } catch (_) {
      return 'Could not load dashboard data.';
    }
  }
}
