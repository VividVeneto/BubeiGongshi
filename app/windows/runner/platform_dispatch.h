#ifndef RUNNER_PLATFORM_DISPATCH_H_
#define RUNNER_PLATFORM_DISPATCH_H_
#include <cstdint>
#include <deque>
#include <functional>
#include <mutex>
#include <utility>
#include <vector>

// Worker-facing value queue. Never carries a messenger, MethodResult or sink.
// The window owns it until all worker/wait callbacks have been joined.
class PlatformDispatch {
 public:
  struct Result { uint64_t request_id; std::vector<uint8_t> bytes; };
  explicit PlatformDispatch(std::function<bool()> wake) : wake_(std::move(wake)) {}
  bool Complete(Result result) {
    std::lock_guard<std::mutex> lock(mutex_);
    if (closed_) return false;
    queue_.push_back(std::move(result));
    // PostMessage is asynchronous, so holding this lock cannot reenter Drain.
    if (!wake_()) { queue_.pop_back(); return false; }
    return true;
  }
  // Platform thread only: correlate request_id with its pending reply exactly once.
  template <class Reply> void Drain(Reply reply) {
    std::deque<Result> batch;
    { std::lock_guard<std::mutex> lock(mutex_); batch.swap(queue_); }
    for (auto& result : batch) reply(std::move(result));
  }
  void Close() {
    std::lock_guard<std::mutex> lock(mutex_);
    closed_ = true;
    queue_.clear();
  }
 private:
  std::mutex mutex_;
  std::deque<Result> queue_;
  std::function<bool()> wake_;
  bool closed_ = false;
};
#endif
