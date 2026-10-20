import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/routes.dart';
import '../../core/theme.dart';
import '../../models/dashboard_models.dart';
import '../../models/referral_model.dart';
import '../../providers/auth_provider.dart';
import '../../services/api_exception.dart';
import '../../services/dashboard_service.dart';
import '../../services/referral_service.dart';

class CounselorDashboard extends StatefulWidget {
  const CounselorDashboard({super.key});

  @override
  State<CounselorDashboard> createState() => _CounselorDashboardState();
}

class _CounselorDashboardState extends State<CounselorDashboard> {
  final ReferralService _service = ReferralService();
  bool _loading = true;
  String? _error;
  List<ReferralModel> _requests = [];
  List<EscalationModel> _escalations = [];
  final DashboardService _dashboardService = DashboardService();

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
        _service.getCounselorInbox(),
        _dashboardService.getCounselorEscalations(),
      ]);
      if (mounted) {
        setState(() {
          _requests = results[0] as List<ReferralModel>;
          _escalations = results[1] as List<EscalationModel>;
        });
      }
    } on ApiException catch (error) {
      if (mounted) setState(() => _error = error.message);
    } catch (_) {
      if (mounted) {
        setState(() => _error =
            'Could not load requests. Check your connection and try again.');
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _update(ReferralModel request, String status) async {
    try {
      await _service.updateRequestStatus(request.id, status);
      await _load();
    } on ApiException catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(error.message)));
      }
    }
  }

  Future<void> _updateEscalation(
    EscalationModel event,
    String status,
  ) async {
    try {
      await _dashboardService.updateEscalationStatus(event.id, status);
      await _load();
    } on ApiException catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(error.message)));
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
              content: Text('Could not update the alert. Try again.')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Counselor support inbox'),
        actions: [_logoutAction(context)],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? _DashboardError(message: _error!, onRetry: _load)
              : RefreshIndicator(
                  onRefresh: _load,
                  child: ListView(
                    physics: const AlwaysScrollableScrollPhysics(),
                    padding: const EdgeInsets.all(20),
                    children: [
                      Text('Student requests',
                          style: Theme.of(context).textTheme.headlineMedium),
                      const SizedBox(height: 6),
                      Text(
                        'Escalations require sustained high indicators and current student consent. Requests are student-initiated. Chat content is never shown.',
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                      const SizedBox(height: 18),
                      Text(
                        'Sustained well-being alerts',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 10),
                      if (_escalations.isEmpty)
                        const _EmptyDashboardCard(
                          message: 'There are no active consented alerts.',
                        )
                      else
                        ..._escalations.map(
                          (event) => Card(
                            margin: const EdgeInsets.only(bottom: 12),
                            child: Padding(
                              padding: const EdgeInsets.all(16),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    event.studentName ?? 'Student',
                                    style:
                                        Theme.of(context).textTheme.titleMedium,
                                  ),
                                  const SizedBox(height: 6),
                                  Text(event.summary),
                                  const SizedBox(height: 6),
                                  Text(
                                    '${event.riskLevel} pattern · ${event.consecutiveDays} consecutive cycles · ${event.status}',
                                  ),
                                  const SizedBox(height: 12),
                                  if (event.status == 'new')
                                    FilledButton.tonal(
                                      onPressed: () => _updateEscalation(
                                        event,
                                        'acknowledged',
                                      ),
                                      child: const Text('Acknowledge'),
                                    )
                                  else if (event.status == 'acknowledged')
                                    OutlinedButton(
                                      onPressed: () => _updateEscalation(
                                        event,
                                        'closed',
                                      ),
                                      child: const Text('Close alert'),
                                    ),
                                ],
                              ),
                            ),
                          ),
                        ),
                      const SizedBox(height: 18),
                      Text(
                        'Student-initiated requests',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 10),
                      if (_requests.isEmpty)
                        const _EmptyDashboardCard(
                          message: 'There are no consented requests right now.',
                        )
                      else
                        ..._requests.map(
                          (request) => Card(
                            margin: const EdgeInsets.only(bottom: 12),
                            child: Padding(
                              padding: const EdgeInsets.all(16),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(request.studentName ?? 'Student',
                                      style: Theme.of(context)
                                          .textTheme
                                          .titleMedium),
                                  const SizedBox(height: 4),
                                  Text(
                                    'Requested ${request.requestedAt.toLocal().toString().split(' ').first} · ${request.status}',
                                  ),
                                  const SizedBox(height: 12),
                                  Wrap(
                                    spacing: 8,
                                    children: [
                                      if (request.status == 'requested') ...[
                                        FilledButton.tonal(
                                          onPressed: () =>
                                              _update(request, 'accepted'),
                                          child: const Text('Accept'),
                                        ),
                                        OutlinedButton(
                                          onPressed: () =>
                                              _update(request, 'declined'),
                                          child: const Text('Decline'),
                                        ),
                                      ],
                                      if (request.status == 'accepted')
                                        FilledButton.tonal(
                                          onPressed: () =>
                                              _update(request, 'completed'),
                                          child: const Text('Mark completed'),
                                        ),
                                    ],
                                  ),
                                ],
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

class ParentDashboard extends StatefulWidget {
  const ParentDashboard({super.key});

  @override
  State<ParentDashboard> createState() => _ParentDashboardState();
}

class _ParentDashboardState extends State<ParentDashboard> {
  final DashboardService _service = DashboardService();
  bool _loading = true;
  String? _error;
  List<ParentStudentSummary> _students = [];

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
      final students = await _service.getParentStudents();
      if (mounted) setState(() => _students = students);
    } on ApiException catch (error) {
      if (mounted) setState(() => _error = error.message);
    } catch (_) {
      if (mounted) {
        setState(() => _error =
            'Could not load shared summaries. Check your connection and try again.');
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Family well-being'),
        actions: [_logoutAction(context)],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? _DashboardError(message: _error!, onRetry: _load)
              : RefreshIndicator(
                  onRefresh: _load,
                  child: ListView(
                    physics: const AlwaysScrollableScrollPhysics(),
                    padding: const EdgeInsets.all(20),
                    children: [
                      Text('Shared summaries',
                          style: Theme.of(context).textTheme.headlineMedium),
                      const SizedBox(height: 6),
                      Text(
                        'You only see linked students who have enabled parent sharing. Private conversations are never included.',
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                      const SizedBox(height: 18),
                      if (_students.isEmpty)
                        const _EmptyDashboardCard(
                          message:
                              'No linked student has shared a summary with you yet.',
                        )
                      else
                        ..._students.map(
                          (student) => Card(
                            margin: const EdgeInsets.only(bottom: 12),
                            child: Padding(
                              padding: const EdgeInsets.all(18),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(student.fullName,
                                      style: Theme.of(context)
                                          .textTheme
                                          .titleMedium),
                                  const SizedBox(height: 12),
                                  Text(
                                    student.averageStress == null
                                        ? 'No recent check-ins shared'
                                        : 'Average self-rated stress: ${student.averageStress}/10',
                                  ),
                                  if (student.averageSleepHours != null)
                                    Text(
                                      'Average reported sleep: ${student.averageSleepHours} hours',
                                    ),
                                  if (student.latestWellbeingStatus != null)
                                    Text(
                                      'Latest well-being indicator: ${student.latestWellbeingStatus}',
                                    ),
                                  if (student.escalations.isNotEmpty) ...[
                                    const SizedBox(height: 12),
                                    const Divider(),
                                    const Text(
                                      'Support notifications',
                                      style: TextStyle(
                                        fontWeight: FontWeight.w600,
                                      ),
                                    ),
                                    ...student.escalations.map(
                                      (event) => ListTile(
                                        contentPadding: EdgeInsets.zero,
                                        leading: const Icon(
                                          Icons.notifications_active_outlined,
                                        ),
                                        title: Text(event.summary),
                                        subtitle: Text(
                                          '${event.riskLevel} · ${event.consecutiveDays} cycles',
                                        ),
                                      ),
                                    ),
                                  ],
                                ],
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

class AdminDashboard extends StatefulWidget {
  const AdminDashboard({super.key});

  @override
  State<AdminDashboard> createState() => _AdminDashboardState();
}

class _AdminDashboardState extends State<AdminDashboard> {
  final DashboardService _service = DashboardService();
  bool _loading = true;
  bool _savingConfiguration = false;
  bool _savingResource = false;
  String? _error;
  AdminOverview? _overview;
  RiskConfigurationModel? _riskConfiguration;
  List<AdminUserModel> _users = [];
  List<AuditEventModel> _auditEvents = [];
  List<ExternalSupportResourceModel> _supportResources = [];

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
        _service.getAdminOverview(),
        _service.getAdminUsers(),
        _service.getAdminAudit(),
        _service.getRiskConfiguration(),
        _service.getAdminSupportResources(),
      ]);
      if (mounted) {
        setState(() {
          _overview = results[0] as AdminOverview;
          _users = results[1] as List<AdminUserModel>;
          _auditEvents = results[2] as List<AuditEventModel>;
          _riskConfiguration = results[3] as RiskConfigurationModel;
          _supportResources = results[4] as List<ExternalSupportResourceModel>;
        });
      }
    } on ApiException catch (error) {
      if (mounted) setState(() => _error = error.message);
    } catch (_) {
      if (mounted) {
        setState(() => _error =
            'Could not load the university overview. Check your connection and try again.');
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _setUserActive(AdminUserModel user, bool isActive) async {
    try {
      final updated = await _service.updateAdminUserStatus(user.id, isActive);
      if (mounted) {
        setState(() {
          _users = _users
              .map((item) => item.id == updated.id ? updated : item)
              .toList();
        });
      }
      await _load();
    } on ApiException catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(error.message)));
      }
    }
  }

  Future<void> _editRiskConfiguration() async {
    final initial = _riskConfiguration;
    if (initial == null) return;
    final updated = await showDialog<RiskConfigurationModel>(
      context: context,
      builder: (_) => _RiskConfigurationDialog(initial: initial),
    );
    if (updated == null) return;

    setState(() => _savingConfiguration = true);
    try {
      final saved = await _service.updateRiskConfiguration(updated);
      if (mounted) {
        setState(() => _riskConfiguration = saved);
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Risk configuration saved.')),
        );
      }
    } on ApiException catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(error.message)));
      }
    } finally {
      if (mounted) setState(() => _savingConfiguration = false);
    }
  }

  Future<void> _addSupportResource() async {
    final resourceData = await showDialog<Map<String, String?>>(
      context: context,
      builder: (_) => const _SupportResourceDialog(),
    );
    if (resourceData == null) return;

    setState(() => _savingResource = true);
    try {
      await _service.createAdminSupportResource(
        name: resourceData['name']!,
        specialization: resourceData['specialization']!,
        costDescription: resourceData['cost_description']!,
        contactEmail: resourceData['contact_email'],
        websiteUrl: resourceData['website_url'],
      );
      await _load();
    } on ApiException catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(error.message)));
      }
    } finally {
      if (mounted) setState(() => _savingResource = false);
    }
  }

  Future<void> _setSupportResourceActive(
    ExternalSupportResourceModel resource,
    bool isActive,
  ) async {
    try {
      final updated = await _service.updateAdminSupportResourceStatus(
        resource.id,
        isActive,
      );
      if (mounted) {
        setState(() {
          _supportResources = _supportResources
              .map((item) => item.id == updated.id ? updated : item)
              .toList();
        });
      }
      await _load();
    } on ApiException catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(error.message)));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final overview = _overview;
    final currentAdminId = context.watch<AuthProvider>().currentUser?.id;
    return Scaffold(
      appBar: AppBar(
        title: const Text('University overview'),
        actions: [_logoutAction(context)],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? _DashboardError(message: _error!, onRetry: _load)
              : RefreshIndicator(
                  onRefresh: _load,
                  child: ListView(
                    physics: const AlwaysScrollableScrollPhysics(),
                    padding: const EdgeInsets.all(20),
                    children: [
                      Text('Aggregate indicators',
                          style: Theme.of(context).textTheme.headlineMedium),
                      const SizedBox(height: 6),
                      Text(
                        'Well-being metrics are opted-in and aggregate-only. Account management is separate; student conversations are never available.',
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                      const SizedBox(height: 18),
                      Card(
                        child: Padding(
                          padding: const EdgeInsets.all(18),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(overview?.message ?? 'Overview unavailable'),
                              if (overview?.available == true) ...[
                                const SizedBox(height: 12),
                                Text('Recent cohort: ${overview!.cohortSize}'),
                                const SizedBox(height: 12),
                                ...overview.riskDistribution.entries.map(
                                  (entry) => ListTile(
                                    contentPadding: EdgeInsets.zero,
                                    leading: Icon(
                                      Icons.circle,
                                      color: _riskColor(entry.key),
                                      size: 14,
                                    ),
                                    title: Text(entry.key),
                                    trailing: Text('${entry.value}'),
                                  ),
                                ),
                              ],
                            ],
                          ),
                        ),
                      ),
                      const SizedBox(height: 12),
                      Card(
                        child: ExpansionTile(
                          leading: const Icon(Icons.manage_accounts_outlined),
                          title: const Text('Account management'),
                          subtitle: Text('${_users.length} accounts'),
                          children: [
                            if (_users.isEmpty)
                              const ListTile(title: Text('No accounts found'))
                            else
                              ..._users.map(
                                (user) => SwitchListTile(
                                  title: Text(user.fullName),
                                  subtitle: Text(
                                    '${user.email} · ${user.role}${user.id == currentAdminId ? ' · you' : ''}',
                                  ),
                                  value: user.isActive,
                                  onChanged: user.id == currentAdminId
                                      ? null
                                      : (active) =>
                                          _setUserActive(user, active),
                                ),
                              ),
                          ],
                        ),
                      ),
                      Card(
                        child: ExpansionTile(
                          leading: const Icon(Icons.medical_services_outlined),
                          title: const Text('External support directory'),
                          subtitle: Text(
                            '${_supportResources.where((resource) => resource.isActive).length} verified resources available to students',
                          ),
                          children: [
                            Padding(
                              padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
                              child: Align(
                                alignment: Alignment.centerRight,
                                child: FilledButton.tonalIcon(
                                  onPressed: _savingResource
                                      ? null
                                      : _addSupportResource,
                                  icon: const Icon(Icons.add),
                                  label: const Text('Add resource'),
                                ),
                              ),
                            ),
                            if (_supportResources.isEmpty)
                              const ListTile(
                                title: Text('No resources added'),
                                subtitle: Text(
                                  'Only add provider details verified by your university.',
                                ),
                              )
                            else
                              ..._supportResources.map(
                                (resource) => SwitchListTile(
                                  title: Text(resource.name),
                                  subtitle: Text(
                                    '${resource.specialization} · ${resource.costDescription}',
                                  ),
                                  value: resource.isActive,
                                  onChanged: (active) =>
                                      _setSupportResourceActive(
                                          resource, active),
                                ),
                              ),
                          ],
                        ),
                      ),
                      Card(
                        child: ExpansionTile(
                          leading: const Icon(Icons.tune),
                          title: const Text('Risk policy'),
                          subtitle: Text(
                            _riskConfiguration == null
                                ? 'Configuration unavailable'
                                : 'Escalate after ${_riskConfiguration!.minConsecutiveDays} consecutive high cycles',
                          ),
                          children: [
                            if (_riskConfiguration != null)
                              Padding(
                                padding:
                                    const EdgeInsets.fromLTRB(16, 0, 16, 8),
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      'Weights: sentiment ${_riskConfiguration!.sentimentDeviation.toStringAsFixed(2)}, stress ${_riskConfiguration!.stressDeviation.toStringAsFixed(2)}, workload ${_riskConfiguration!.workloadDeviation.toStringAsFixed(2)}, sleep ${_riskConfiguration!.sleepDeviation.toStringAsFixed(2)}, engagement ${_riskConfiguration!.engagementDeviation.toStringAsFixed(2)}',
                                    ),
                                    Text(
                                      'Low below ${_riskConfiguration!.lowMax.toStringAsFixed(2)} · medium below ${_riskConfiguration!.mediumMax.toStringAsFixed(2)}',
                                    ),
                                    const SizedBox(height: 8),
                                    Align(
                                      alignment: Alignment.centerRight,
                                      child: FilledButton.tonal(
                                        onPressed: _savingConfiguration
                                            ? null
                                            : _editRiskConfiguration,
                                        child: const Text('Edit policy'),
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                          ],
                        ),
                      ),
                      Card(
                        child: ExpansionTile(
                          leading: const Icon(Icons.history),
                          title: const Text('Audit trail'),
                          subtitle: Text(
                            'Latest ${_auditEvents.length} system and admin actions',
                          ),
                          children: _auditEvents.isEmpty
                              ? const [
                                  ListTile(title: Text('No audit events yet'))
                                ]
                              : _auditEvents
                                  .map(
                                    (event) => ListTile(
                                      dense: true,
                                      title: Text(event.action),
                                      subtitle: Text(
                                        '${event.actorType}${event.status == null ? '' : ' · ${event.status}'} · ${event.createdAt.toLocal()}',
                                      ),
                                    ),
                                  )
                                  .toList(),
                        ),
                      ),
                    ],
                  ),
                ),
    );
  }

  Color _riskColor(String level) => switch (level) {
        'LOW' => AppTheme.riskLow,
        'MEDIUM' => AppTheme.riskMedium,
        'HIGH' => AppTheme.riskHigh,
        _ => AppTheme.textSecondary,
      };
}

class _RiskConfigurationDialog extends StatefulWidget {
  final RiskConfigurationModel initial;

  const _RiskConfigurationDialog({required this.initial});

  @override
  State<_RiskConfigurationDialog> createState() =>
      _RiskConfigurationDialogState();
}

class _RiskConfigurationDialogState extends State<_RiskConfigurationDialog> {
  final _formKey = GlobalKey<FormState>();
  late final Map<String, TextEditingController> _controllers;
  String? _error;

  @override
  void initState() {
    super.initState();
    final config = widget.initial;
    _controllers = {
      'sentiment':
          TextEditingController(text: config.sentimentDeviation.toString()),
      'stress': TextEditingController(text: config.stressDeviation.toString()),
      'workload':
          TextEditingController(text: config.workloadDeviation.toString()),
      'sleep': TextEditingController(text: config.sleepDeviation.toString()),
      'engagement':
          TextEditingController(text: config.engagementDeviation.toString()),
      'low': TextEditingController(text: config.lowMax.toString()),
      'medium': TextEditingController(text: config.mediumMax.toString()),
      'days': TextEditingController(text: config.minConsecutiveDays.toString()),
    };
  }

  @override
  void dispose() {
    for (final controller in _controllers.values) {
      controller.dispose();
    }
    super.dispose();
  }

  void _save() {
    if (!_formKey.currentState!.validate()) return;
    final sentiment = double.parse(_controllers['sentiment']!.text);
    final stress = double.parse(_controllers['stress']!.text);
    final workload = double.parse(_controllers['workload']!.text);
    final sleep = double.parse(_controllers['sleep']!.text);
    final engagement = double.parse(_controllers['engagement']!.text);
    final low = double.parse(_controllers['low']!.text);
    final medium = double.parse(_controllers['medium']!.text);
    final days = int.parse(_controllers['days']!.text);

    if ((sentiment + stress + workload + sleep + engagement - 1).abs() >
            0.001 ||
        low >= medium) {
      setState(() => _error =
          'Weights must total 1.0, and the low threshold must be below medium.');
      return;
    }

    Navigator.of(context).pop(
      RiskConfigurationModel(
        sentimentDeviation: sentiment,
        stressDeviation: stress,
        workloadDeviation: workload,
        sleepDeviation: sleep,
        engagementDeviation: engagement,
        lowMax: low,
        mediumMax: medium,
        minConsecutiveDays: days,
      ),
    );
  }

  Widget _numberField(String label, String key, {bool integer = false}) {
    return TextFormField(
      controller: _controllers[key],
      decoration: InputDecoration(labelText: label),
      keyboardType: const TextInputType.numberWithOptions(decimal: true),
      validator: (value) {
        final parsed =
            integer ? int.tryParse(value ?? '') : double.tryParse(value ?? '');
        if (parsed == null) return 'Enter a valid number';
        if (!integer && (parsed <= 0 || parsed >= 1)) {
          return 'Use a value greater than 0 and less than 1';
        }
        if (integer && (parsed < 2 || parsed > 14)) {
          return 'Choose between 2 and 14 days';
        }
        return null;
      },
    );
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
        title: const Text('Risk scoring policy'),
        content: SizedBox(
          width: 440,
          child: SingleChildScrollView(
            child: Form(
              key: _formKey,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Text(
                    'Weights must add to 1.0. Changes apply to future risk calculations.',
                  ),
                  _numberField('Sentiment weight', 'sentiment'),
                  _numberField('Stress weight', 'stress'),
                  _numberField('Workload weight', 'workload'),
                  _numberField('Sleep weight', 'sleep'),
                  _numberField('Engagement weight', 'engagement'),
                  _numberField('Low threshold', 'low'),
                  _numberField('Medium threshold', 'medium'),
                  _numberField(
                    'Consecutive days before escalation',
                    'days',
                    integer: true,
                  ),
                  if (_error != null) ...[
                    const SizedBox(height: 12),
                    Text(
                      _error!,
                      style: TextStyle(
                        color: Theme.of(context).colorScheme.error,
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: _save,
            child: const Text('Save policy'),
          ),
        ],
      );
}

class _SupportResourceDialog extends StatefulWidget {
  const _SupportResourceDialog();

  @override
  State<_SupportResourceDialog> createState() => _SupportResourceDialogState();
}

class _SupportResourceDialogState extends State<_SupportResourceDialog> {
  final _formKey = GlobalKey<FormState>();
  final _nameController = TextEditingController();
  final _specializationController = TextEditingController();
  final _emailController = TextEditingController();
  final _websiteController = TextEditingController();
  final _costController = TextEditingController();
  String? _error;

  @override
  void dispose() {
    _nameController.dispose();
    _specializationController.dispose();
    _emailController.dispose();
    _websiteController.dispose();
    _costController.dispose();
    super.dispose();
  }

  void _save() {
    if (!_formKey.currentState!.validate()) return;
    final email = _emailController.text.trim();
    final website = _websiteController.text.trim();
    if (email.isEmpty && website.isEmpty) {
      setState(() => _error = 'Add a verified email address or website.');
      return;
    }
    Navigator.of(context).pop({
      'name': _nameController.text.trim(),
      'specialization': _specializationController.text.trim(),
      'contact_email': email.isEmpty ? null : email,
      'website_url': website.isEmpty ? null : website,
      'cost_description': _costController.text.trim(),
    });
  }

  String? _required(String? value) => value == null || value.trim().length < 2
      ? 'Enter at least 2 characters'
      : null;

  @override
  Widget build(BuildContext context) => AlertDialog(
        title: const Text('Add verified support resource'),
        content: SizedBox(
          width: 440,
          child: SingleChildScrollView(
            child: Form(
              key: _formKey,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Text(
                    'Enter provider information verified by your university. Students can view but not submit details to this directory.',
                  ),
                  TextFormField(
                    controller: _nameController,
                    decoration:
                        const InputDecoration(labelText: 'Provider name'),
                    validator: _required,
                  ),
                  TextFormField(
                    controller: _specializationController,
                    decoration: const InputDecoration(
                      labelText: 'Specialization / service',
                    ),
                    validator: _required,
                  ),
                  TextFormField(
                    controller: _emailController,
                    decoration: const InputDecoration(
                      labelText: 'Contact email (optional)',
                    ),
                    keyboardType: TextInputType.emailAddress,
                  ),
                  TextFormField(
                    controller: _websiteController,
                    decoration: const InputDecoration(
                      labelText: 'Website URL (optional)',
                    ),
                    keyboardType: TextInputType.url,
                  ),
                  TextFormField(
                    controller: _costController,
                    decoration: const InputDecoration(
                      labelText: 'Cost / access information',
                    ),
                    validator: _required,
                  ),
                  if (_error != null) ...[
                    const SizedBox(height: 12),
                    Text(
                      _error!,
                      style: TextStyle(
                        color: Theme.of(context).colorScheme.error,
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: _save,
            child: const Text('Add resource'),
          ),
        ],
      );
}

IconButton _logoutAction(BuildContext context) => IconButton(
      tooltip: 'Log out',
      onPressed: () async {
        await context.read<AuthProvider>().logout();
        if (!context.mounted) return;
        Navigator.of(context).pushNamedAndRemoveUntil(
          AppRoutes.login,
          (route) => false,
        );
      },
      icon: const Icon(Icons.logout),
    );

class _DashboardError extends StatelessWidget {
  final String message;
  final VoidCallback onRetry;

  const _DashboardError({required this.message, required this.onRetry});

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

class _EmptyDashboardCard extends StatelessWidget {
  final String message;

  const _EmptyDashboardCard({required this.message});

  @override
  Widget build(BuildContext context) => Card(
        child: Padding(
          padding: const EdgeInsets.all(18),
          child: Text(message, style: Theme.of(context).textTheme.bodyMedium),
        ),
      );
}
