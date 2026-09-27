import 'package:flutter/material.dart';

import '../../core/theme.dart';

/// Reused for every nav tab that isn't built yet, so HomeShell's bottom
/// nav is fully navigable now even though Chat (Phase 4), Trends (Phase
/// 6/7), and Support (Phase 9) don't have real content until their phase.
class PlaceholderTab extends StatelessWidget {
  final String title;
  final IconData icon;
  final String comingInPhase;

  const PlaceholderTab({
    super.key,
    required this.title,
    required this.icon,
    required this.comingInPhase,
  });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(title)),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, size: 56, color: AppTheme.textSecondary.withOpacity(0.4)),
            const SizedBox(height: 16),
            Text(
              '$title is coming in $comingInPhase',
              style: Theme.of(context).textTheme.bodyMedium,
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }
}
