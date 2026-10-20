// This is a basic Flutter widget test.
//
// To perform an interaction with a widget in your test, use the WidgetTester
// utility in the flutter_test package. For example, you can send tap and scroll
// gestures. You can also use WidgetTester to find child widgets in the widget
// tree, read text, and verify that the values of widget properties are correct.

import 'package:flutter_test/flutter_test.dart';

import 'package:mindpulse/models/consent_model.dart';
import 'package:mindpulse/models/daily_sentiment_model.dart';
import 'package:mindpulse/models/referral_model.dart';
import 'package:mindpulse/models/risk_status_model.dart';

void main() {
  test('consent model updates a single permission', () {
    const consent = ConsentModel(
      shareSummaryWithParent: false,
      shareWithUniversitySupport: false,
      allowReferralDataShare: false,
    );
    final updated = consent.copyWith(shareSummaryWithParent: true);

    expect(updated.shareSummaryWithParent, isTrue);
    expect(updated.shareWithUniversitySupport, isFalse);
    expect(updated.allowReferralDataShare, isFalse);
    expect(ConsentModel.fromJson(consent.toJson()).shareSummaryWithParent,
        isFalse);
  });

  test('risk status model represents a student awaiting their first check-in',
      () {
    final status = RiskStatusModel.fromJson({
      'status': 'awaiting_checkin',
      'risk_level': 'INSUFFICIENT_DATA',
      'message': "Complete today's check-in to see your well-being status.",
    });

    expect(status.status, 'awaiting_checkin');
    expect(status.riskLevel, 'INSUFFICIENT_DATA');
    expect(status.requiredSampleSize, 5);
    expect(status.weightedScore, isNull);
  });

  test('daily sentiment model parses the API trend shape', () {
    final result = DailySentimentModel.fromJson({
      'date': '2026-10-20T00:00:00',
      'avg_sentiment': -0.25,
      'message_count': 3,
    });

    expect(result.averageSentiment, -0.25);
    expect(result.messageCount, 3);
  });

  test('referral model parses a student support request', () {
    final result = ReferralModel.fromJson({
      '_id': 'request-1',
      'counselor_id': 'counselor-1',
      'status': 'requested',
      'requested_at': '2026-10-20T00:00:00Z',
      'updated_at': '2026-10-20T00:00:00Z',
      'student_consent_confirmed': true,
    });

    expect(result.status, 'requested');
    expect(result.counselorId, 'counselor-1');
  });
}
