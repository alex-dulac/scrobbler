import 'package:flutter/material.dart';
import '../../controllers/scrobbler_controller.dart';
import '../../theme/app_theme.dart';
import '../../widgets/page_heading.dart';
import '../listening/listening_page.dart';

class SettingsPage extends StatelessWidget {
  const SettingsPage({super.key, required this.controller});
  final ScrobblerController controller;
  @override
  Widget build(BuildContext context) => ListView(
    padding: AppSpacing.page,
    children: [
      const PageHeading(title: 'Settings'),
      Align(
        alignment: Alignment.centerLeft,
        child: SourcePicker(controller: controller),
      ),
      const SizedBox(height: 28),
      ListTile(
        contentPadding: EdgeInsets.zero,
        title: const Text('Backend address'),
        subtitle: Text(controller.api.baseUrl.toString()),
      ),
      ListTile(
        contentPadding: EdgeInsets.zero,
        title: const Text('History database'),
        subtitle: Text(
          controller.state?.databaseAvailable == true
              ? 'Connected · History and Wrapped use your synced library'
              : 'Unavailable · Live scrobbling and your pending queue still work',
        ),
      ),
      const SizedBox(height: 28),
      const Text(
        'Close the window to keep listening in the background. The menu bar brings you back; Quit stops the app.',
      ),
    ],
  );
}
