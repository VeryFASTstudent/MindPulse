import 'package:flutter/material.dart';

import '../../core/theme.dart';
import '../../services/api_exception.dart';
import '../../services/behavior_service.dart';
import '../../widgets/primary_button.dart';

/// Returns `true` via Navigator.pop when a check-in was successfully
/// submitted, so DashboardTab knows to refresh its data on return.
class CheckinScreen extends StatefulWidget {
  const CheckinScreen({super.key});

  @override
  State<CheckinScreen> createState() => _CheckinScreenState();
}

class _CheckinScreenState extends State<CheckinScreen> {
  final BehaviorService _behaviorService = BehaviorService();

  double _stress = 5;
  double _workload = 5;
  double _sleepHours = 7;
  double _activity = 5;
  bool _isSubmitting = false;

  Future<void> _submit() async {
    setState(() => _isSubmitting = true);
    try {
      await _behaviorService.submitCheckin(
        stress: _stress.round(),
        workload: _workload.round(),
        sleepHours: _sleepHours,
        activityScore: _activity.round(),
      );
      if (mounted) Navigator.of(context).pop(true);
    } on ApiException catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(e.message)));
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text(
                'Could not submit your check-in. Check your connection and try again.'),
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _isSubmitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Daily Check-in')),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'How are things today?',
                style: Theme.of(context).textTheme.headlineMedium,
              ),
              const SizedBox(height: 4),
              Text(
                'Takes 30 seconds. Be honest — this is just for you.',
                style: Theme.of(context).textTheme.bodyMedium,
              ),
              const SizedBox(height: 32),
              _SliderField(
                label: 'Stress level',
                value: _stress,
                min: 1,
                max: 10,
                lowLabel: 'Calm',
                highLabel: 'Overwhelmed',
                onChanged: (v) => setState(() => _stress = v),
              ),
              const SizedBox(height: 28),
              _SliderField(
                label: 'Academic workload',
                value: _workload,
                min: 1,
                max: 10,
                lowLabel: 'Light',
                highLabel: 'Heavy',
                onChanged: (v) => setState(() => _workload = v),
              ),
              const SizedBox(height: 28),
              _SliderField(
                label: 'Sleep last night',
                value: _sleepHours,
                min: 0,
                max: 12,
                divisions: 24,
                lowLabel: '0h',
                highLabel: '12h',
                valueSuffix: 'h',
                onChanged: (v) => setState(() => _sleepHours = v),
              ),
              const SizedBox(height: 28),
              _SliderField(
                label: 'Physical activity',
                value: _activity,
                min: 0,
                max: 10,
                lowLabel: 'None',
                highLabel: 'A lot',
                onChanged: (v) => setState(() => _activity = v),
              ),
              const SizedBox(height: 40),
              PrimaryButton(
                label: 'Submit Check-in',
                isLoading: _isSubmitting,
                onPressed: _submit,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _SliderField extends StatelessWidget {
  final String label;
  final double value;
  final double min;
  final double max;
  final int? divisions;
  final String lowLabel;
  final String highLabel;
  final String valueSuffix;
  final ValueChanged<double> onChanged;

  const _SliderField({
    required this.label,
    required this.value,
    required this.min,
    required this.max,
    required this.lowLabel,
    required this.highLabel,
    required this.onChanged,
    this.divisions,
    this.valueSuffix = '',
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(label, style: Theme.of(context).textTheme.titleMedium),
            Text(
              '${value.toStringAsFixed(valueSuffix.isEmpty ? 0 : 1)}$valueSuffix',
              style: const TextStyle(
                color: AppTheme.primaryColor,
                fontWeight: FontWeight.bold,
                fontSize: 16,
              ),
            ),
          ],
        ),
        Slider(
          value: value,
          min: min,
          max: max,
          divisions: divisions ?? (max - min).round(),
          onChanged: onChanged,
        ),
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(lowLabel, style: Theme.of(context).textTheme.bodyMedium),
            Text(highLabel, style: Theme.of(context).textTheme.bodyMedium),
          ],
        ),
      ],
    );
  }
}
