class UserProfile {
  const UserProfile({
    required this.name,
    required this.email,
    required this.farmName,
    required this.location,
  });

  final String name;
  final String email;
  final String farmName;
  final String location;

  static const empty = UserProfile(
    name: '',
    email: '',
    farmName: '',
    location: '',
  );

  bool get isComplete {
    return name.trim().isNotEmpty &&
        email.trim().isNotEmpty &&
        farmName.trim().isNotEmpty &&
        location.trim().isNotEmpty;
  }

  UserProfile copyWith({
    String? name,
    String? email,
    String? farmName,
    String? location,
  }) {
    return UserProfile(
      name: name ?? this.name,
      email: email ?? this.email,
      farmName: farmName ?? this.farmName,
      location: location ?? this.location,
    );
  }
}
