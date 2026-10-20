import 'package:flutter/material.dart';

/// Used on both auth screens so "logging in..." spinner behavior is
/// implemented once instead of duplicated per screen.
class PrimaryButton extends StatelessWidget {
  final String label;
  final VoidCallback? onPressed;
  final bool isLoading;

  const PrimaryButton({
    super.key,
    required this.label,
    required this.onPressed,
    this.isLoading = false,
  });

  @override
  Widget build(BuildContext context) {
    return ElevatedButton(
      onPressed: isLoading ? null : onPressed,
      child: isLoading
          ? const SizedBox(
              height: 22,
              width: 22,
              child: CircularProgressIndicator(
                  strokeWidth: 2.5, color: Colors.white),
            )
          : Text(label,
              style:
                  const TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
    );
  }
}
