/// Turns API identifiers into words people read: `left_elbow` -> `Left elbow`.
String humanize(String id) {
  final words = id.replaceAll('_', ' ').trim();
  if (words.isEmpty) return words;
  return words[0].toUpperCase() + words.substring(1);
}

/// `action` -> `Action`.
String capitalize(String s) => s.isEmpty ? s : s[0].toUpperCase() + s.substring(1);
