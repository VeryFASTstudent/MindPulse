class EscalationModel {
  final String id;
  final String studentId;
  final String? studentName;
  final String riskLevel;
  final int consecutiveDays;
  final String summary;
  final String status;
  final DateTime triggerDate;
  final DateTime createdAt;

  const EscalationModel({
    required this.id,
    required this.studentId,
    required this.studentName,
    required this.riskLevel,
    required this.consecutiveDays,
    required this.summary,
    required this.status,
    required this.triggerDate,
    required this.createdAt,
  });

  factory EscalationModel.fromJson(Map<String, dynamic> json) {
    return EscalationModel(
      id: json['_id'] as String,
      studentId: json['student_id'] as String,
      studentName: json['student_name'] as String?,
      riskLevel: json['risk_level'] as String,
      consecutiveDays: json['consecutive_days'] as int,
      summary: json['summary'] as String,
      status: json['status'] as String,
      triggerDate: DateTime.parse(json['trigger_date'] as String),
      createdAt: DateTime.parse(json['created_at'] as String),
    );
  }
}

class AdminUserModel {
  final String id;
  final String fullName;
  final String email;
  final String role;
  final bool isActive;
  final DateTime createdAt;

  const AdminUserModel({
    required this.id,
    required this.fullName,
    required this.email,
    required this.role,
    required this.isActive,
    required this.createdAt,
  });

  factory AdminUserModel.fromJson(Map<String, dynamic> json) {
    return AdminUserModel(
      id: json['_id'] as String,
      fullName: json['full_name'] as String,
      email: json['email'] as String,
      role: json['role'] as String,
      isActive: json['is_active'] as bool,
      createdAt: DateTime.parse(json['created_at'] as String),
    );
  }
}

class AuditEventModel {
  final String id;
  final String actorType;
  final String? actorId;
  final String action;
  final String? status;
  final DateTime createdAt;

  const AuditEventModel({
    required this.id,
    required this.actorType,
    required this.actorId,
    required this.action,
    required this.status,
    required this.createdAt,
  });

  factory AuditEventModel.fromJson(Map<String, dynamic> json) {
    return AuditEventModel(
      id: json['_id'] as String,
      actorType: json['actor_type'] as String,
      actorId: json['actor_id'] as String?,
      action: json['action'] as String,
      status: json['status'] as String?,
      createdAt: DateTime.parse(json['created_at'] as String),
    );
  }
}

class RiskConfigurationModel {
  final double sentimentDeviation;
  final double stressDeviation;
  final double workloadDeviation;
  final double sleepDeviation;
  final double engagementDeviation;
  final double lowMax;
  final double mediumMax;
  final int minConsecutiveDays;

  const RiskConfigurationModel({
    required this.sentimentDeviation,
    required this.stressDeviation,
    required this.workloadDeviation,
    required this.sleepDeviation,
    required this.engagementDeviation,
    required this.lowMax,
    required this.mediumMax,
    required this.minConsecutiveDays,
  });

  factory RiskConfigurationModel.fromJson(Map<String, dynamic> json) {
    return RiskConfigurationModel(
      sentimentDeviation: (json['sentiment_deviation'] as num).toDouble(),
      stressDeviation: (json['stress_deviation'] as num).toDouble(),
      workloadDeviation: (json['workload_deviation'] as num).toDouble(),
      sleepDeviation: (json['sleep_deviation'] as num).toDouble(),
      engagementDeviation: (json['engagement_deviation'] as num).toDouble(),
      lowMax: (json['low_max'] as num).toDouble(),
      mediumMax: (json['medium_max'] as num).toDouble(),
      minConsecutiveDays: json['min_consecutive_days'] as int,
    );
  }

  Map<String, dynamic> toJson() => {
        'sentiment_deviation': sentimentDeviation,
        'stress_deviation': stressDeviation,
        'workload_deviation': workloadDeviation,
        'sleep_deviation': sleepDeviation,
        'engagement_deviation': engagementDeviation,
        'low_max': lowMax,
        'medium_max': mediumMax,
        'min_consecutive_days': minConsecutiveDays,
      };
}

class ParentStudentSummary {
  final String studentId;
  final String fullName;
  final DateTime? lastCheckinAt;
  final double? averageStress;
  final double? averageSleepHours;
  final String? latestWellbeingStatus;
  final List<EscalationModel> escalations;

  const ParentStudentSummary({
    required this.studentId,
    required this.fullName,
    required this.lastCheckinAt,
    required this.averageStress,
    required this.averageSleepHours,
    required this.latestWellbeingStatus,
    required this.escalations,
  });

  factory ParentStudentSummary.fromJson(Map<String, dynamic> json) {
    return ParentStudentSummary(
      studentId: json['student_id'] as String,
      fullName: json['full_name'] as String,
      lastCheckinAt: json['last_checkin_at'] == null
          ? null
          : DateTime.parse(json['last_checkin_at'] as String),
      averageStress: (json['average_stress'] as num?)?.toDouble(),
      averageSleepHours: (json['average_sleep_hours'] as num?)?.toDouble(),
      latestWellbeingStatus: json['latest_wellbeing_status'] as String?,
      escalations: (json['escalations'] as List<dynamic>? ?? [])
          .map((item) => EscalationModel.fromJson(item as Map<String, dynamic>))
          .toList(),
    );
  }
}

class AdminOverview {
  final bool available;
  final bool suppressed;
  final int periodDays;
  final int? cohortSize;
  final Map<String, int> riskDistribution;
  final String message;

  const AdminOverview({
    required this.available,
    required this.suppressed,
    required this.periodDays,
    required this.cohortSize,
    required this.riskDistribution,
    required this.message,
  });

  factory AdminOverview.fromJson(Map<String, dynamic> json) {
    final distribution = json['risk_distribution'] as Map<String, dynamic>;
    return AdminOverview(
      available: json['available'] as bool,
      suppressed: json['suppressed'] as bool,
      periodDays: json['period_days'] as int,
      cohortSize: json['cohort_size'] as int?,
      riskDistribution: distribution.map(
        (key, value) => MapEntry(key, value as int),
      ),
      message: json['message'] as String,
    );
  }
}
