class RiskStatusModel {
  final String status;
  final String riskLevel;
  final String? observedLevel;
  final double? weightedScore;
  final int consecutiveDaysAtLevel;
  final int sampleSize;
  final int requiredSampleSize;
  final bool escalationSent;
  final String message;

  const RiskStatusModel({
    required this.status,
    required this.riskLevel,
    required this.observedLevel,
    required this.weightedScore,
    required this.consecutiveDaysAtLevel,
    required this.sampleSize,
    required this.requiredSampleSize,
    required this.escalationSent,
    required this.message,
  });

  factory RiskStatusModel.fromJson(Map<String, dynamic> json) {
    return RiskStatusModel(
      status: json['status'] as String,
      riskLevel: json['risk_level'] as String,
      observedLevel: json['observed_level'] as String?,
      weightedScore: (json['weighted_score'] as num?)?.toDouble(),
      consecutiveDaysAtLevel: json['consecutive_days_at_level'] as int? ?? 0,
      sampleSize: json['sample_size'] as int? ?? 0,
      requiredSampleSize: json['required_sample_size'] as int? ?? 5,
      escalationSent: json['escalation_sent'] as bool? ?? false,
      message: json['message'] as String,
    );
  }
}
