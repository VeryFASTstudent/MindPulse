class CheckinModel {
  final String id;
  final DateTime date;
  final int selfRatedStress;
  final int workload;
  final double sleepHours;
  final int activityScore;
  final bool checkinCompleted;

  CheckinModel({
    required this.id,
    required this.date,
    required this.selfRatedStress,
    required this.workload,
    required this.sleepHours,
    required this.activityScore,
    required this.checkinCompleted,
  });

  factory CheckinModel.fromJson(Map<String, dynamic> json) {
    return CheckinModel(
      id: json['_id'] as String,
      date: DateTime.parse(json['date'] as String),
      selfRatedStress: json['self_rated_stress'] as int,
      workload: json['workload'] as int,
      sleepHours: (json['sleep_hours'] as num).toDouble(),
      activityScore: json['activity_score'] as int,
      checkinCompleted: json['checkin_completed'] as bool,
    );
  }
}
