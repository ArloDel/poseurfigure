const _months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

/// `Today, 20:14`, `Yesterday, 19:02`, `8 Nov` or `8 Nov 2025`, in local time.
String friendlyDate(DateTime time, {DateTime? now}) {
  final t = time.toLocal();
  final n = (now ?? DateTime.now()).toLocal();
  final day = DateTime(t.year, t.month, t.day);
  final today = DateTime(n.year, n.month, n.day);
  final clock = '${t.hour.toString().padLeft(2, '0')}:${t.minute.toString().padLeft(2, '0')}';

  final diff = today.difference(day).inDays;
  if (diff == 0) return 'Today, $clock';
  if (diff == 1) return 'Yesterday, $clock';
  final date = '${t.day} ${_months[t.month - 1]}';
  return t.year == n.year ? date : '$date ${t.year}';
}
