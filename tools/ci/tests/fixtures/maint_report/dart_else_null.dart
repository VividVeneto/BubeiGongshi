int f(int? a, int? b) {
  if (a == null) {
    return 0;
  } else {
    return a ?? b!;
  }
}

bool g(String? s) {
  return s?.isNotEmpty == true;
}
