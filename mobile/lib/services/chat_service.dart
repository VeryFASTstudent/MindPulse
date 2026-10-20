import 'dart:convert';

import 'package:http/http.dart' as http;

import '../core/constants.dart';
import '../models/chat_message_model.dart';
import 'api_exception.dart';
import 'token_storage_service.dart';

class ChatService {
  final TokenStorageService _tokenStorage = TokenStorageService();

  Future<Map<String, String>> _authHeaders() async {
    final token = await _tokenStorage.getAccessToken();
    return {
      'Content-Type': 'application/json',
      if (token != null) 'Authorization': 'Bearer $token',
    };
  }

  /// Sends a message and returns [studentMessage, assistantMessage] in
  /// that order, matching the backend's ChatReplyResponse shape.
  Future<List<ChatMessage>> sendMessage(String text) async {
    final response = await http.post(
      Uri.parse(ApiConstants.chatMessage),
      headers: await _authHeaders(),
      body: jsonEncode({'text': text}),
    );

    if (response.statusCode != 200) {
      throw ApiException(response.statusCode, _extractDetail(response));
    }

    final data = jsonDecode(response.body);
    return [
      ChatMessage.fromJson(data['student_message']),
      ChatMessage.fromJson(data['assistant_message']),
    ];
  }

  Future<List<ChatMessage>> getRecentMessages() async {
    final sessionsResponse = await http.get(
      Uri.parse('${ApiConstants.apiBaseUrl}/chat/sessions'),
      headers: await _authHeaders(),
    );
    if (sessionsResponse.statusCode != 200) {
      throw ApiException(
          sessionsResponse.statusCode, _extractDetail(sessionsResponse));
    }

    final sessions = jsonDecode(sessionsResponse.body) as List<dynamic>;
    if (sessions.isEmpty) return [];
    final sessionId = (sessions.first as Map<String, dynamic>)['_id'] as String;
    final messagesResponse = await http.get(
      Uri.parse('${ApiConstants.apiBaseUrl}/chat/sessions/$sessionId/messages'),
      headers: await _authHeaders(),
    );
    if (messagesResponse.statusCode != 200) {
      throw ApiException(
          messagesResponse.statusCode, _extractDetail(messagesResponse));
    }
    final messages = jsonDecode(messagesResponse.body) as List<dynamic>;
    return messages
        .map((item) => ChatMessage.fromJson(item as Map<String, dynamic>))
        .toList();
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
