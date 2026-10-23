import 'dart:io';

List<String>? _arguments;

/// Original engine-forwarded arguments; never consult VM executable arguments.
List<String> get windowsLaunchArguments =>
    _arguments ?? (throw StateError('Windows arguments not initialized'));

/// Called once by main; preserves a defensive, immutable copy for WIN-03.
void setWindowsLaunchArguments(List<String> arguments) {
  if (_arguments != null)
    throw StateError('Windows arguments already initialized');
  _arguments = List<String>.unmodifiable(arguments);
}

/// Resolves a trusted packaged filename beside the executable, never in cwd/PATH.
String appDirFile(String name) {
  if (!RegExp(r'^[A-Za-z0-9_-]+\.[A-Za-z0-9]+$').hasMatch(name)) {
    throw ArgumentError.value(name, 'name', 'Expected a packaged filename');
  }
  return File(Platform.resolvedExecutable).parent.uri
      .resolve(name)
      .toFilePath();
}
