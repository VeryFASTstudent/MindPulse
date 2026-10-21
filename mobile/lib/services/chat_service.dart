import 'dart:convert';

import 'package:http/http.dart' as http;

import '../core/constants.dart';
import '../models/chat_message_model.dart';
import 'api_exception.dart';
import 'authenticated_client.dart';
import 'token_storage_service.dart';

class ChatService {
  final TokenStorageService _tokenStorage = TokenStorageService();
  final AuthenticatedClient _authenticatedClient = AuthenticatedClient();

  Future<Map<String, String>> _authHeaders() async {
    final token = await _tokenStorage.getAccessToken();
    return {
      'Content-Type': 'application/json',
      if (token != null) 'Authorization': 'Bearer $token',
    };
  }

  /// Sends a message and returns [studentMessage, assistantMessage] in
  /// that order, matching the backend's ChatReplyResponse shape.
  Future<ChatSendResult> sendMessage(String text) async {
    final response = await http.post(
      Uri.parse(ApiConstants.chatMessage),
      headers: await _authHeaders(),
      body: jsonEncode({'text': text}),
    );

    if (response.statusCode != 200) {
      throw ApiException(response.statusCode, _extractDetail(response));
    }

    final data = jsonDecode(response.body);
    return ChatSendResult(
      messages: [
        ChatMessage.fromJson(data['student_message']),
        ChatMessage.fromJson(data['assistant_message']),
      ],
      sessionId: data['session_id'] as String,
      checkinState: data['checkin_state'] as String?,
    );
  }

  Future<String> confirmCheckin(String sessionId, String action) async {
    final response = await http.post(
      Uri.parse('${ApiConstants.apiBaseUrl}/chat/checkin/confirm'),
      headers: await _authHeaders(),
      body: jsonEncode({'session_id': sessionId, 'action': action}),
    );
    if (response.statusCode != 200) {
      throw ApiException(response.statusCode, _extractDetail(response));
    }
    return (jsonDecode(response.body) as Map<String, dynamic>)['status'] as String;
  }

  Future<List<ChatMessage>> getRecentMessages() async {
    final sessionsResponse = await _authenticatedClient.get(
      Uri.parse('${ApiConstants.apiBaseUrl}/chat/sessions'),
    );
    if (sessionsResponse.statusCode != 200) {
      throw ApiException(
          sessionsResponse.statusCode, _extractDetail(sessionsResponse));
    }

    final sessions = jsonDecode(sessionsResponse.body) as List<dynamic>;
    if (sessions.isEmpty) return [];
    final allMessages = <ChatMessage>[];
    for (final session in sessions.reversed) {
      final sessionId = (session as Map<String, dynamic>)['_id'] as String;
      final messagesResponse = await _authenticatedClient.get(
        Uri.parse('${ApiConstants.apiBaseUrl}/chat/sessions/$sessionId/messages'),
      );
      if (messagesResponse.statusCode != 200) {
        throw ApiException(
            messagesResponse.statusCode, _extractDetail(messagesResponse));
      }
      final messages = jsonDecode(messagesResponse.body) as List<dynamic>;
      allMessages.addAll(
        messages.map((item) => ChatMessage.fromJson(item as Map<String, dynamic>)),
      );
    }
    return allMessages;
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

class ChatSendResult {
  final List<ChatMessage> messages;
  final String sessionId;
  final String? checkinState;

  ChatSendResult({
    required this.messages,
    required this.sessionId,
    required this.checkinState,
  });
}
