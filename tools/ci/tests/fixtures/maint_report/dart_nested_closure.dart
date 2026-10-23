void outer(bool a) {
  list.forEach((e) {
    if (e) {
      use(e);
    }
  });
  if (a) {
    use(a);
  }
}
