import 'package:flutter/material.dart';

import '../../models/consent_model.dart';
import '../../models/referral_model.dart';
import '../../services/api_exception.dart';
import '../../services/consent_service.dart';
import '../../services/referral_service.dart';

class SupportTab extends StatefulWidget {
  const SupportTab({super.key});

  @override
  State<SupportTab> createState() => _SupportTabState();
}

class _SupportTabState extends State<SupportTab> {
  final ReferralService _referralService = ReferralService();
  final ConsentService _consentService = ConsentService();
  List<CounselorModel> _counselors = [];
  List<ExternalSupportResourceModel> _externalResources = [];
  List<ReferralModel> _requests = [];
  ConsentModel? _consent;
  bool _loading = true;
  bool _submitting = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final results = await Future.wait([
        _referralService.getCounselors(),
        _referralService.getExternalResources(),
        _referralService.getMyRequests(),
        _consentService.getMine(),
      ]);
      if (!mounted) return;
      setState(() {
        _counselors = results[0] as List<CounselorModel>;
        _externalResources = results[1] as List<ExternalSupportResourceModel>;
        _requests = results[2] as List<ReferralModel>;
        _consent = results[3] as ConsentModel;
      });
    } on ApiException catch (error) {
      if (mounted) {
        setState(() => _error = error.message);
      }
    } catch (_) {
      if (mounted) {
        setState(
            () => _error = 'Could not load support options. Please try again.');
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _request(CounselorModel counselor) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Send support request?'),
        content: Text(
          'This sends your account identity and request status to ${counselor.fullName}. '
          'Your chat messages are not shared. You can withdraw referral-sharing consent in Profile.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Send request'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;

    setState(() => _submitting = true);
    try {
      await _referralService.requestSupport(counselor.id);
      await _load();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Your support request was sent.')),
        );
      }
    } on ApiException catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(error.message)));
      }
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Support')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? _ErrorCard(message: _error!, onRetry: _load)
              : RefreshIndicator(
                  onRefresh: _load,
                  child: ListView(
                    physics: const AlwaysScrollableScrollPhysics(),
                    padding: const EdgeInsets.all(20),
                    children: [
                      Text('You can reach out',
                          style: Theme.of(context).textTheme.headlineMedium),
                      const SizedBox(height: 6),
                      Text(
                        'MindPulse is not a crisis service or a substitute for professional care. '
                        'Choosing to contact support is always up to you.',
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                      if (_consent?.allowReferralDataShare != true) ...[
                        const SizedBox(height: 16),
                        const Card(
                          child: ListTile(
                            leading: Icon(Icons.lock_outline),
                            title: Text('Referral sharing is off'),
                            subtitle: Text(
                              'You can browse support options. To send an in-app request, first enable referral sharing in Profile.',
                            ),
                          ),
                        ),
                      ],
                      const SizedBox(height: 20),
                      Text('University counselors',
                          style: Theme.of(context).textTheme.titleMedium),
                      const SizedBox(height: 10),
                      if (_counselors.isEmpty)
                        const Card(
                          child: ListTile(
                            title: Text('No counselors are listed yet'),
                            subtitle: Text(
                                'Please check with your university support office.'),
                          ),
                        )
                      else
                        ..._counselors.map(
                          (counselor) => Padding(
                            padding: const EdgeInsets.only(bottom: 10),
                            child: Card(
                              child: Padding(
                                padding: const EdgeInsets.all(16),
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(counselor.fullName,
                                        style: Theme.of(context)
                                            .textTheme
                                            .titleMedium),
                                    if (counselor.specialization.isNotEmpty)
                                      Text(counselor.specialization),
                                    if (counselor.availability.isNotEmpty)
                                      Text(
                                          'Availability: ${counselor.availability}'),
                                    if (counselor.contactEmail.isNotEmpty)
                                      Text(counselor.contactEmail),
                                    const SizedBox(height: 12),
                                    FilledButton.tonal(
                                      onPressed: _submitting ||
                                              _consent?.allowReferralDataShare !=
                                                  true
                                          ? null
                                          : () => _request(counselor),
                                      child: const Text('Request support'),
                                    ),
                                  ],
                                ),
                              ),
                            ),
                          ),
                        ),
                      const SizedBox(height: 12),
                      Text('External support resources',
                          style: Theme.of(context).textTheme.titleMedium),
                      const SizedBox(height: 10),
                      if (_externalResources.isEmpty)
                        const Card(
                          child: ListTile(
                            title: Text('No external resources are listed'),
                            subtitle: Text(
                              'Your university can add verified providers and support options here.',
                            ),
                          ),
                        )
                      else
                        ..._externalResources.map(
                          (resource) => Card(
                            child: Padding(
                              padding: const EdgeInsets.all(16),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    resource.name,
                                    style:
                                        Theme.of(context).textTheme.titleMedium,
                                  ),
                                  const SizedBox(height: 4),
                                  Text(resource.specialization),
                                  Text('Cost: ${resource.costDescription}'),
                                  if (resource.contactEmail != null)
                                    SelectableText(
                                        'Email: ${resource.contactEmail}'),
                                  if (resource.websiteUrl != null)
                                    SelectableText(
                                        'Website: ${resource.websiteUrl}'),
                                ],
                              ),
                            ),
                          ),
                        ),
                      const SizedBox(height: 12),
                      Text('Your requests',
                          style: Theme.of(context).textTheme.titleMedium),
                      const SizedBox(height: 10),
                      if (_requests.isEmpty)
                        const Card(
                          child: ListTile(
                            title: Text('No support requests yet'),
                            subtitle:
                                Text('Any request you send will appear here.'),
                          ),
                        )
                      else
                        ..._requests.map(
                          (request) => Card(
                            child: ListTile(
                              leading: const Icon(Icons.support_agent),
                              title: Text('Request ${request.status}'),
                              subtitle: Text(
                                'Sent ${request.requestedAt.toLocal().toString().split(' ').first}',
                              ),
                            ),
                          ),
                        ),
                    ],
                  ),
                ),
    );
  }
}

class _ErrorCard extends StatelessWidget {
  final String message;
  final VoidCallback onRetry;

  const _ErrorCard({required this.message, required this.onRetry});

  @override
  Widget build(BuildContext context) => Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(message, textAlign: TextAlign.center),
              const SizedBox(height: 12),
              OutlinedButton(
                  onPressed: onRetry, child: const Text('Try again')),
            ],
          ),
        ),
      );
}
