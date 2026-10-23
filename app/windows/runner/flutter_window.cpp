#include "flutter_window.h"
#include <commctrl.h>
#include "flutter/generated_plugin_registrant.h"

FlutterWindow::FlutterWindow(const flutter::DartProject& project) : project_(project) {}
FlutterWindow::~FlutterWindow() { OnDestroy(); }

bool FlutterWindow::OnCreate() {
  if (!Win32Window::OnCreate()) return false;
  RECT frame = GetClientArea();
  flutter_controller_ = std::make_unique<flutter::FlutterViewController>(
      frame.right - frame.left, frame.bottom - frame.top, project_);
  if (!flutter_controller_->engine() || !flutter_controller_->view()) return false;
  closing_ = false;
  auto* engine = flutter_controller_->engine();
  RegisterPlugins(engine);
  view_ = flutter_controller_->view()->GetNativeWindow();
  SetChildContent(view_);
  const HWND top = GetHandle();
  dispatch_ = std::make_shared<PlatformDispatch>([top] {
    return ::PostMessage(top, WM_APP + 1, 0, 0) != FALSE;
  });
  registrar_ = std::make_unique<flutter::PluginRegistrarWindows>(
      engine->GetRegistrarForPlugin("FmlWindowsDispatch"));
  AddTopDelegate([this](HWND, UINT message, WPARAM, LPARAM) -> std::optional<LRESULT> {
    if (message != WM_APP + 1) return std::nullopt;
    const auto queue = dispatch_;  // Keep the queue alive across reply callbacks.
    queue->Drain([this](PlatformDispatch::Result result) {
      auto found = replies_.find(result.request_id);
      if (closing_ || found == replies_.end()) return;
      auto reply = std::move(found->second);
      replies_.erase(found);  // Erase before callback: reentrancy cannot reply twice.
      reply(std::move(result));
    });
    return 0;
  });
  if (!::SetWindowSubclass(view_, ViewProc, 1, reinterpret_cast<DWORD_PTR>(this))) {
    OnDestroy();
    return false;
  }
  // Future RegisterXxxChannel(engine->messenger(), top, view_) rows go here.
  // No future platform channels or installers are fabricated in S0.
  engine->SetNextFrameCallback([this] { Show(); });
  flutter_controller_->ForceRedraw();
  return true;
}

void FlutterWindow::AddTopDelegate(flutter::WindowProcDelegate delegate) {
  if (!closing_) tokens_.push_back(registrar_->RegisterTopLevelWindowProcDelegate(std::move(delegate)));
}
void FlutterWindow::AddViewDelegate(flutter::WindowProcDelegate delegate) {
  if (!closing_) view_delegates_.push_back(std::move(delegate));
}
void FlutterWindow::AddShutdownHooks(ShutdownHooks hooks) {
  if (!closing_) hooks_.push_back(std::move(hooks));
}
uint64_t FlutterWindow::ExpectReply(Reply reply) {
  if (closing_) return 0;
  const auto id = next_request_++;
  replies_.emplace(id, std::move(reply));
  return id;
}
LRESULT CALLBACK FlutterWindow::ViewProc(HWND hwnd, UINT msg, WPARAM wp, LPARAM lp,
                                        UINT_PTR id, DWORD_PTR data) {
  auto* self = reinterpret_cast<FlutterWindow*>(data);
  if (msg == WM_NCDESTROY) {
    ::RemoveWindowSubclass(hwnd, ViewProc, id);
    self->view_ = nullptr;
  } else if (!self->closing_) {
    for (const auto& delegate : self->view_delegates_) {
      const auto result = delegate(hwnd, msg, wp, lp);
      if (result) return *result;
    }
  }
  return ::DefSubclassProc(hwnd, msg, wp, lp);
}
void FlutterWindow::OnDestroy() {
  if (closing_) return;
  closing_ = true;                  // 1. Reject new requests/completions.
  dispatch_->Close();
  for (auto& hook : hooks_) if (hook.cancel_and_join) hook.cancel_and_join();
  // No queue mutex is held while joining or unregistering waits.
  for (auto& hook : hooks_) if (hook.unregister) hook.unregister();
  for (int token : tokens_) registrar_->UnregisterTopLevelWindowProcDelegate(token);
  tokens_.clear();
  if (view_) ::RemoveWindowSubclass(view_, ViewProc, 1);
  view_ = nullptr;
  view_delegates_.clear();
  replies_.clear();                 // Abandon pending replies, never touch messenger.
  for (auto& hook : hooks_) if (hook.release) hook.release();
  hooks_.clear();
  registrar_.reset();
  dispatch_.reset();
  flutter_controller_.reset();
  Win32Window::OnDestroy();
}
LRESULT FlutterWindow::MessageHandler(HWND hwnd, UINT message, WPARAM wp,
                                      LPARAM lp) noexcept {
  if (flutter_controller_ && !closing_) {
    auto result = flutter_controller_->HandleTopLevelWindowProc(hwnd, message, wp, lp);
    if (result) return *result;
    if (message == WM_FONTCHANGE) flutter_controller_->engine()->ReloadSystemFonts();
  }
  return Win32Window::MessageHandler(hwnd, message, wp, lp);
}
