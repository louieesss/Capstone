import 'package:flutter/material.dart';

import '../app.dart';
import '../models/user_profile.dart';
import '../services/profile_service.dart';
import '../utils/app_theme.dart';

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  final _formKey = GlobalKey<FormState>();
  final _nameController = TextEditingController();
  final _emailController = TextEditingController();
  final _farmController = TextEditingController();
  final _locationController = TextEditingController();
  ProfileService? _profileService;
  bool _loaded = false;
  bool _saving = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_loaded) {
      return;
    }
    _profileService = AppScope.of(context).profileService;
    final profile = _profileService!.profile;
    _nameController.text = profile.name;
    _emailController.text = profile.email;
    _farmController.text = profile.farmName;
    _locationController.text = profile.location;
    _loaded = true;
  }

  Future<void> _save() async {
    if (!_formKey.currentState!.validate() || _saving) {
      return;
    }

    setState(() => _saving = true);
    final profile = UserProfile(
      name: _nameController.text,
      email: _emailController.text,
      farmName: _farmController.text,
      location: _locationController.text,
    );
    await _profileService?.save(profile);

    if (!mounted) {
      return;
    }
    setState(() => _saving = false);
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Profile saved')),
    );
  }

  @override
  void dispose() {
    _nameController.dispose();
    _emailController.dispose();
    _farmController.dispose();
    _locationController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Profile')),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 28),
          children: [
            Container(
              padding: const EdgeInsets.all(18),
              decoration: BoxDecoration(
                color: AppTheme.soil,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Row(
                children: [
                  Container(
                    width: 58,
                    height: 58,
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.12),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: const Icon(
                      Icons.person_pin_rounded,
                      color: Colors.white,
                      size: 34,
                    ),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          _nameController.text.trim().isEmpty
                              ? 'CocoScan User'
                              : _nameController.text.trim(),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: Theme.of(context).textTheme.titleLarge?.copyWith(
                                color: Colors.white,
                                fontWeight: FontWeight.w900,
                              ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          _farmController.text.trim().isEmpty
                              ? 'Local field profile'
                              : _farmController.text.trim(),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                                color: Colors.white70,
                              ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 18),
            Form(
              key: _formKey,
              child: Column(
                children: [
                  TextFormField(
                    controller: _nameController,
                    textInputAction: TextInputAction.next,
                    decoration: const InputDecoration(
                      labelText: 'Name',
                      prefixIcon: Icon(Icons.badge_outlined),
                    ),
                    validator: _required,
                    onChanged: (_) => setState(() {}),
                  ),
                  const SizedBox(height: 12),
                  TextFormField(
                    controller: _emailController,
                    keyboardType: TextInputType.emailAddress,
                    textInputAction: TextInputAction.next,
                    decoration: const InputDecoration(
                      labelText: 'Email',
                      prefixIcon: Icon(Icons.email_outlined),
                    ),
                    validator: _email,
                  ),
                  const SizedBox(height: 12),
                  TextFormField(
                    controller: _farmController,
                    textInputAction: TextInputAction.next,
                    decoration: const InputDecoration(
                      labelText: 'Farm name',
                      prefixIcon: Icon(Icons.agriculture_outlined),
                    ),
                    validator: _required,
                    onChanged: (_) => setState(() {}),
                  ),
                  const SizedBox(height: 12),
                  TextFormField(
                    controller: _locationController,
                    textInputAction: TextInputAction.done,
                    decoration: const InputDecoration(
                      labelText: 'Location',
                      prefixIcon: Icon(Icons.place_outlined),
                    ),
                    validator: _required,
                  ),
                ],
              ),
            ),
            const SizedBox(height: 18),
            FilledButton.icon(
              onPressed: _saving ? null : _save,
              icon: _saving
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.save_rounded),
              label: const Text('Save Profile'),
            ),
          ],
        ),
      ),
    );
  }

  String? _required(String? value) {
    if (value == null || value.trim().isEmpty) {
      return 'Required';
    }
    return null;
  }

  String? _email(String? value) {
    final text = value?.trim() ?? '';
    if (text.isEmpty) {
      return 'Required';
    }
    if (!text.contains('@') || !text.contains('.')) {
      return 'Enter a valid email';
    }
    return null;
  }
}
