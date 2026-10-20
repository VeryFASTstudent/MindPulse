import 'package:flutter/foundation.dart';

import '../models/user_model.dart';
import '../services/api_exception.dart';
import '../services/auth_service.dart';

enum AuthStatus { unknown, authenticated, unauthenticated }

/// Single source of truth for "who is logged in right now," consumed by
/// SplashScreen (to decide where to route on app start) and by
/// LoginScreen/RegisterScreen/HomeShell (to trigger/react to auth changes).
class AuthProvider extends ChangeNotifier {
  final AuthService _authService = AuthService();

  AuthStatus status = AuthStatus.unknown;
  UserModel? currentUser;
  String? errorMessage;
  bool isLoading = false;

  /// Called once on app start (from SplashScreen) to check for an
  /// existing valid session before deciding whether to show
  /// login or the home dashboard.
  Future<void> checkAuthStatus() async {
    try {
      final user = await _authService.getCurrentUser();
      currentUser = user;
      status =
          user != null ? AuthStatus.authenticated : AuthStatus.unauthenticated;
    } catch (_) {
      currentUser = null;
      status = AuthStatus.unauthenticated;
      errorMessage =
          'Could not connect to MindPulse. Check that the backend is running and try again.';
    } finally {
      notifyListeners();
    }
  }

  Future<bool> login(String email, String password) async {
    isLoading = true;
    errorMessage = null;
    notifyListeners();

    try {
      await _authService.login(email: email, password: password);
      final user = await _authService.getCurrentUser();
      if (user == null) {
        await _authService.logout();
        errorMessage =
            'Your session could not be verified. Please log in again.';
        return false;
      }
      currentUser = user;
      status = AuthStatus.authenticated;
      return true;
    } on ApiException catch (e) {
      errorMessage = e.message;
      return false;
    } catch (_) {
      errorMessage =
          'Could not connect to MindPulse. Check that the backend is running and try again.';
      return false;
    } finally {
      isLoading = false;
      notifyListeners();
    }
  }

  Future<bool> register({
    required String email,
    required String password,
    required String fullName,
    required String role,
    String? universityId,
    String? program,
    int? semester,
  }) async {
    isLoading = true;
    errorMessage = null;
    notifyListeners();

    try {
      await _authService.register(
        email: email,
        password: password,
        fullName: fullName,
        role: role,
        universityId: universityId,
        program: program,
        semester: semester,
      );
      // Registration succeeded -- log them in immediately so they land
      // straight on the dashboard instead of a second manual login step.
      return await login(email, password);
    } on ApiException catch (e) {
      errorMessage = e.message;
      isLoading = false;
      notifyListeners();
      return false;
    } catch (_) {
      errorMessage =
          'Could not connect to MindPulse. Check that the backend is running and try again.';
      isLoading = false;
      notifyListeners();
      return false;
    }
  }

  Future<void> logout() async {
    await _authService.logout();
    currentUser = null;
    status = AuthStatus.unauthenticated;
    notifyListeners();
  }
}
