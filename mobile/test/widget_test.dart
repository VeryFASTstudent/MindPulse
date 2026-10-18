// This is a basic Flutter widget test.
//
// To perform an interaction with a widget in your test, use the WidgetTester
// utility in the flutter_test package. For example, you can send tap and scroll
// gestures. You can also use WidgetTester to find child widgets in the widget
// tree, read text, and verify that the values of widget properties are correct.

import 'package:flutter_test/flutter_test.dart';

import 'package:mindpulse/models/consent_model.dart';
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
    expect(ConsentModel.fromJson(consent.toJson()).shareSummaryWithParent, isFalse);
  });

  test('risk status model represents a student awaiting their first check-in', () {
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
}
