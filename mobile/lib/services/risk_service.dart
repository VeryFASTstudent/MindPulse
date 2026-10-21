import 'dart:convert';

import '../core/constants.dart';
import '../models/risk_status_model.dart';
import 'api_exception.dart';
import 'authenticated_client.dart';

class RiskService {
  final AuthenticatedClient _authenticatedClient = AuthenticatedClient();

  Future<RiskStatusModel> getStatus() async {
    final response = await _authenticatedClient.get(Uri.parse(ApiConstants.riskStatus));
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
