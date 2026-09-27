/// Thrown whenever the backend returns a non-2xx response. Carries the
/// FastAPI `detail` message so screens can show the real reason (e.g.
/// "Incorrect email or password") instead of a generic failure message.
class ApiException implements Exception {
  final int statusCode;
  final String message;

  ApiException(this.statusCode, this.message);

  @override
  String toString() => message;
}
