/// Mirrors the backend's UserOut schema (app/auth/schemas.py).
/// Keeping field names identical to the API response avoids a mental
/// mapping step every time a new field is added on either side.
class UserModel {
  final String id;
  final String email;
  final String fullName;
  final String role;
  final bool isActive;

  UserModel({
    required this.id,
    required this.email,
    required this.fullName,
    required this.role,
    required this.isActive,
  });

  factory UserModel.fromJson(Map<String, dynamic> json) {
    return UserModel(
      id: json['_id'] as String,
      email: json['email'] as String,
      fullName: json['full_name'] as String,
      role: json['role'] as String,
      isActive: json['is_active'] as bool,
    );
  }
}
