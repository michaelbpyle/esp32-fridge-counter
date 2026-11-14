// Server protocol: JSON payload builder, response parser, retry policy.
#pragma once

#include <string>

#include "fc_types.h"

namespace fc {

struct PayloadHeader {
  const char* deviceId;
  const char* fw;
  uint32_t bootId;
  const char* uplink;   // "wifi", "lte-m"
  uint32_t sentAt;      // UTC epoch now, 0 = clock unknown
  uint32_t uptimeS;
  uint32_t doorTotal;
};

struct StatusInfo {
  int rssi;             // dBm, 0 = unknown
  uint32_t heap;        // free heap bytes
  bool doorOpen;
  uint32_t queue;       // events still waiting on the device after this POST
  uint32_t dropped;     // lifetime count of events dropped because the queue was full
  const char* resetReason;
};

// Work out what to send for an event/reading timestamp.
//  - Same boot: age is always known from uptime; if the clock was unknown at
//    the time but is known now, the epoch is reconstructed.
//  - Earlier boot: age is only known when both the stored epoch and the
//    current clock are valid.
struct ResolvedTime {
  uint32_t t;      // epoch to send (0 = unknown)
  bool ageKnown;
  uint32_t ageS;
};
ResolvedTime resolveTime(uint32_t recBoot, uint32_t recT, uint32_t recUpS,
                         uint32_t curBoot, uint32_t curUptimeS, uint32_t nowEpoch);

// Build the ingest JSON body. `events`/`readings` may be null when count is 0.
std::string buildPayload(const PayloadHeader& h, const DoorEventRec* events, size_t nEvents,
                         const ReadingRec* readings, size_t nReadings, const StatusInfo& st);

struct IngestResponse {
  bool ok = false;
  uint32_t accepted = 0;
  uint32_t duplicates = 0;
  uint32_t serverTime = 0;
};
// Parse {"ok":true,"accepted":2,"duplicates":0,"server_time":...}.
// Returns true only if the body is a JSON object containing "ok": true.
bool parseIngestResponse(const std::string& body, IngestResponse& out);

enum class PostAction {
  Ack,          // delivered: remove what was sent from the queue
  DropBatch,    // server says the batch is malformed: discard it so the queue cannot jam
  RetryAuth,    // bad device key: keep everything, retry slowly
  RetryBackoff  // anything else (5xx, 404, timeouts, odd bodies): keep, retry with backoff
};
// httpStatus <= 0 means a transport error (no HTTP response at all).
PostAction classifyResponse(int httpStatus, bool bodyOk);

// Exponential backoff with +/-25 % jitter.
class Backoff {
 public:
  Backoff(uint32_t baseMs, uint32_t maxMs) : baseMs_(baseMs), maxMs_(maxMs) {}
  void reset() { failures_ = 0; }
  uint32_t failures() const { return failures_; }
  // Register a failure and return how long to wait. `rnd` is any random number.
  uint32_t next(uint32_t rnd);

 private:
  uint32_t baseMs_;
  uint32_t maxMs_;
  uint32_t failures_ = 0;
};

// Fixed-capacity FIFO that overwrites the oldest entry when full.
template <typename T, size_t N>
class Ring {
 public:
  bool push(const T& v) {
    bool dropped = false;
    if (count_ == N) {
      head_ = (head_ + 1) % N;
      count_--;
      dropped = true;
    }
    buf_[(head_ + count_) % N] = v;
    count_++;
    return dropped;
  }
  size_t size() const { return count_; }
  const T& at(size_t i) const { return buf_[(head_ + i) % N]; }
  void popFront(size_t n) {
    if (n > count_) n = count_;
    head_ = (head_ + n) % N;
    count_ -= n;
  }
  void clear() { head_ = 0; count_ = 0; }

 private:
  T buf_[N];
  size_t head_ = 0;
  size_t count_ = 0;
};

}  // namespace fc
