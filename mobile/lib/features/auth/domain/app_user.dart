class AppUser {
  const AppUser({required this.id, required this.name, required this.email});

  final int id;
  final String name;
  final String email;

  factory AppUser.fromJson(Map<String, dynamic> json) => AppUser(
        id: json['id'] as int,
        name: json['name'] as String,
        email: json['email'] as String,
      );
}

class AuthResult {
  const AuthResult({required this.token, required this.user, this.claimedAnalyses = 0});

  final String token;
  final AppUser user;

  /// Guest analyses from this device that moved to the account.
  final int claimedAnalyses;

  factory AuthResult.fromJson(Map<String, dynamic> json) => AuthResult(
        token: json['token'] as String,
        user: AppUser.fromJson(json['user'] as Map<String, dynamic>),
        claimedAnalyses: json['claimed_analyses'] as int? ?? 0,
      );
}
