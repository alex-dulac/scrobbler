const _months = [
  'Jan',
  'Feb',
  'Mar',
  'Apr',
  'May',
  'Jun',
  'Jul',
  'Aug',
  'Sep',
  'Oct',
  'Nov',
  'Dec',
];

/// Groups thousands: 8420 → 8,420.
String formatCount(num value) {
  final digits = value.round().abs().toString();
  final grouped = digits.replaceAllMapped(
    RegExp(r'\B(?=(\d{3})+(?!\d))'),
    (_) => ',',
  );
  return value < 0 ? '-$grouped' : grouped;
}

/// Last.fm reports totals as strings; format them when they are numeric.
String formatCountText(String value) {
  final parsed = int.tryParse(value);
  return parsed == null ? value : formatCount(parsed);
}

/// Short month name for a 1-based month: 3 → Mar.
String formatMonth(int month) => _months[month - 1];

String formatDate(DateTime date) =>
    '${_months[date.month - 1]} ${date.day}, ${date.year}';

const _weekdays = [
  'Monday',
  'Tuesday',
  'Wednesday',
  'Thursday',
  'Friday',
  'Saturday',
  'Sunday',
];

/// 12-hour clock: 18:30 → 6:30pm.
String formatClock(DateTime date) {
  final hour = date.hour % 12 == 0 ? 12 : date.hour % 12;
  return '$hour:${date.minute.toString().padLeft(2, '0')}${date.hour < 12 ? 'am' : 'pm'}';
}

/// Full date and time, for tooltips: Saturday, Oct 17, 2026 · 6:30pm.
String formatFullDate(DateTime date) =>
    '${_weekdays[date.weekday - 1]}, ${formatDate(date)} · ${formatClock(date)}';

/// How long ago a listen was, in the coarsest terms that stay precise:
/// Just now · 12 min ago · Today 6:30pm · Yesterday 6:30pm · Tuesday 6:30pm ·
/// Oct 3 · 6:30pm · Oct 3, 2024.
String formatWhen(DateTime date, {DateTime? now}) {
  final current = now ?? DateTime.now();
  final elapsed = current.difference(date);
  if (!elapsed.isNegative && elapsed.inMinutes < 1) return 'Just now';
  if (!elapsed.isNegative && elapsed.inMinutes < 60) {
    return '${elapsed.inMinutes} min ago';
  }
  final today = DateTime(current.year, current.month, current.day);
  final days = today
      .difference(DateTime(date.year, date.month, date.day))
      .inDays;
  final clock = formatClock(date);
  if (days == 0) return 'Today $clock';
  if (days == 1) return 'Yesterday $clock';
  if (days > 1 && days < 7) return '${_weekdays[date.weekday - 1]} $clock';
  if (date.year == current.year) {
    return '${formatMonth(date.month)} ${date.day} · $clock';
  }
  return formatDate(date);
}
