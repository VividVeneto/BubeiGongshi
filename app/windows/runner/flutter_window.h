#ifndef RUNNER_FLUTTER_WINDOW_H_
#define RUNNER_FLUTTER_WINDOW_H_
#include <flutter/dart_project.h>
#include <flutter/flutter_view_controller.h>
#include <flutter/plugin_registrar_windows.h>
#include <map>
#include <memory>
#include "platform_dispatch.h"
#include "win32_window.h"

// All APIs except dispatch()->Complete are platform-thread only.
class FlutterWindow : public Win32Window {
 public:
  explicit FlutterWindow(const flutter::DartProject& project);
  ~FlutterWindow() override;
  using Reply = std::function<void(PlatformDispatch::Result)>;
  struct ShutdownHooks {
    std::function<void()> cancel_and_join;
    std::function<void()> unregister;
    std::function<void()> release;
  };
  // Future channel owners register only in this aggregate, never replace WndProc.
  void AddTopDelegate(flutter::WindowProcDelegate delegate);
  void AddViewDelegate(flutter::WindowProcDelegate delegate);
  void AddShutdownHooks(ShutdownHooks hooks);
  uint64_t ExpectReply(Reply reply);
  std::shared_ptr<PlatformDispatch> dispatch() const { return dispatch_; }
 protected:
  bool OnCreate() override;
  void OnDestroy() override;
  LRESULT MessageHandler(HWND, UINT, WPARAM, LPARAM) noexcept override;
 private:
  static LRESULT CALLBACK ViewProc(HWND, UINT, WPARAM, LPARAM, UINT_PTR, DWORD_PTR);
  flutter::DartProject project_;
  std::unique_ptr<flutter::FlutterViewController> flutter_controller_;
  std::unique_ptr<flutter::PluginRegistrarWindows> registrar_;
  std::shared_ptr<PlatformDispatch> dispatch_;
  std::map<uint64_t, Reply> replies_;
  std::vector<int> tokens_;
  std::vector<flutter::WindowProcDelegate> view_delegates_;
  std::vector<ShutdownHooks> hooks_;
  HWND view_ = nullptr;
  uint64_t next_request_ = 1;
  bool closing_ = true;
};
#endif
