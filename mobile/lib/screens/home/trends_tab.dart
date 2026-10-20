import 'package:flutter/material.dart';

import '../../models/checkin_model.dart';
import '../../models/daily_sentiment_model.dart';
import '../../services/api_exception.dart';
import '../../services/behavior_service.dart';
import '../../services/sentiment_service.dart';

class TrendsTab extends StatefulWidget {
  const TrendsTab({super.key});

  @override
  State<TrendsTab> createState() => _TrendsTabState();
}

class _TrendsTabState extends State<TrendsTab> {
  final BehaviorService _behaviorService = BehaviorService();
  final SentimentService _sentimentService = SentimentService();
  int _days = 30;
  bool _loading = true;
  String? _error;
  List<CheckinModel> _checkins = [];
  List<DailySentimentModel> _sentiments = [];

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
        _behaviorService.getHistory(days: _days),
        _sentimentService.getDailySentiment(days: _days),
      ]);
      if (!mounted) return;
      setState(() {
        _checkins = results[0] as List<CheckinModel>;
        _sentiments = results[1] as List<DailySentimentModel>;
      });
    } on ApiException catch (error) {
      if (mounted) {
        setState(() => _error = error.message);
      }
    } catch (_) {
      if (mounted) {
        setState(() => _error = 'Could not load trends. Please try again.');
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Your trends')),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(20),
          children: [
            Text('Patterns over time',
                style: Theme.of(context).textTheme.headlineMedium),
            const SizedBox(height: 6),
            Text(
              'These voluntary check-ins and chat signals are for reflection, not diagnosis.',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            const SizedBox(height: 16),
            SegmentedButton<int>(
              segments: const [
                ButtonSegment(value: 7, label: Text('7 days')),
                ButtonSegment(value: 30, label: Text('30 days')),
                ButtonSegment(value: 90, label: Text('90 days')),
              ],
              selected: {_days},
              onSelectionChanged: (selected) {
                setState(() => _days = selected.first);
                _load();
              },
            ),
            const SizedBox(height: 20),
            if (_loading)
              const Padding(
                padding: EdgeInsets.all(32),
                child: Center(child: CircularProgressIndicator()),
              )
            else if (_error != null)
              _ErrorCard(message: _error!, onRetry: _load)
            else ...[
              _TrendCard(
                title: 'Self-rated stress',
                subtitle: 'Daily check-ins · scale 1–10',
                color: const Color(0xFFE5A33D),
                barMaximum: 1,
                formatValue: (value) =>
                    '${(value * 10).toStringAsFixed(1)} / 10',
                values: _checkins
                    .map((item) =>
                        _TrendPoint(item.date, item.selfRatedStress / 10))
                    .toList(),
                emptyMessage: 'No check-ins in this period yet.',
              ),
              const SizedBox(height: 14),
              _TrendCard(
                title: 'Academic workload',
                subtitle: 'Daily check-ins · scale 1–10',
                color: const Color(0xFF5B6EE8),
                barMaximum: 1,
                formatValue: (value) =>
                    '${(value * 10).toStringAsFixed(1)} / 10',
                values: _checkins
                    .map((item) => _TrendPoint(item.date, item.workload / 10))
                    .toList(),
                emptyMessage: 'No check-ins in this period yet.',
              ),
              const SizedBox(height: 14),
              _TrendCard(
                title: 'Sleep',
                subtitle: 'Daily check-ins · hours per night',
                color: const Color(0xFF7868C8),
                barMaximum: 12,
                formatValue: (value) => '${value.toStringAsFixed(1)} hrs',
                values: _checkins
                    .map((item) => _TrendPoint(item.date, item.sleepHours))
                    .toList(),
                emptyMessage: 'No check-ins in this period yet.',
              ),
              const SizedBox(height: 14),
              _TrendCard(
                title: 'Physical activity',
                subtitle: 'Daily check-ins · self-rating scale 1–10',
                color: const Color(0xFF48A878),
                barMaximum: 1,
                formatValue: (value) =>
                    '${(value * 10).toStringAsFixed(1)} / 10',
                values: _checkins
                    .map((item) =>
                        _TrendPoint(item.date, item.activityScore / 10))
                    .toList(),
                emptyMessage: 'No check-ins in this period yet.',
              ),
              const SizedBox(height: 14),
              _TrendCard(
                title: 'Chat sentiment',
                subtitle: 'Automated estimate · −1 negative to +1 positive',
                color: const Color(0xFF35A88E),
                barMaximum: 1,
                formatValue: (value) => (value * 2 - 1).toStringAsFixed(2),
                values: _sentiments
                    .map((item) =>
                        _TrendPoint(item.date, (item.averageSentiment + 1) / 2))
                    .toList(),
                emptyMessage:
                    'No sentiment results yet. Chat signals may take a moment to appear.',
              ),
              const SizedBox(height: 14),
              _TrendCard(
                title: 'Chat engagement',
                subtitle: 'Processed chat messages per day',
                color: const Color(0xFF38A4B8),
                barMaximum: _sentiments
                    .fold<int>(
                      0,
                      (maximum, item) => item.messageCount > maximum
                          ? item.messageCount
                          : maximum,
                    )
                    .toDouble(),
                formatValue: (value) => '${value.toStringAsFixed(0)} messages',
                values: _sentiments
                    .map((item) =>
                        _TrendPoint(item.date, item.messageCount.toDouble()))
                    .toList(),
                emptyMessage: 'No chat activity in this period yet.',
              ),
            ],
            const SizedBox(height: 14),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Text(
                  'Sentiment is an imperfect model estimate. Missing data is not evidence that everything is fine. '
                  'If you are concerned, consider reaching out to someone you trust or using Support.',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _TrendPoint {
  final DateTime date;
  final double value;

  const _TrendPoint(this.date, this.value);
}

class _TrendCard extends StatelessWidget {
  final String title;
  final String subtitle;
  final Color color;
  final List<_TrendPoint> values;
  final String emptyMessage;
  final double barMaximum;
  final String Function(double value) formatValue;

  const _TrendCard({
    required this.title,
    required this.subtitle,
    required this.color,
    required this.values,
    required this.emptyMessage,
    required this.barMaximum,
    required this.formatValue,
  });

  @override
  Widget build(BuildContext context) {
    final mean = values.isEmpty
        ? null
        : values.map((point) => point.value).reduce((a, b) => a + b) /
            values.length;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 4),
            Text(subtitle, style: Theme.of(context).textTheme.bodySmall),
            if (mean != null) ...[
              const SizedBox(height: 8),
              Text(
                'Average: ${formatValue(mean)}',
                style: TextStyle(color: color, fontWeight: FontWeight.w600),
              ),
              const SizedBox(height: 14),
              SizedBox(
                height: 92,
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: values.map((point) {
                    final normalized = barMaximum <= 0
                        ? 0.04
                        : (point.value / barMaximum)
                            .clamp(0.04, 1.0)
                            .toDouble();
                    return Expanded(
                      child: Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 2),
                        child: Tooltip(
                          message: '${point.date.month}/${point.date.day}: '
                              '${formatValue(point.value)}',
                          child: FractionallySizedBox(
                            heightFactor: normalized,
                            alignment: Alignment.bottomCenter,
                            child: DecoratedBox(
                              decoration: BoxDecoration(
                                color: color.withValues(alpha: 0.75),
                                borderRadius: BorderRadius.circular(4),
                              ),
                              child: const SizedBox.expand(),
                            ),
                          ),
                        ),
                      ),
                    );
                  }).toList(),
                ),
              ),
              const SizedBox(height: 6),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(_dateLabel(values.first.date),
                      style: Theme.of(context).textTheme.bodySmall),
                  Text(_dateLabel(values.last.date),
                      style: Theme.of(context).textTheme.bodySmall),
                ],
              ),
            ] else ...[
              const SizedBox(height: 12),
              Text(emptyMessage, style: Theme.of(context).textTheme.bodyMedium),
            ],
          ],
        ),
      ),
    );
  }

  String _dateLabel(DateTime date) => '${date.month}/${date.day}';
}

class _ErrorCard extends StatelessWidget {
  final String message;
  final VoidCallback onRetry;

  const _ErrorCard({required this.message, required this.onRetry});

  @override
  Widget build(BuildContext context) {
    return Card(
      child: ListTile(
        title: Text(message),
        trailing: IconButton(
          onPressed: onRetry,
          icon: const Icon(Icons.refresh),
          tooltip: 'Retry',
        ),
      ),
    );
  }
}
