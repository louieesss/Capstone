import 'package:shared_preferences/shared_preferences.dart';

import '../models/user_profile.dart';

class ProfileService {
  static const _nameKey = 'profile_name';
  static const _emailKey = 'profile_email';
  static const _farmNameKey = 'profile_farm_name';
  static const _locationKey = 'profile_location';

  UserProfile _profile = UserProfile.empty;

  UserProfile get profile => _profile;

  Future<void> load() async {
    final prefs = await SharedPreferences.getInstance();
    _profile = UserProfile(
      name: prefs.getString(_nameKey) ?? '',
      email: prefs.getString(_emailKey) ?? '',
      farmName: prefs.getString(_farmNameKey) ?? '',
      location: prefs.getString(_locationKey) ?? '',
    );
  }

  Future<UserProfile> save(UserProfile profile) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_nameKey, profile.name.trim());
    await prefs.setString(_emailKey, profile.email.trim());
    await prefs.setString(_farmNameKey, profile.farmName.trim());
    await prefs.setString(_locationKey, profile.location.trim());
    _profile = profile.copyWith(
      name: profile.name.trim(),
      email: profile.email.trim(),
      farmName: profile.farmName.trim(),
      location: profile.location.trim(),
    );
    return _profile;
  }
}
