import 'package:flutter/material.dart';

import '../../core/theme.dart';
import '../chat/chat_screen.dart';
import 'dashboard_tab.dart';
import 'placeholder_tab.dart';
import 'profile_tab.dart';

/// Matches the mobile screen list from the blueprint: Home, Chatbot,
/// Trends, Referral/Support, and Profile/Settings are the five bottom-nav
/// destinations. Home, Chat, and Profile have real content as of Phase 4 --
/// Trends/Support are still navigable placeholders, swapped for the real
/// screen in their own later phase without touching this file otherwise.
class HomeShell extends StatefulWidget {
  const HomeShell({super.key});

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  int _selectedIndex = 0;

  static const List<Widget> _tabs = [
    DashboardTab(),
    ChatScreen(),
    PlaceholderTab(
      title: 'Trends',
      icon: Icons.show_chart,
      comingInPhase: 'Phase 6–7',
    ),
    PlaceholderTab(
      title: 'Support',
      icon: Icons.support_agent_outlined,
      comingInPhase: 'Phase 9',
    ),
    ProfileTab(),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: IndexedStack(index: _selectedIndex, children: _tabs),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _selectedIndex,
        onDestinationSelected: (index) => setState(() => _selectedIndex = index),
        backgroundColor: AppTheme.surfaceColor,
        indicatorColor: AppTheme.primaryColor.withOpacity(0.12),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.home_outlined), selectedIcon: Icon(Icons.home), label: 'Home'),
          NavigationDestination(icon: Icon(Icons.chat_bubble_outline), selectedIcon: Icon(Icons.chat_bubble), label: 'Chat'),
          NavigationDestination(icon: Icon(Icons.show_chart), selectedIcon: Icon(Icons.show_chart), label: 'Trends'),
          NavigationDestination(icon: Icon(Icons.support_agent_outlined), selectedIcon: Icon(Icons.support_agent), label: 'Support'),
          NavigationDestination(icon: Icon(Icons.person_outline), selectedIcon: Icon(Icons.person), label: 'Profile'),
        ],
      ),
    );
  }
}
