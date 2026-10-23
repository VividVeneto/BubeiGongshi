// 注释里的判定点不计入复杂度：if (a && b) { for (;;) {} }
void f() {
  final s = """
if (a && b) { for (;;) {} while (c) {} }
""";
  // if (q) { do { } while (r); }
  x();
}
