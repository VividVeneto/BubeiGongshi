#include "runner/flutter_window.h"
#include <iostream>
#include <thread>
#include <string>
#define CHECK(x) do { if (!(x)) { std::cerr << #x << " failed at " << __LINE__; return 1; } } while (0)
int main() {
  CHECK(SetDefaultDllDirectories(LOAD_LIBRARY_SEARCH_APPLICATION_DIR | LOAD_LIBRARY_SEARCH_SYSTEM32));
  CHECK(SetDllDirectoryW(L""));
  CHECK(SUCCEEDED(CoInitializeEx(nullptr, COINIT_APARTMENTTHREADED)));
  flutter::DartProject project(L"data");
  FlutterWindow window(project);
  CHECK(window.Create(L"WIN01 native test", {30, 30}, {640, 480}));
  auto dispatch = window.dispatch();
  const auto platform = std::this_thread::get_id();
  int replies = 0;
  bool on_platform = false;
  const auto request = window.ExpectReply([&](auto r) {
    ++replies; on_platform = std::this_thread::get_id() == platform && r.bytes == std::vector<uint8_t>{7};
  });
  std::thread worker([&] {
    dispatch->Complete({request, {7}});
    dispatch->Complete({request, {7}}); // duplicate must not call MethodResult twice
    dispatch->Complete({request + 100, {7}}); // unknown id dropped
  });
  worker.join();
  SendMessage(window.GetHandle(), WM_APP + 1, 0, 0);
  CHECK(replies == 1 && on_platform);
  int observed = 0;
  window.AddTopDelegate([&](HWND, UINT m, WPARAM, LPARAM) -> std::optional<LRESULT> {
    if (m == WM_APP + 21) ++observed;
    return std::nullopt;
  });
  window.AddTopDelegate([](HWND, UINT m, WPARAM, LPARAM) -> std::optional<LRESULT> {
    if (m == WM_APP + 22) return 123;
    return std::nullopt;
  });
  SendMessage(window.GetHandle(), WM_APP + 21, 0, 0);
  CHECK(observed == 1);
  CHECK(SendMessage(window.GetHandle(), WM_APP + 22, 0, 0) == 123);
  window.AddViewDelegate([](HWND, UINT m, WPARAM, LPARAM) -> std::optional<LRESULT> {
    if (m == WM_APP + 23) return 456;
    return std::nullopt;
  });
  CHECK(SendMessage(GetWindow(window.GetHandle(), GW_CHILD), WM_APP + 23, 0, 0) == 456);
  std::string order;
  window.AddShutdownHooks({[&] {
    std::thread late([&] { if (dispatch->Complete({request, {}})) std::terminate(); });
    late.join(); order += '1';
  }, [&] { order += '2'; }, [&] { order += '3'; }});
  window.ExpectReply([&](auto) { ++replies; });
  window.Destroy(); window.Destroy();
  CHECK(order == "123" && replies == 1);
  CHECK(!dispatch->Complete({request, {}}));
  CHECK(window.ExpectReply([](auto) {}) == 0);
  CoUninitialize();
  std::cout << "runner: real engine, once-only reply, delegates/subclass, shutdown PASS\n";
}
