import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/routes.dart';
import '../../core/theme.dart';
import '../../models/consent_model.dart';
import '../../providers/auth_provider.dart';
import '../../services/consent_service.dart';

class ProfileTab extends StatefulWidget {
  const ProfileTab({super.key});

  @override
  State<ProfileTab> createState() => _ProfileTabState();
}

class _ProfileTabState extends State<ProfileTab> {
  final ConsentService _consentService = ConsentService();
  ConsentModel? _consent;
  bool _isLoadingConsent = true;
  bool _isSavingConsent = false;

  @override
  void initState() {
    super.initState();
    _loadConsent();
  }

  Future<void> _loadConsent() async {
    try {
      final consent = await _consentService.getMine();
      if (mounted) setState(() => _consent = consent);
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Could not load privacy settings: $error')),
        );
      }
    } finally {
      if (mounted) setState(() => _isLoadingConsent = false);
    }
  }

  Future<void> _saveConsent(ConsentModel updated) async {
    setState(() => _isSavingConsent = true);
    try {
      final saved = await _consentService.updateMine(updated);
      if (mounted) setState(() => _consent = saved);
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Privacy settings were not saved: $error')),
        );
      }
    } finally {
      if (mounted) setState(() => _isSavingConsent = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final authProvider = context.watch<AuthProvider>();
    final user = authProvider.currentUser;

    return Scaffold(
      appBar: AppBar(title: const Text('Profile & Settings')),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          CircleAvatar(
            radius: 36,
            backgroundColor: AppTheme.primaryColor,
            child: Text(
              (user?.fullName.isNotEmpty ?? false) ? user!.fullName[0].toUpperCase() : '?',
              style: const TextStyle(color: Colors.white, fontSize: 28, fontWeight: FontWeight.bold),
            ),
          ),
          const SizedBox(height: 16),
          Center(
            child: Text(user?.fullName ?? '', style: Theme.of(context).textTheme.titleMedium),
          ),
          Center(
            child: Text(user?.email ?? '', style: Theme.of(context).textTheme.bodyMedium),
          ),
          const SizedBox(height: 32),
          Card(
            child: ListTile(
              leading: const Icon(Icons.verified_user_outlined),
              title: const Text('Role'),
              trailing: Text(user?.role ?? ''),
            ),
          ),
          const SizedBox(height: 12),
          const SizedBox(height: 12),
          Card(
            child: Column(
              children: [
                const ListTile(
                  leading: Icon(Icons.privacy_tip_outlined),
                  title: Text('Privacy & sharing'),
                  subtitle: Text('Sharing is off unless you turn it on.'),
                ),
                if (_isLoadingConsent)
                  const Padding(
                    padding: EdgeInsets.all(20),
                    child: CircularProgressIndicator(),
                  )
                else if (_consent != null) ...[
                  SwitchListTile(
                    title: const Text('Share summary with parent'),
                    subtitle: const Text('Allow a linked parent to see well-being summaries.'),
                    value: _consent!.shareSummaryWithParent,
                    onChanged: _isSavingConsent
                        ? null
                        : (value) => _saveConsent(
                              _consent!.copyWith(shareSummaryWithParent: value),
                            ),
                  ),
                  SwitchListTile(
                    title: const Text('Share with university support'),
                    subtitle: const Text('Allow authorized support staff to see your summary.'),
                    value: _consent!.shareWithUniversitySupport,
                    onChanged: _isSavingConsent
                        ? null
                        : (value) => _saveConsent(
                              _consent!.copyWith(shareWithUniversitySupport: value),
                            ),
                  ),
                  SwitchListTile(
                    title: const Text('Share data for referrals'),
                    subtitle: const Text('Allow your summary to accompany a referral request.'),
                    value: _consent!.allowReferralDataShare,
                    onChanged: _isSavingConsent
                        ? null
                        : (value) => _saveConsent(
                              _consent!.copyWith(allowReferralDataShare: value),
                            ),
                  ),
                ] else
                  const ListTile(
                    title: Text('Privacy settings unavailable'),
                    subtitle: Text('Check your connection and reopen Profile to try again.'),
                  ),
              ],
            ),
          ),
          const SizedBox(height: 32),
          OutlinedButton.icon(
            onPressed: () async {
              await authProvider.logout();
              if (context.mounted) {
                Navigator.of(context).pushNamedAndRemoveUntil(
                  AppRoutes.login,
                  (route) => false,
                );
              }
            },
            icon: const Icon(Icons.logout, color: AppTheme.riskHigh),
            label: const Text('Log Out', style: TextStyle(color: AppTheme.riskHigh)),
            style: OutlinedButton.styleFrom(
              minimumSize: const Size.fromHeight(50),
              side: const BorderSide(color: AppTheme.riskHigh),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
            ),
          ),
        ],
      ),
    );
  }
}
