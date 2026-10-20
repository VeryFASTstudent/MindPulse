class ConsentModel {
  final bool shareSummaryWithParent;
  final bool shareWithUniversitySupport;
  final bool allowReferralDataShare;

  const ConsentModel({
    required this.shareSummaryWithParent,
    required this.shareWithUniversitySupport,
    required this.allowReferralDataShare,
  });

  factory ConsentModel.fromJson(Map<String, dynamic> json) {
    return ConsentModel(
      shareSummaryWithParent: json['share_summary_with_parent'] as bool,
      shareWithUniversitySupport: json['share_with_university_support'] as bool,
      allowReferralDataShare: json['allow_referral_data_share'] as bool,
    );
  }

  Map<String, dynamic> toJson() => {
        'share_summary_with_parent': shareSummaryWithParent,
        'share_with_university_support': shareWithUniversitySupport,
        'allow_referral_data_share': allowReferralDataShare,
      };

  ConsentModel copyWith({
    bool? shareSummaryWithParent,
    bool? shareWithUniversitySupport,
    bool? allowReferralDataShare,
  }) {
    return ConsentModel(
      shareSummaryWithParent:
          shareSummaryWithParent ?? this.shareSummaryWithParent,
      shareWithUniversitySupport:
          shareWithUniversitySupport ?? this.shareWithUniversitySupport,
      allowReferralDataShare:
          allowReferralDataShare ?? this.allowReferralDataShare,
    );
  }
}
