class DailySentimentModel {
  final DateTime date;
  final double averageSentiment;
  final int messageCount;

  const DailySentimentModel({
    required this.date,
    required this.averageSentiment,
    required this.messageCount,
  });

  factory DailySentimentModel.fromJson(Map<String, dynamic> json) {
    return DailySentimentModel(
      date: DateTime.parse(json['date'] as String),
      averageSentiment: (json['avg_sentiment'] as num).toDouble(),
      messageCount: json['message_count'] as int,
    );
  }
}
