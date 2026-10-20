import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/theme.dart';
import '../../models/checkin_model.dart';
import '../../models/risk_status_model.dart';
import '../../providers/auth_provider.dart';
import '../../services/behavior_service.dart';
import '../../services/risk_service.dart';
import '../checkin/checkin_screen.dart';

/// As of Phase 5, the check-in card is wired to real data (today's check-in
/// status + streak) and a consent-independent student-only risk status.
class DashboardTab extends StatefulWidget {
  const DashboardTab({super.key});

  @override
  State<DashboardTab> createState() => _DashboardTabState();
}

class _DashboardTabState extends State<DashboardTab> {
  final BehaviorService _behaviorService = BehaviorService();
  final RiskService _riskService = RiskService();

  CheckinModel? _todayCheckin;
  RiskStatusModel? _riskStatus;
  int _streak = 0;
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });
    try {
      final results = await Future.wait([
        _behaviorService.getTodayCheckin(),
        _behaviorService.getStreak(),
        _riskService.getStatus(),
      ]);
      if (!mounted) return;
      setState(() {
        _todayCheckin = results[0] as CheckinModel?;
        _streak = results[1] as int;
        _riskStatus = results[2] as RiskStatusModel;
      });
    } catch (_) {
      if (mounted) {
        setState(() {
          _error =
              'Could not refresh your dashboard. Check your connection and try again.';
        });
      }
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _openCheckin() async {
    final submitted = await Navigator.of(context).push<bool>(
      MaterialPageRoute(builder: (_) => const CheckinScreen()),
    );
    if (submitted == true) _loadData();
  }

  @override
  Widget build(BuildContext context) {
    final user = context.watch<AuthProvider>().currentUser;
    final firstName = (user?.fullName ?? 'there').split(' ').first;

    return Scaffold(
      appBar: AppBar(title: const Text('MindPulse')),
      body: RefreshIndicator(
        onRefresh: _loadData,
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Hi, $firstName 👋',
                  style: Theme.of(context).textTheme.headlineMedium),
              const SizedBox(height: 4),
              Text(
                "Here's your well-being snapshot",
                style: Theme.of(context).textTheme.bodyMedium,
              ),
              if (_error != null) ...[
                const SizedBox(height: 16),
                Card(
                  child: ListTile(
                    leading: const Icon(Icons.cloud_off_outlined),
                    title: Text(_error!),
                    trailing: IconButton(
                      tooltip: 'Retry',
                      onPressed: _loadData,
                      icon: const Icon(Icons.refresh),
                    ),
                  ),
                ),
              ],
              const SizedBox(height: 24),
              _StatusCard(status: _riskStatus, isLoading: _isLoading),
              if (_riskStatus?.escalationSent == true) ...[
                const SizedBox(height: 12),
                const Card(
                  child: ListTile(
                    leading: Icon(Icons.notifications_active_outlined),
                    title: Text('Support contact notified'),
                    subtitle: Text(
                      'Your selected support contacts received a brief alert after a sustained high pattern. Chat content was not shared.',
                    ),
                  ),
                ),
              ],
              const SizedBox(height: 16),
              Row(
                children: [
                  Expanded(
                    child: _QuickStatCard(
                      label: 'day streak',
                      value: _isLoading ? '—' : '$_streak',
                      icon: Icons.local_fire_department_outlined,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: _QuickStatCard(
                      label: 'Last sleep',
                      value: _todayCheckin != null
                          ? '${_todayCheckin!.sleepHours.toStringAsFixed(1)}h'
                          : 'No data yet',
                      icon: Icons.bedtime_outlined,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 24),
              Text("Today's check-in",
                  style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 12),
              _CheckinCard(
                isLoading: _isLoading,
                checkin: _todayCheckin,
                onTap: _openCheckin,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _CheckinCard extends StatelessWidget {
  final bool isLoading;
  final CheckinModel? checkin;
  final VoidCallback onTap;

  const _CheckinCard(
      {required this.isLoading, required this.checkin, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final done = checkin != null;
    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(18),
        onTap: isLoading ? null : onTap,
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Row(
            children: [
              Icon(
                done ? Icons.check_circle : Icons.edit_note,
                color: done ? AppTheme.riskLow : AppTheme.primaryColor,
                size: 32,
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      done
                          ? "You've checked in today"
                          : "You haven't checked in today",
                      style: const TextStyle(fontWeight: FontWeight.w600),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      done
                          ? 'Stress ${checkin!.selfRatedStress}/10 · Workload ${checkin!.workload}/10 — tap to update'
                          : 'Takes 30 seconds',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                  ],
                ),
              ),
              const Icon(Icons.chevron_right, color: AppTheme.textSecondary),
            ],
          ),
        ),
      ),
    );
  }
}

class _StatusCard extends StatelessWidget {
  final RiskStatusModel? status;
  final bool isLoading;

  const _StatusCard({required this.status, required this.isLoading});

  @override
  Widget build(BuildContext context) {
    final title = switch (status?.status) {
      'awaiting_checkin' => 'Check in to get started',
      'insufficient_data' => 'Building your baseline',
      'monitoring' => 'Monitoring your well-being',
      'sustained' => '${status!.riskLevel} pattern sustained',
      _ => isLoading ? 'Loading your status' : 'Status unavailable',
    };
    final description = status?.message ??
        (isLoading
            ? 'Your latest signals are being loaded.'
            : 'Pull down to refresh your status.');
    final currentStatus = status;
    final detail = currentStatus == null || currentStatus.weightedScore == null
        ? null
        : 'Observed ${currentStatus.observedLevel} · score ${(currentStatus.weightedScore! * 100).round()}% · ${currentStatus.consecutiveDaysAtLevel} consecutive days';

    return Card(
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(18),
          gradient: const LinearGradient(
            colors: [AppTheme.primaryColor, AppTheme.secondaryColor],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Well-being status',
                style: TextStyle(color: Colors.white70, fontSize: 13)),
            const SizedBox(height: 6),
            Text(
              title,
              style: const TextStyle(
                  color: Colors.white,
                  fontSize: 20,
                  fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 6),
            Text(
              description,
              style: const TextStyle(color: Colors.white70, fontSize: 13),
            ),
            if (detail != null) ...[
              const SizedBox(height: 8),
              Text(detail,
                  style: const TextStyle(color: Colors.white70, fontSize: 12)),
            ],
          ],
        ),
      ),
    );
  }
}

class _QuickStatCard extends StatelessWidget {
  final String label;
  final String value;
  final IconData icon;

  const _QuickStatCard(
      {required this.label, required this.value, required this.icon});

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icon, color: AppTheme.secondaryColor),
            const SizedBox(height: 10),
            Text(value,
                style:
                    const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
            const SizedBox(height: 2),
            Text(label, style: Theme.of(context).textTheme.bodyMedium),
          ],
        ),
      ),
    );
  }
}
