#include "../runner/platform_dispatch.h"
#include <atomic>
#include <iostream>
#include <thread>
#include <set>
#define CHECK(x) do { if (!(x)) { std::cerr << #x << " failed at " << __LINE__; return 1; } } while (0)
int main() {
  std::atomic<int> posts{0};
  PlatformDispatch queue([&] { ++posts; return true; });
  std::vector<std::thread> workers;
  for (uint64_t i = 1; i <= 8; ++i) workers.emplace_back([&, i] {
    for (uint64_t j = 0; j < 200; ++j) queue.Complete({i * 1000 + j, {1, 2, 3}});
  });
  for (auto& worker : workers) worker.join();
  CHECK(posts == 1600);
  std::set<uint64_t> ids;
  const auto platform = std::this_thread::get_id();
  bool correct = true;
  queue.Drain([&](PlatformDispatch::Result result) {
    correct &= std::this_thread::get_id() == platform && result.bytes.size() == 3;
    correct &= ids.insert(result.request_id).second;
  });
  CHECK(correct && ids.size() == 1600);
  int duplicate = 0;
  queue.Drain([&](auto) { ++duplicate; });
  CHECK(duplicate == 0);
  PlatformDispatch failed([] { return false; });
  CHECK(!failed.Complete({1, {9}}));
  failed.Drain([&](auto) { ++duplicate; });
  CHECK(duplicate == 0);
  CHECK(queue.Complete({2, {}}));
  queue.Close(); queue.Close();
  CHECK(!queue.Complete({3, {}}));
  queue.Drain([&](auto) { ++duplicate; });
  CHECK(duplicate == 0);
  std::cout << "dispatch: concurrency, thread affinity, failed post, close PASS\n";
}
