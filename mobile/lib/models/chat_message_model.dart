/// Mirrors the backend's MessageOut schema (app/chat/schemas.py).
class ChatMessage {
  final String id;
  final String sessionId;
  final String sender; // "student" | "assistant"
  final String text;
  final DateTime createdAt;
  final String? responseMode;
  final bool synthetic;

  ChatMessage({
    required this.id,
    required this.sessionId,
    required this.sender,
    required this.text,
    required this.createdAt,
    this.responseMode,
    this.synthetic = false,
  });

  factory ChatMessage.fromJson(Map<String, dynamic> json) {
    return ChatMessage(
      id: json['_id'] as String,
      sessionId: json['session_id'] as String,
      sender: json['sender'] as String,
      text: json['text'] as String,
      createdAt: DateTime.parse(json['created_at'] as String),
      responseMode: json['response_mode'] as String?,
      synthetic: json['synthetic'] as bool? ?? false,
    );
  }
}
