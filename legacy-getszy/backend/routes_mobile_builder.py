import uuid
import os
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_admin
from db import db
from llm_provider import chat_completion

router = APIRouter(prefix='/admin/mobile-builder', tags=['mobile-builder'])


def _now():
    return datetime.now(timezone.utc).isoformat()


def _uid():
    return str(uuid.uuid4())


MOBILE_TEMPLATES = {
    'ecommerce': {
        'name': 'E-Commerce',
        'description': 'Full-featured mobile commerce app with products, cart, checkout, orders, payments, and user profiles',
        'platforms': ['flutter', 'react_native'],
        'features': ['auth', 'push_notifications', 'payments', 'offline_mode', 'deep_links', 'splash_screen', 'onboarding', 'camera'],
        'tech_stack': {'flutter': 'Provider + Dio + Hive', 'react_native': 'Context + Axios + AsyncStorage'},
        'screens': ['splash', 'onboarding', 'login', 'signup', 'home', 'product_list', 'product_detail', 'cart', 'checkout', 'order_history', 'profile', 'settings', 'search', 'wishlist'],
    },
    'social': {
        'name': 'Social',
        'description': 'Social networking app with feeds, profiles, messaging, notifications, and media sharing',
        'platforms': ['flutter', 'react_native'],
        'features': ['auth', 'push_notifications', 'camera', 'chat', 'video', 'file_upload', 'deep_links', 'splash_screen', 'onboarding'],
        'tech_stack': {'flutter': 'Riverpod + Dio + Hive', 'react_native': 'Context + Axios + AsyncStorage'},
        'screens': ['splash', 'onboarding', 'login', 'signup', 'feed', 'profile', 'messages', 'chat', 'notifications', 'settings', 'camera', 'media_preview', 'search'],
    },
    'blog': {
        'name': 'Blog',
        'description': 'Content-focused blog app with articles, categories, comments, bookmarks, and offline reading',
        'platforms': ['flutter', 'react_native'],
        'features': ['auth', 'push_notifications', 'offline_mode', 'deep_links', 'splash_screen', 'onboarding'],
        'tech_stack': {'flutter': 'Provider + Dio + Hive', 'react_native': 'Context + Axios + AsyncStorage'},
        'screens': ['splash', 'onboarding', 'login', 'home', 'article_list', 'article_detail', 'categories', 'bookmarks', 'profile', 'settings', 'search', 'comments'],
    },
    'portfolio': {
        'name': 'Portfolio',
        'description': 'Professional portfolio app with project showcase, blog, contact form, and analytics',
        'platforms': ['flutter', 'react_native'],
        'features': ['auth', 'deep_links', 'splash_screen', 'onboarding'],
        'tech_stack': {'flutter': 'Provider + Dio', 'react_native': 'Context + Axios'},
        'screens': ['splash', 'home', 'projects', 'project_detail', 'blog', 'about', 'contact', 'settings'],
    },
    'crm': {
        'name': 'CRM',
        'description': 'Customer Relationship Management with contacts, deals, pipeline, tasks, and activity tracking',
        'platforms': ['flutter', 'react_native'],
        'features': ['auth', 'push_notifications', 'camera', 'file_upload', 'offline_mode', 'deep_links', 'splash_screen'],
        'tech_stack': {'flutter': 'Provider + Dio + Hive', 'react_native': 'Context + Axios + AsyncStorage'},
        'screens': ['splash', 'login', 'dashboard', 'contacts', 'contact_detail', 'deals', 'deal_detail', 'pipeline', 'tasks', 'activities', 'profile', 'settings', 'search'],
    },
    'booking': {
        'name': 'Booking',
        'description': 'Appointment and booking app with services, calendar, slots, payments, and reminders',
        'platforms': ['flutter', 'react_native'],
        'features': ['auth', 'push_notifications', 'location', 'payments', 'deep_links', 'splash_screen', 'onboarding'],
        'tech_stack': {'flutter': 'Provider + Dio', 'react_native': 'Context + Axios'},
        'screens': ['splash', 'onboarding', 'login', 'signup', 'home', 'services', 'service_detail', 'calendar', 'slot_selection', 'booking_confirmation', 'my_bookings', 'profile', 'settings', 'payment'],
    },
    'food': {
        'name': 'Food Delivery',
        'description': 'Food ordering app with restaurants, menus, cart, orders, tracking, and reviews',
        'platforms': ['flutter', 'react_native'],
        'features': ['auth', 'push_notifications', 'location', 'payments', 'camera', 'deep_links', 'splash_screen', 'onboarding'],
        'tech_stack': {'flutter': 'Riverpod + Dio + Hive', 'react_native': 'Context + Axios + AsyncStorage'},
        'screens': ['splash', 'onboarding', 'login', 'signup', 'home', 'restaurant_list', 'restaurant_detail', 'menu', 'cart', 'checkout', 'order_tracking', 'order_history', 'reviews', 'profile', 'settings', 'search', 'location'],
    },
    'fitness': {
        'name': 'Fitness',
        'description': 'Fitness tracking app with workouts, exercises, progress, nutrition, and social challenges',
        'platforms': ['flutter', 'react_native'],
        'features': ['auth', 'push_notifications', 'camera', 'location', 'offline_mode', 'deep_links', 'splash_screen', 'onboarding'],
        'tech_stack': {'flutter': 'Provider + Dio + Hive', 'react_native': 'Context + Axios + AsyncStorage'},
        'screens': ['splash', 'onboarding', 'login', 'signup', 'home', 'workouts', 'workout_detail', 'exercises', 'progress', 'nutrition', 'challenges', 'profile', 'settings', 'timer'],
    },
}

MOBILE_FEATURES = {
    'auth': {'name': 'Authentication', 'description': 'Login, signup, forgot password, social auth'},
    'push_notifications': {'name': 'Push Notifications', 'description': 'Firebase Cloud Messaging integration'},
    'camera': {'name': 'Camera', 'description': 'Photo/video capture and gallery access'},
    'location': {'name': 'Location', 'description': 'GPS tracking and map integration'},
    'payments': {'name': 'Payments', 'description': 'Stripe/PayPal payment processing'},
    'offline_mode': {'name': 'Offline Mode', 'description': 'Local data caching and offline support'},
    'deep_links': {'name': 'Deep Links', 'description': 'Universal links and deep linking'},
    'splash_screen': {'name': 'Splash Screen', 'description': 'Animated splash screen on launch'},
    'onboarding': {'name': 'Onboarding', 'description': 'User onboarding tutorial screens'},
    'chat': {'name': 'Chat', 'description': 'Real-time messaging with WebSocket'},
    'video': {'name': 'Video', 'description': 'Video playback and streaming'},
    'file_upload': {'name': 'File Upload', 'description': 'File/image upload to server'},
}

MOBILE_PLATFORMS = {
    'flutter': {'name': 'Flutter', 'sdk_version': '3.22.0', 'dart_version': '3.4.0', 'description': 'Cross-platform UI toolkit by Google'},
    'react_native': {'name': 'React Native', 'sdk_version': '0.74.0', 'description': 'Cross-platform mobile framework by Meta'},
}


class MobileProjectIn(BaseModel):
    name: str
    platform: str = 'flutter'
    template: str = 'ecommerce'
    features: List[str] = ['auth', 'splash_screen', 'onboarding']
    backend_url: str = 'http://localhost:8000'


class AIEnhanceIn(BaseModel):
    file_path: str
    instructions: str = 'Improve code quality, add error handling, and follow best practices'


class AddScreenIn(BaseModel):
    name: str
    fields: List[Dict[str, str]]
    layout: str = 'list'


class AddEndpointIn(BaseModel):
    endpoint_path: str
    method: str = 'GET'
    name: str
    fields: Optional[List[Dict[str, str]]] = None


class FileUpdateIn(BaseModel):
    content: str


# ── Templates & Platforms ──

@router.get('/templates')
async def list_templates(_=Depends(get_current_admin)):
    result = []
    for key, tpl in MOBILE_TEMPLATES.items():
        result.append({
            'id': key,
            'name': tpl['name'],
            'description': tpl['description'],
            'platforms': tpl['platforms'],
            'features': tpl['features'],
            'tech_stack': tpl['tech_stack'],
            'screen_count': len(tpl['screens']),
            'screens': tpl['screens'],
        })
    return result


@router.get('/platforms')
async def list_platforms(_=Depends(get_current_admin)):
    return MOBILE_PLATFORMS


@router.get('/features')
async def list_features(_=Depends(get_current_admin)):
    return MOBILE_FEATURES


# ── Project Generation ──

def _generate_flutter_project(name: str, template: str, features: list, backend_url: str) -> dict:
    tpl = MOBILE_TEMPLATES.get(template, MOBILE_TEMPLATES['ecommerce'])
    safe_name = name.replace(' ', '_').replace('-', '_').lower()
    pub_name = name.replace(' ', '_').replace('-', '_').lower()

    files = {}

    files['pubspec.yaml'] = f'''name: {pub_name}
description: {name} - Generated by Getszy Mobile Builder
version: 1.0.0+1

environment:
  sdk: '>=3.4.0 <4.0.0'

dependencies:
  flutter:
    sdk: flutter
  dio: ^5.4.0
  provider: ^6.1.0
  hive: ^2.2.3
  hive_flutter: ^1.1.0
  shared_preferences: ^2.2.2
  flutter_secure_storage: ^9.0.0
  cached_network_image: ^3.3.0
  flutter_svg: ^2.0.9
  intl: ^0.19.0
  google_fonts: ^6.1.0
  shimmer: ^3.0.0
  pull_to_refresh: ^2.0.0
  flutter_staggered_animations: ^1.1.1
  connectivity_plus: ^5.0.2
  path_provider: ^2.1.1
  image_picker: ^1.0.4
  url_launcher: ^6.2.1
  flutter_local_notifications: ^16.1.0
  firebase_core: ^2.24.0
  firebase_messaging: ^14.7.0
{"".join(f'  geolocator: ^11.0.0\\n  permission_handler: ^11.1.0\\n' if f == "location" else "" for f in features)}
{"".join(f'  flutter_polyline_points: ^2.0.0\\n' if f == "location" else "" for f in features)}
{"".join(f'  stripe_payment: ^3.1.0\\n' if f == "payments" else "" for f in features)}
{"".join(f'  video_player: ^2.8.1\\n' if f == "video" else "" for f in features)}
{"".join(f'  web_socket_channel: ^2.4.0\\n' if f == "chat" else "" for f in features)}

dev_dependencies:
  flutter_test:
    sdk: flutter
  hive_generator: ^2.0.1
  build_runner: ^2.4.7
  flutter_lints: ^3.0.1

flutter:
  uses-material-design: true
  assets:
    - assets/images/
    - assets/icons/
'''

    files['lib/main.dart'] = f'''import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:hive_flutter/hive_flutter.dart';
import 'app.dart';
import 'services/api_service.dart';
import 'services/auth_service.dart';
import 'services/storage_service.dart';
import 'providers/theme_provider.dart';

void main() async {{
  WidgetsFlutterBinding.ensureInitialized();
  await Hive.initFlutter();
  await Hive.openBox('cache');
  await Hive.openBox('settings');

  runApp(
    MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => ThemeProvider()),
        Provider(create: (_) => ApiService(baseUrl: '{backend_url}')),
        ChangeNotifierProvider(create: (_) => AuthService()),
        Provider(create: (_) => StorageService()),
      ],
      child: const {safe_name.title().replace(" ", "")}App(),
    ),
  );
}}
'''

    files['lib/app.dart'] = f'''import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'providers/theme_provider.dart';
import 'screens/splash_screen.dart';
import 'theme/app_theme.dart';

class {safe_name.title().replace(" ", "")}App extends StatelessWidget {{
  const {{super.key}};

  @override
  Widget build(BuildContext context) {{
    final themeProvider = Provider.of<ThemeProvider>(context);
    return MaterialApp(
      title: '{name}',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.lightTheme,
      darkTheme: AppTheme.darkTheme,
      themeMode: themeProvider.themeMode,
      home: const SplashScreen(),
    );
  }}
}}
'''

    files['lib/theme/app_theme.dart'] = f'''import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class AppTheme {{
  static final lightTheme = ThemeData(
    brightness: Brightness.light,
    primarySwatch: Colors.blue,
    scaffoldBackgroundColor: Colors.white,
    textTheme: GoogleFonts.interTextTheme(),
    appBarTheme: const AppBarTheme(elevation: 0, centerTitle: true),
    cardTheme: CardTheme(elevation: 2, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12))),
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8))),
    ),
  );

  static final darkTheme = ThemeData(
    brightness: Brightness.dark,
    primarySwatch: Colors.blue,
    scaffoldBackgroundColor: const Color(0xFF121212),
    textTheme: GoogleFonts.interTextTheme(ThemeData.dark().textTheme),
    appBarTheme: const AppBarTheme(elevation: 0, centerTitle: true),
  );
}}
'''

    files['lib/services/api_service.dart'] = f'''import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class ApiService {{
  final Dio _dio;
  final FlutterSecureStorage _storage = const FlutterSecureStorage();
  final String baseUrl;

  ApiService({{required this.baseUrl}}) : _dio = Dio(BaseOptions(baseUrl: baseUrl, connectTimeout: const Duration(seconds: 30), receiveTimeout: const Duration(seconds: 30))) {{
    _dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) async {{
        final token = await _storage.read(key: 'auth_token');
        if (token != null) options.headers['Authorization'] = 'Bearer $token';
        handler.next(options);
      }},
      onError: (error, handler) {{
        if (error.response?.statusCode == 401) {{
          _storage.delete(key: 'auth_token');
        }}
        handler.next(error);
      }},
    ));
  }}

  Dio get dio => _dio;

  Future<Response> get(String path, {{Map<String, dynamic>? query}}) => _dio.get(path, queryParameters: query);
  Future<Response> post(String path, {{dynamic data}}) => _dio.post(path, data: data);
  Future<Response> put(String path, {{dynamic data}}) => _dio.put(path, data: data);
  Future<Response> patch(String path, {{dynamic data}}) => _dio.patch(path, data: data);
  Future<Response> delete(String path) => _dio.delete(path);
}}
'''

    files['lib/services/auth_service.dart'] = '''import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../services/api_service.dart';

class AuthService extends ChangeNotifier {
  final FlutterSecureStorage _storage = const FlutterSecureStorage();
  bool _isLoggedIn = false;
  Map<String, dynamic>? _user;

  bool get isLoggedIn => _isLoggedIn;
  Map<String, dynamic>? get user => _user;

  Future<void> login(String email, String password) async {
    // Implementation
    _isLoggedIn = true;
    notifyListeners();
  }

  Future<void> signup(String name, String email, String password) async {
    // Implementation
    _isLoggedIn = true;
    notifyListeners();
  }

  Future<void> logout() async {
    await _storage.delete(key: 'auth_token');
    _isLoggedIn = false;
    _user = null;
    notifyListeners();
  }

  Future<void> checkAuth() async {
    final token = await _storage.read(key: 'auth_token');
    _isLoggedIn = token != null;
    notifyListeners();
  }
}
'''

    files['lib/services/storage_service.dart'] = '''import 'package:hive/hive.dart';

class StorageService {
  final Box _box = Hive.box('cache');

  Future<void> save(String key, dynamic value) async => _box.put(key, value);
  dynamic get(String key, {dynamic defaultValue}) => _box.get(key, defaultValue: defaultValue);
  Future<void> remove(String key) async => _box.delete(key);
  Future<void> clear() async => _box.clear();
}
'''

    files['lib/providers/theme_provider.dart'] = '''import 'package:flutter/material.dart';
import 'package:hive/hive.dart';

class ThemeProvider extends ChangeNotifier {
  final Box _settings = Hive.box('settings');

  ThemeMode get themeMode {
    final isDark = _settings.get('dark_mode', defaultValue: false);
    return isDark ? ThemeMode.dark : ThemeMode.light;
  }

  void toggleTheme() {
    final isDark = _settings.get('dark_mode', defaultValue: false);
    _settings.put('dark_mode', !isDark);
    notifyListeners();
  }
}
'''

    files['lib/models/base_model.dart'] = '''abstract class BaseModel {
  Map<String, dynamic> toJson();
  factory BaseModel.fromJson(Map<String, dynamic> json) => throw UnimplementedError();
}
'''

    for screen in tpl['screens']:
        screen_name = ''.join(w.capitalize() for w in screen.split('_'))
        files[f'lib/screens/{screen}.dart'] = _generate_flutter_screen(screen, screen_name, template, features)

    files['lib/widgets/custom_button.dart'] = '''import 'package:flutter/material.dart';

class CustomButton extends StatelessWidget {
  final String text;
  final VoidCallback onPressed;
  final bool isLoading;
  final Color? color;

  const CustomButton({super.key, required this.text, required this.onPressed, this.isLoading = false, this.color});

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: double.infinity,
      height: 48,
      child: ElevatedButton(
        onPressed: isLoading ? null : onPressed,
        style: ElevatedButton.styleFrom(backgroundColor: color),
        child: isLoading
            ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
            : Text(text, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
      ),
    );
  }
}
'''

    files['lib/widgets/custom_text_field.dart'] = '''import 'package:flutter/material.dart';

class CustomTextField extends StatelessWidget {
  final String label;
  final TextEditingController? controller;
  final bool obscureText;
  final TextInputType? keyboardType;
  final String? Function(String?)? validator;
  final Widget? suffixIcon;

  const CustomTextField({super.key, required this.label, this.controller, this.obscureText = false, this.keyboardType, this.validator, this.suffixIcon});

  @override
  Widget build(BuildContext context) {
    return TextFormField(
      controller: controller,
      obscureText: obscureText,
      keyboardType: keyboardType,
      validator: validator,
      decoration: InputDecoration(
        labelText: label,
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
        suffixIcon: suffixIcon,
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      ),
    );
  }
}
'''

    files['lib/widgets/loading_widget.dart'] = '''import 'package:flutter/material.dart';

class LoadingWidget extends StatelessWidget {
  final String? message;
  const LoadingWidget({super.key, this.message});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const CircularProgressIndicator(),
          if (message != null) ...[
            const SizedBox(height: 16),
            Text(message!, style: Theme.of(context).textTheme.bodyMedium),
          ],
        ],
      ),
    );
  }
}
'''

    files['lib/widgets/empty_state.dart'] = '''import 'package:flutter/material.dart';

class EmptyState extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;
  final String? actionText;
  final VoidCallback? onAction;

  const EmptyState({super.key, required this.icon, required this.title, required this.subtitle, this.actionText, this.onAction});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, size: 64, color: Colors.grey[400]),
            const SizedBox(height: 16),
            Text(title, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            Text(subtitle, textAlign: TextAlign.center, style: TextStyle(color: Colors.grey[600])),
            if (actionText != null) ...[
              const SizedBox(height: 24),
              ElevatedButton(onPressed: onAction, child: Text(actionText!)),
            ],
          ],
        ),
      ),
    );
  }
}
'''

    files['README.md'] = f'''# {name}

Generated by Getszy Mobile Builder

## Platform
Flutter

## Template
{tpl['name']}

## Features
{", ".join(features)}

## Getting Started
```bash
flutter pub get
flutter run
```

## Backend
API: {backend_url}
'''

    return files


def _generate_flutter_screen(screen: str, screen_name: str, template: str, features: list) -> str:
    screen_configs = {
        'splash': '''import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/auth_service.dart';
import 'home_screen.dart';
import 'onboarding_screen.dart';

class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});
  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen> {
  @override
  void initState() {
    super.initState();
    _navigate();
  }

  Future<void> _navigate() async {
    await Future.delayed(const Duration(seconds: 2));
    if (!mounted) return;
    final auth = Provider.of<AuthService>(context, listen: false);
    await auth.checkAuth();
    if (!mounted) return;
    Navigator.pushReplacement(
      context,
      MaterialPageRoute(builder: (_) => auth.isLoggedIn ? const HomeScreen() : const OnboardingScreen()),
    );
  }

  @override
  Widget build(BuildContext context) {
    return const Scaffold(
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.apps, size: 80),
            SizedBox(height: 16),
            CircularProgressIndicator(),
          ],
        ),
      ),
    );
  }
}''',
        'onboarding': '''import 'package:flutter/material.dart';

class OnboardingScreen extends StatefulWidget {
  const OnboardingScreen({super.key});
  @override
  State<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends State<OnboardingScreen> {
  final PageController _controller = PageController();
  int _current = 0;

  final _pages = [
    const _OnboardingPage(title: 'Welcome', subtitle: 'Discover amazing features', icon: Icons.wave_motion_sharp),
    const _OnboardingPage(title: 'Explore', subtitle: 'Browse through our catalog', icon: Icons.explore),
    const _OnboardingPage(title: 'Get Started', subtitle: 'Create your account today', icon: Icons.rocket_launch),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Column(
          children: [
            Expanded(
              child: PageView.builder(
                controller: _controller,
                itemCount: _pages.length,
                onPageChanged: (i) => setState(() => _current = i),
                itemBuilder: (_, i) => _pages[i],
              ),
            ),
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: List.generate(_pages.length, (i) => Container(
                margin: const EdgeInsets.all(4),
                width: _current == i ? 24 : 8,
                height: 8,
                decoration: BoxDecoration(color: _current == i ? Theme.of(context).primaryColor : Colors.grey[300], borderRadius: BorderRadius.circular(4)),
              )),
            ),
            const SizedBox(height: 24),
            Padding(
              padding: const EdgeInsets.all(16),
              child: SizedBox(
                width: double.infinity,
                height: 48,
                child: ElevatedButton(
                  onPressed: () {
                    if (_current < _pages.length - 1) {
                      _controller.nextPage(duration: const Duration(milliseconds: 300), curve: Curves.easeInOut);
                    } else {
                      Navigator.pushReplacementNamed(context, '/login');
                    }
                  },
                  child: Text(_current == _pages.length - 1 ? 'Get Started' : 'Next'),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _OnboardingPage extends StatelessWidget {
  final String title;
  final String subtitle;
  final IconData icon;
  const _OnboardingPage({required this.title, required this.subtitle, required this.icon});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(32),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(icon, size: 120, color: Theme.of(context).primaryColor),
          const SizedBox(height: 32),
          Text(title, style: const TextStyle(fontSize: 28, fontWeight: FontWeight.bold)),
          const SizedBox(height: 12),
          Text(subtitle, textAlign: TextAlign.center, style: TextStyle(fontSize: 16, color: Colors.grey[600])),
        ],
      ),
    );
  }
}''',
        'login': '''import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/auth_service.dart';
import '../widgets/custom_button.dart';
import '../widgets/custom_text_field.dart';
import 'home_screen.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});
  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _isLoading = false;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Form(
            key: _formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const SizedBox(height: 40),
                const Text('Welcome Back', style: TextStyle(fontSize: 28, fontWeight: FontWeight.bold)),
                const SizedBox(height: 8),
                Text('Sign in to continue', style: TextStyle(color: Colors.grey[600])),
                const SizedBox(height: 32),
                CustomTextField(label: 'Email', controller: _emailController, keyboardType: TextInputType.emailAddress, validator: (v) => v?.isEmpty ?? true ? 'Required' : null),
                const SizedBox(height: 16),
                CustomTextField(label: 'Password', controller: _passwordController, obscureText: true, validator: (v) => v?.isEmpty ?? true ? 'Required' : null),
                const SizedBox(height: 8),
                Align(alignment: Alignment.centerRight, child: TextButton(onPressed: () {}, child: const Text('Forgot Password?'))),
                const SizedBox(height: 16),
                CustomButton(
                  text: 'Sign In',
                  isLoading: _isLoading,
                  onPressed: () async {
                    if (!_formKey.currentState!.validate()) return;
                    setState(() => _isLoading = true);
                    try {
                      await Provider.of<AuthService>(context, listen: false).login(_emailController.text, _passwordController.text);
                      if (mounted) Navigator.pushReplacement(context, MaterialPageRoute(builder: (_) => const HomeScreen()));
                    } catch (e) {
                      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
                    }
                    if (mounted) setState(() => _isLoading = false);
                  },
                ),
                const SizedBox(height: 16),
                Center(child: TextButton(onPressed: () => Navigator.pushNamed(context, '/signup'), child: const Text("Don't have an account? Sign Up"))),
              ],
            ),
          ),
        ),
      ),
    );
  }
}''',
        'signup': '''import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/auth_service.dart';
import '../widgets/custom_button.dart';
import '../widgets/custom_text_field.dart';

class SignupScreen extends StatefulWidget {
  const SignupScreen({super.key});
  @override
  State<SignupScreen> createState() => _SignupScreenState();
}

class _SignupScreenState extends State<SignupScreen> {
  final _formKey = GlobalKey<FormState>();
  final _nameController = TextEditingController();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _isLoading = false;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Form(
            key: _formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const SizedBox(height: 40),
                const Text('Create Account', style: TextStyle(fontSize: 28, fontWeight: FontWeight.bold)),
                const SizedBox(height: 32),
                CustomTextField(label: 'Full Name', controller: _nameController, validator: (v) => v?.isEmpty ?? true ? 'Required' : null),
                const SizedBox(height: 16),
                CustomTextField(label: 'Email', controller: _emailController, keyboardType: TextInputType.emailAddress, validator: (v) => v?.isEmpty ?? true ? 'Required' : null),
                const SizedBox(height: 16),
                CustomTextField(label: 'Password', controller: _passwordController, obscureText: true, validator: (v) => (v?.length ?? 0) < 6 ? 'Min 6 characters' : null),
                const SizedBox(height: 24),
                CustomButton(
                  text: 'Sign Up',
                  isLoading: _isLoading,
                  onPressed: () async {
                    if (!_formKey.currentState!.validate()) return;
                    setState(() => _isLoading = true);
                    try {
                      await Provider.of<AuthService>(context, listen: false).signup(_nameController.text, _emailController.text, _passwordController.text);
                      if (mounted) Navigator.pop(context);
                    } catch (e) {
                      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
                    }
                    if (mounted) setState(() => _isLoading = false);
                  },
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}''',
        'home': f'''import 'package:flutter/material.dart';
import '../services/api_service.dart';
import '../widgets/loading_widget.dart';

class HomeScreen extends StatefulWidget {{
  const HomeScreen({{super.key}});
  @override
  State<HomeScreen> createState() => _HomeScreenState();
}}

class _HomeScreenState extends State<HomeScreen> {{
  int _currentIndex = 0;

  @override
  Widget build(BuildContext context) {{
    return Scaffold(
      body: IndexedStack(
        index: _currentIndex,
        children: const [
          _HomeContent(),
          Center(child: Text('Search')),
          Center(child: Text('Cart')),
          Center(child: Text('Profile')),
        ],
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _currentIndex,
        onDestinationSelected: (i) => setState(() => _currentIndex = i),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.home_outlined), selectedIcon: Icon(Icons.home), label: 'Home'),
          NavigationDestination(icon: Icon(Icons.search), label: 'Search'),
          NavigationDestination(icon: Icon(Icons.shopping_cart_outlined), label: 'Cart'),
          NavigationDestination(icon: Icon(Icons.person_outline), label: 'Profile'),
        ],
      ),
    );
  }}
}}

class _HomeContent extends StatelessWidget {{
  const _HomeContent();
  @override
  Widget build(BuildContext context) {{
    return SafeArea(
      child: CustomScrollView(
        slivers: [
          SliverAppBar(title: const Text('Home'), floating: true, actions: [
            IconButton(onPressed: () {{}}, icon: const Icon(Icons.notifications_outlined)),
          ]),
          SliverPadding(
            padding: const EdgeInsets.all(16),
            sliver: SliverList(
              delegate: SliverChildListDelegate([
                const Text('Welcome!', style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold)),
                const SizedBox(height: 16),
                ...List.generate(5, (i) => Card(
                  margin: const EdgeInsets.only(bottom: 12),
                  child: ListTile(
                    leading: CircleAvatar(child: Text('${{i+1}}')),
                    title: Text('Item ${{i+1}}'),
                    subtitle: const Text('Description'),
                    trailing: const Icon(Icons.chevron_right),
                  ),
                )),
              ]),
            ),
          ),
        ],
      ),
    );
  }}
}}''',
        'profile': '''import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/auth_service.dart';

class ProfileScreen extends StatelessWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Profile')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          const CircleAvatar(radius: 40, child: Icon(Icons.person, size: 40)),
          const SizedBox(height: 16),
          const Text('User Name', textAlign: TextAlign.center, style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
          const Text('user@email.com', textAlign: TextAlign.center, style: TextStyle(color: Colors.grey)),
          const SizedBox(height: 24),
          _buildTile(Icons.edit, 'Edit Profile', () {}),
          _buildTile(Icons.shopping_bag, 'Orders', () {}),
          _buildTile(Icons.location_on, 'Addresses', () {}),
          _buildTile(Icons.payment, 'Payment Methods', () {}),
          _buildTile(Icons.settings, 'Settings', () {}),
          _buildTile(Icons.help, 'Help & Support', () {}),
          const SizedBox(height: 16),
          ListTile(
            leading: const Icon(Icons.logout, color: Colors.red),
            title: const Text('Sign Out', style: TextStyle(color: Colors.red)),
            onTap: () => Provider.of<AuthService>(context, listen: false).logout(),
          ),
        ],
      ),
    );
  }

  Widget _buildTile(IconData icon, String title, VoidCallback onTap) {
    return Card(
      child: ListTile(
        leading: Icon(icon),
        title: Text(title),
        trailing: const Icon(Icons.chevron_right),
        onTap: onTap,
      ),
    );
  }
}''',
        'settings': '''import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/theme_provider.dart';

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final themeProvider = Provider.of<ThemeProvider>(context);
    return Scaffold(
      appBar: AppBar(title: const Text('Settings')),
      body: ListView(
        children: [
          SwitchListTile(
            title: const Text('Dark Mode'),
            subtitle: const Text('Toggle dark theme'),
            value: themeProvider.themeMode == ThemeMode.dark,
            onChanged: (_) => themeProvider.toggleTheme(),
          ),
          const Divider(),
          ListTile(title: const Text('Notifications'), trailing: Switch(value: true, onChanged: (v) {})),
          const Divider(),
          ListTile(title: const Text('Language'), subtitle: const Text('English'), trailing: const Icon(Icons.chevron_right)),
          const Divider(),
          ListTile(title: const Text('About'), subtitle: const Text('Version 1.0.0'), trailing: const Icon(Icons.chevron_right)),
        ],
      ),
    );
  }
}''',
        'cart': '''import 'package:flutter/material.dart';

class CartScreen extends StatelessWidget {
  const CartScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Cart')),
      body: const Center(child: Text('Cart is empty')),
      bottomNavigationBar: Container(
        padding: const EdgeInsets.all(16),
        child: ElevatedButton(
          onPressed: () {},
          child: const Text('Checkout - $0.00'),
        ),
      ),
    );
  }
}''',
        'search': '''import 'package:flutter/material.dart';

class SearchScreen extends StatelessWidget {
  const SearchScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.all(16),
              child: TextField(
                decoration: InputDecoration(
                  hintText: 'Search...',
                  prefixIcon: const Icon(Icons.search),
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                ),
              ),
            ),
            const Expanded(child: Center(child: Text('Start searching'))),
          ],
        ),
      ),
    );
  }
}''',
        'notifications': '''import 'package:flutter/material.dart';

class NotificationsScreen extends StatelessWidget {
  const NotificationsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Notifications')),
      body: const Center(child: Text('No notifications')),
    );
  }
}''',
        'product_list': '''import 'package:flutter/material.dart';

class ProductListScreen extends StatelessWidget {
  const ProductListScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Products')),
      body: GridView.builder(
        padding: const EdgeInsets.all(16),
        gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(crossAxisCount: 2, childAspectRatio: 0.7, crossAxisSpacing: 12, mainAxisSpacing: 12),
        itemCount: 10,
        itemBuilder: (_, i) => Card(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(child: Container(color: Colors.grey[200], child: const Center(child: Icon(Icons.image, size: 40)))),
              Padding(
                padding: const EdgeInsets.all(8),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Product ${{i+1}}', style: const TextStyle(fontWeight: FontWeight.bold)),
                    const Text('$99.99', style: TextStyle(color: Colors.green, fontWeight: FontWeight.w600)),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}''',
        'product_detail': '''import 'package:flutter/material.dart';

class ProductDetailScreen extends StatelessWidget {
  const ProductDetailScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: CustomScrollView(
        slivers: [
          SliverAppBar(expandedHeight: 300, pinned: true, flexibleSpace: FlexibleSpaceBar(background: Container(color: Colors.grey[200], child: const Center(child: Icon(Icons.image, size: 80))))),
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Product Name', style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold)),
                  const SizedBox(height: 8),
                  const Text('$99.99', style: TextStyle(fontSize: 20, color: Colors.green, fontWeight: FontWeight.w600)),
                  const SizedBox(height: 16),
                  const Text('Product description goes here.'),
                  const SizedBox(height: 24),
                  SizedBox(width: double.infinity, height: 48, child: ElevatedButton(onPressed: () {}, child: const Text('Add to Cart'))),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}''',
        'checkout': '''import 'package:flutter/material.dart';

class CheckoutScreen extends StatelessWidget {
  const CheckoutScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Checkout')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          const Text('Shipping Address', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
          const SizedBox(height: 8),
          Card(child: ListTile(title: const Text('Add address'), leading: const Icon(Icons.add), trailing: const Icon(Icons.chevron_right))),
          const SizedBox(height: 16),
          const Text('Payment', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
          const SizedBox(height: 8),
          Card(child: ListTile(title: const Text('Add payment method'), leading: const Icon(Icons.payment), trailing: const Icon(Icons.chevron_right))),
          const SizedBox(height: 16),
          const Text('Order Summary', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
          const SizedBox(height: 8),
          const Card(child: Padding(padding: EdgeInsets.all(16), child: Column(children: [Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [Text('Subtotal'), Text('$99.99')]), SizedBox(height: 8), Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [Text('Shipping'), Text('$5.99')]), Divider(), Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [Text('Total', style: TextStyle(fontWeight: FontWeight.bold)), Text('$105.98', style: TextStyle(fontWeight: FontWeight.bold))])]))),
          const SizedBox(height: 24),
          SizedBox(width: double.infinity, height: 48, child: ElevatedButton(onPressed: () {}, child: const Text('Place Order'))),
        ],
      ),
    );
  }
}''',
        'order_history': '''import 'package:flutter/material.dart';

class OrderHistoryScreen extends StatelessWidget {
  const OrderHistoryScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('My Orders')),
      body: ListView.builder(
        padding: const EdgeInsets.all(16),
        itemCount: 5,
        itemBuilder: (_, i) => Card(
          margin: const EdgeInsets.only(bottom: 12),
          child: ListTile(
            leading: CircleAvatar(child: Text('#${{i+1}}')),
            title: Text('Order #${1000 + i}'),
            subtitle: const Text('2 items - $59.99'),
            trailing: const Chip(label: Text('Delivered', style: TextStyle(fontSize: 12))),
          ),
        ),
      ),
    );
  }
}''',
        'wishlist': '''import 'package:flutter/material.dart';

class WishlistScreen extends StatelessWidget {
  const WishlistScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Wishlist')),
      body: const Center(child: Text('Your wishlist is empty')),
    );
  }
}''',
        'categories': '''import 'package:flutter/material.dart';

class CategoriesScreen extends StatelessWidget {
  const CategoriesScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Categories')),
      body: GridView.builder(
        padding: const EdgeInsets.all(16),
        gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(crossAxisCount: 2, childAspectRatio: 1, crossAxisSpacing: 12, mainAxisSpacing: 12),
        itemCount: 8,
        itemBuilder: (_, i) => Card(child: Center(child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [Icon(Icons.category, size: 40, color: Colors.blue[200 * (i % 3 + 1)]!), const SizedBox(height: 8), Text('Category ${{i+1}}')]))),
      ),
    );
  }
}''',
    }

    return screen_configs.get(screen, f'''import 'package:flutter/material.dart';

class {screen_name}Screen extends StatelessWidget {{
  const {screen_name}Screen({{super.key}});

  @override
  Widget build(BuildContext context) {{
    return Scaffold(
      appBar: AppBar(title: const Text('{screen_name}')),
      body: const Center(child: Text('{screen_name}')),
    );
  }}
}}''')


def _generate_react_native_project(name: str, template: str, features: list, backend_url: str) -> dict:
    tpl = MOBILE_TEMPLATES.get(template, MOBILE_TEMPLATES['ecommerce'])
    safe_name = name.replace(' ', '_').replace('-', '_').lower()

    files = {}
    files['package.json'] = json.dumps({
        'name': safe_name,
        'version': '1.0.0',
        'main': 'index.js',
        'scripts': {
            'start': 'react-native start',
            'android': 'react-native run-android',
            'ios': 'react-native run-ios',
        },
        'dependencies': {
            'react': '18.2.0',
            'react-native': '0.74.0',
            '@react-navigation/native': '^6.1.0',
            '@react-navigation/native-stack': '^6.9.0',
            '@react-navigation/bottom-tabs': '^6.5.0',
            'react-native-screens': '^3.30.0',
            'react-native-safe-area-context': '^4.8.0',
            'axios': '^1.6.0',
            '@react-native-async-storage/async-storage': '^1.21.0',
            'react-native-vector-icons': '^10.0.0',
            **({'react-native-push-notification': '^8.1.0'} if 'push_notifications' in features else {}),
            **({'react-native-image-picker': '^7.1.0'} if 'camera' in features else {}),
            **({'react-native-geolocation-service': '^5.3.1'} if 'location' in features else {}),
            **({'react-native-webview': '^13.6.0'} if 'video' in features else {}),
        },
    }, indent=2)

    files['index.js'] = f'''import {{ AppRegistry }} from 'react-native';
import App from './src/App';
AppRegistry.registerComponent('{safe_name}', () => App);
'''

    files['src/App.tsx'] = f'''import React from 'react';
import {{ NavigationContainer }} from '@react-navigation/native';
import {{ createNativeStackNavigator }} from '@react-navigation/native-stack';
import {{ AuthProvider }} from './context/AuthContext';
import {{ ThemeProvider }} from './context/ThemeContext';
import SplashScreen from './screens/SplashScreen';
import LoginScreen from './screens/LoginScreen';
import HomeScreen from './screens/HomeScreen';
import ProfileScreen from './screens/ProfileScreen';
import SettingsScreen from './screens/SettingsScreen';

const Stack = createNativeStackNavigator();

const App = () => (
  <AuthProvider>
    <ThemeProvider>
      <NavigationContainer>
        <Stack.Navigator screenOptions={{{{ headerShown: false }}}}>
          <Stack.Screen name="Splash" component={{SplashScreen}} />
          <Stack.Screen name="Login" component={{LoginScreen}} />
          <Stack.Screen name="Home" component={{HomeScreen}} />
          <Stack.Screen name="Profile" component={{ProfileScreen}} />
          <Stack.Screen name="Settings" component={{SettingsScreen}} />
        </Stack.Navigator>
      </NavigationContainer>
    </ThemeProvider>
  </AuthProvider>
);

export default App;
'''

    files['src/services/ApiService.ts'] = f'''import axios from 'axios';

const api = axios.create({{
  baseURL: '{backend_url}',
  timeout: 30000,
  headers: {{ 'Content-Type': 'application/json' }},
}};

api.interceptors.request.use(async (config) => {{
  const token = await AsyncStorage.getItem('auth_token');
  if (token) config.headers.Authorization = `Bearer ${{token}}`;
  return config;
}});

api.interceptors.response.use(
  (resp) => resp,
  async (error) => {{
    if (error.response?.status === 401) {{
      await AsyncStorage.removeItem('auth_token');
    }}
    return Promise.reject(error);
  }}
);

export default api;
'''

    files['src/context/AuthContext.tsx'] = '''import React, { createContext, useContext, useState, useEffect } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import api from '../services/ApiService';

const AuthContext = createContext({});

export const useAuth = () => useContext(AuthContext);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    const token = await AsyncStorage.getItem('auth_token');
    if (token) {
      try {
        const resp = await api.get('/auth/me');
        setUser(resp.data);
      } catch {
        await AsyncStorage.removeItem('auth_token');
      }
    }
    setLoading(false);
  };

  const login = async (email, password) => {
    const resp = await api.post('/auth/login', { email, password });
    await AsyncStorage.setItem('auth_token', resp.data.token);
    setUser(resp.data.user);
  };

  const logout = async () => {
    await AsyncStorage.removeItem('auth_token');
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};
'''

    files['src/context/ThemeContext.tsx'] = '''import React, { createContext, useContext, useState } from 'react';
import { useColorScheme } from 'react-native';

const ThemeContext = createContext({});

export const useTheme = () => useContext(ThemeContext);

export const ThemeProvider = ({ children }) => {
  const systemScheme = useColorScheme();
  const [isDark, setIsDark] = useState(systemScheme === 'dark');

  const toggleTheme = () => setIsDark(!isDark);

  return (
    <ThemeContext.Provider value={{ isDark, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
};
'''

    screens = tpl.get('screens', ['SplashScreen', 'HomeScreen', 'LoginScreen'])
    for screen in screens:
        screen_name = ''.join(w.capitalize() for w in screen.split('_'))
        files[f'src/screens/{screen_name}.tsx'] = f'''import React from 'react';
import {{ View, Text, StyleSheet }} from 'react-native';

const {screen_name} = ({{ navigation }}) => (
  <View style={styles.container}>
    <Text style={styles.title}>{screen_name}</Text>
  </View>
);

const styles = StyleSheet.create({{
  container: {{ flex: 1, justifyContent: 'center', alignItems: 'center' }},
  title: {{ fontSize: 24, fontWeight: 'bold' }},
}});

export default {screen_name};
'''

    files['src/components/CustomButton.tsx'] = '''import React from 'react';
import { TouchableOpacity, Text, ActivityIndicator, StyleSheet } from 'react-native';

interface Props {
  title: string;
  onPress: () => void;
  loading?: boolean;
  color?: string;
}

const CustomButton = ({ title, onPress, loading = false, color = '#2196F3' }: Props) => (
  <TouchableOpacity
    style={[styles.button, { backgroundColor: color }]}
    onPress={onPress}
    disabled={loading}
  >
    {loading ? (
      <ActivityIndicator color="#fff" />
    ) : (
      <Text style={styles.text}>{title}</Text>
    )}
  </TouchableOpacity>
);

const styles = StyleSheet.create({
  button: { height: 48, borderRadius: 8, justifyContent: 'center', alignItems: 'center' },
  text: { color: '#fff', fontSize: 16, fontWeight: '600' },
});

export default CustomButton;
'''

    files['tsconfig.json'] = json.dumps({
        'compilerOptions': {'target': 'esnext', 'module': 'commonjs', 'lib': ['es2017'], 'jsx': 'react-native', 'strict': True, 'esModuleInterop': True, 'skipLibCheck': True},
        'exclude': ['node_modules'],
    }, indent=2)

    files['README.md'] = f'''# {name}

Generated by Getszy Mobile Builder (React Native)

## Template
{tpl['name']}

## Features
{", ".join(features)}

## Getting Started
```bash
npm install
npx react-native run-android  # or run-ios
```

## Backend
API: {backend_url}
'''

    return files


# ── Endpoints ──

@router.post('/generate')
async def generate_project(body: MobileProjectIn, _=Depends(get_current_admin)):
    if body.template not in MOBILE_TEMPLATES:
        raise HTTPException(400, f'Invalid template: {body.template}. Available: {list(MOBILE_TEMPLATES.keys())}')
    if body.platform not in ('flutter', 'react_native'):
        raise HTTPException(400, 'Platform must be flutter or react_native')

    invalid_features = [f for f in body.features if f not in MOBILE_FEATURES]
    if invalid_features:
        raise HTTPException(400, f'Invalid features: {invalid_features}')

    if body.platform == 'flutter':
        files = _generate_flutter_project(body.name, body.template, body.features, body.backend_url)
    else:
        files = _generate_react_native_project(body.name, body.template, body.features, body.backend_url)

    project_id = _uid()
    file_tree = {}
    for fpath in sorted(files.keys()):
        parts = fpath.split('/')
        current = file_tree
        for part in parts[:-1]:
            current = current.setdefault(part, {})
        current[parts[-1]] = len(files[fpath])

    await db.mobile_projects.insert_one({
        'id': project_id,
        'name': body.name,
        'platform': body.platform,
        'template': body.template,
        'features': body.features,
        'backend_url': body.backend_url,
        'files': files,
        'file_tree': file_tree,
        'created_at': _now(),
        'updated_at': _now(),
    })

    return {
        'project_id': project_id,
        'name': body.name,
        'platform': body.platform,
        'template': body.template,
        'file_count': len(files),
        'file_tree': file_tree,
    }


@router.get('/projects')
async def list_projects(_=Depends(get_current_admin)):
    projects = await db.mobile_projects.find({}, {'_id': 0, 'files': 0}).sort('created_at', -1).to_list(100)
    return projects


@router.get('/projects/{project_id}')
async def get_project(project_id: str, _=Depends(get_current_admin)):
    project = await db.mobile_projects.find_one({'id': project_id}, {'_id': 0})
    if not project:
        raise HTTPException(404, 'Project not found')
    return project


@router.get('/projects/{project_id}/files/{file_path:path}')
async def get_file(project_id: str, file_path: str, _=Depends(get_current_admin)):
    project = await db.mobile_projects.find_one({'id': project_id}, {'_id': 0, 'files': 1})
    if not project:
        raise HTTPException(404, 'Project not found')
    files = project.get('files', {})
    if file_path not in files:
        raise HTTPException(404, f'File {file_path} not found')
    return {'path': file_path, 'content': files[file_path]}


@router.put('/projects/{project_id}/files/{file_path:path}')
async def update_file(project_id: str, file_path: str, body: FileUpdateIn, _=Depends(get_current_admin)):
    project = await db.mobile_projects.find_one({'id': project_id}, {'_id': 0, 'files': 1})
    if not project:
        raise HTTPException(404, 'Project not found')
    await db.mobile_projects.update_one({'id': project_id}, {'$set': {
        f'files.{file_path}': body.content,
        'updated_at': _now(),
    }})
    return {'updated': True, 'path': file_path}


@router.delete('/projects/{project_id}')
async def delete_project(project_id: str, _=Depends(get_current_admin)):
    res = await db.mobile_projects.delete_one({'id': project_id})
    if res.deleted_count == 0:
        raise HTTPException(404, 'Project not found')
    return {'deleted': True}


@router.post('/projects/{project_id}/build')
async def build_project(project_id: str, _=Depends(get_current_admin)):
    project = await db.mobile_projects.find_one({'id': project_id}, {'_id': 0, 'platform': 1, 'name': 1})
    if not project:
        raise HTTPException(404, 'Project not found')

    platform = project.get('platform', 'flutter')
    build_cmd = 'flutter build apk --release' if platform == 'flutter' else 'cd android && ./gradlew assembleRelease'

    await db.mobile_projects.update_one({'id': project_id}, {'$set': {
        'build_status': 'building',
        'build_started_at': _now(),
    }})

    return {
        'status': 'building',
        'command': build_cmd,
        'platform': platform,
        'started_at': _now(),
    }


@router.post('/projects/{project_id}/clone')
async def clone_project(project_id: str, body: MobileProjectIn, _=Depends(get_current_admin)):
    original = await db.mobile_projects.find_one({'id': project_id}, {'_id': 0})
    if not original:
        raise HTTPException(404, 'Project not found')

    new_id = _uid()
    new_project = {
        'id': new_id,
        'name': body.name or f"{original['name']} (Copy)",
        'platform': original['platform'],
        'template': original['template'],
        'features': original['features'],
        'backend_url': original['backend_url'],
        'files': original.get('files', {}),
        'file_tree': original.get('file_tree', {}),
        'created_at': _now(),
        'updated_at': _now(),
    }
    await db.mobile_projects.insert_one(new_project)

    return {
        'project_id': new_id,
        'name': new_project['name'],
        'cloned_from': project_id,
    }


@router.post('/projects/{project_id}/ai-enhance')
async def ai_enhance(project_id: str, body: AIEnhanceIn, _=Depends(get_current_admin)):
    project = await db.mobile_projects.find_one({'id': project_id}, {'_id': 0, 'files': 1})
    if not project:
        raise HTTPException(404, 'Project not found')
    files = project.get('files', {})
    if body.file_path not in files:
        raise HTTPException(404, f'File {body.file_path} not found')

    current_code = files[body.file_path]
    prompt = f"""Enhance this code file. Follow these instructions: {body.instructions}

Return ONLY the improved code, no explanations.

```{body.file_path.split('.')[-1]}
{current_code}
```"""
    try:
        result = chat_completion([
            {'role': 'system', 'content': 'You are an expert developer. Return only the enhanced code.'},
            {'role': 'user', 'content': prompt},
        ])
        enhanced = result.get('content', current_code)
        enhanced = enhanced.strip()
        if enhanced.startswith('```'):
            lines = enhanced.split('\n')
            enhanced = '\n'.join(lines[1:-1])

        await db.mobile_projects.update_one({'id': project_id}, {'$set': {
            f'files.{body.file_path}': enhanced,
            'updated_at': _now(),
        }})
        return {'enhanced': True, 'path': body.file_path, 'content': enhanced}
    except Exception as e:
        return {'enhanced': False, 'error': str(e)}


@router.post('/projects/{project_id}/add-screen')
async def add_screen(project_id: str, body: AddScreenIn, _=Depends(get_current_admin)):
    project = await db.mobile_projects.find_one({'id': project_id}, {'_id': 0, 'files': 1, 'platform': 1})
    if not project:
        raise HTTPException(404, 'Project not found')

    platform = project.get('platform', 'flutter')
    screen_name = ''.join(w.capitalize() for w in body.name.split('_'))

    if platform == 'flutter':
        field_lines = []
        for f in body.fields:
            field_lines.append(f"          {'TextEditingController' if f.get('type', 'text') == 'text' else 'TextEditingController'} {f['name'].lower()}Controller = TextEditingController();")
        controllers = '\n'.join(field_lines)

        if body.layout == 'form':
            build_fields = '\n'.join([
                f"              TextFormField(controller: {f['name'].lower()}Controller, decoration: const InputDecoration(labelText: '{f['name'].replace('_', ' ').title()}')),"
                for f in body.fields
            ])
            code = f'''import 'package:flutter/material.dart';

class {screen_name}Screen extends StatelessWidget {{
  const {screen_name}Screen({{super.key}});

  @override
  Widget build(BuildContext context) {{
    return Scaffold(
      appBar: AppBar(title: const Text('{screen_name}')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
{build_fields},
            const SizedBox(height: 16),
            SizedBox(width: double.infinity, child: ElevatedButton(onPressed: () {{}}, child: const Text('Submit'))),
          ],
        ),
      ),
    );
  }}
}}'''
        elif body.layout == 'grid':
            code = f'''import 'package:flutter/material.dart';

class {screen_name}Screen extends StatelessWidget {{
  const {screen_name}Screen({{super.key}});

  @override
  Widget build(BuildContext context) {{
    return Scaffold(
      appBar: AppBar(title: const Text('{screen_name}')),
      body: GridView.builder(
        padding: const EdgeInsets.all(16),
        gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(crossAxisCount: 2, crossAxisSpacing: 12, mainAxisSpacing: 12),
        itemCount: 20,
        itemBuilder: (_, i) => Card(child: Center(child: Text('${screen_name} ${{i+1}}'))),
      ),
    );
  }}
}}'''
        else:
            code = f'''import 'package:flutter/material.dart';

class {screen_name}Screen extends StatelessWidget {{
  const {screen_name}Screen({{super.key}});

  @override
  Widget build(BuildContext context) {{
    return Scaffold(
      appBar: AppBar(title: const Text('{screen_name}')),
      body: ListView.builder(
        padding: const EdgeInsets.all(16),
        itemCount: 20,
        itemBuilder: (_, i) => Card(
          margin: const EdgeInsets.only(bottom: 8),
          child: ListTile(
            leading: CircleAvatar(child: Text('${{i+1}}')),
            title: Text('${screen_name} item ${{i+1}}'),
            trailing: const Icon(Icons.chevron_right),
          ),
        ),
      ),
    );
  }}
}}'''
    else:
        code = f'''import React from 'react';
import {{ View, Text, StyleSheet }} from 'react-native';

const {screen_name} = () => (
  <View style={{styles.container}}>
    <Text style={{styles.title}}>{screen_name}</Text>
  </View>
);

const styles = StyleSheet.create({{
  container: {{ flex: 1, justifyContent: 'center', alignItems: 'center' }},
  title: {{ fontSize: 24, fontWeight: 'bold' }},
}});

export default {screen_name};
'''

    file_path = f'lib/screens/{body.name.lower()}.dart' if platform == 'flutter' else f'src/screens/{screen_name}.tsx'
    await db.mobile_projects.update_one({'id': project_id}, {'$set': {
        f'files.{file_path}': code,
        'updated_at': _now(),
    }})
    return {'added': True, 'path': file_path, 'content': code}


@router.post('/projects/{project_id}/add-api-endpoint')
async def add_api_endpoint(project_id: str, body: AddEndpointIn, _=Depends(get_current_admin)):
    project = await db.mobile_projects.find_one({'id': project_id}, {'_id': 0, 'files': 1, 'platform': 1, 'backend_url': 1})
    if not project:
        raise HTTPException(404, 'Project not found')

    platform = project.get('platform', 'flutter')
    method = body.method.upper()

    if platform == 'flutter':
        method_map = {'GET': 'get', 'POST': 'post', 'PUT': 'put', 'PATCH': 'patch', 'DELETE': 'delete'}
        dio_method = method_map.get(method, 'get')
        code = f'''
  // {body.name}
  Future<Map<String, dynamic>> {body.name.replace(' ', '_').lower()}({{Map<String, dynamic>? params}}) async {{
    final resp = await _dio.{dio_method}('{body.endpoint_path}', queryParameters: params);
    return resp.data;
  }}
'''
    else:
        code = f'''
  // {body.name}
  static async {body.name.replace(' ', '_').toLowerCase()}({{params?: Record<string, any>}}) {{
    const resp = await api.{method.toLowerCase()}('{body.endpoint_path}', {{ params }});
    return resp.data;
  }}
'''

    service_file = 'lib/services/api_service.dart' if platform == 'flutter' else 'src/services/ApiService.ts'
    files = project.get('files', {})
    if service_file in files:
        files[service_file] = files[service_file] + code
        await db.mobile_projects.update_one({'id': project_id}, {'$set': {
            f'files.{service_file}': files[service_file],
            'updated_at': _now(),
        }})
    return {'added': True, 'method': method, 'endpoint': body.endpoint_path, 'code': code}
