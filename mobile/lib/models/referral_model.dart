class CounselorModel {
  final String id;
  final String fullName;
  final String specialization;
  final String contactEmail;
  final String availability;

  const CounselorModel({
    required this.id,
    required this.fullName,
    required this.specialization,
    required this.contactEmail,
    required this.availability,
  });

  factory CounselorModel.fromJson(Map<String, dynamic> json) {
    return CounselorModel(
      id: json['_id'] as String,
      fullName: json['full_name'] as String,
      specialization: json['specialization'] as String? ?? '',
      contactEmail: json['contact_email'] as String? ?? '',
      availability: json['availability'] as String? ?? '',
    );
  }
}

class ReferralModel {
  final String id;
  final String counselorId;
  final String status;
  final DateTime requestedAt;
  final DateTime updatedAt;
  final String? studentId;
  final String? studentName;

  const ReferralModel({
    required this.id,
    required this.counselorId,
    required this.status,
    required this.requestedAt,
    required this.updatedAt,
    this.studentId,
    this.studentName,
  });

  factory ReferralModel.fromJson(Map<String, dynamic> json) {
    return ReferralModel(
      id: json['_id'] as String,
      counselorId: json['counselor_id'] as String,
      status: json['status'] as String,
      requestedAt: DateTime.parse(json['requested_at'] as String),
      updatedAt: DateTime.parse(json['updated_at'] as String),
      studentId: json['student_id'] as String?,
      studentName: json['student_name'] as String?,
    );
  }
}

class ExternalSupportResourceModel {
  final String id;
  final String name;
  final String specialization;
  final String? contactEmail;
  final String? websiteUrl;
  final String costDescription;
  final bool isActive;

  const ExternalSupportResourceModel({
    required this.id,
    required this.name,
    required this.specialization,
    required this.contactEmail,
    required this.websiteUrl,
    required this.costDescription,
    required this.isActive,
  });

  factory ExternalSupportResourceModel.fromJson(Map<String, dynamic> json) {
    return ExternalSupportResourceModel(
      id: json['_id'] as String,
      name: json['name'] as String,
      specialization: json['specialization'] as String,
      contactEmail: json['contact_email'] as String?,
      websiteUrl: json['website_url'] as String?,
      costDescription: json['cost_description'] as String,
      isActive: json['is_active'] as bool? ?? true,
    );
  }
}
