// Debounce + door-opening state machine (pure logic, no hardware access).
#pragma once

#include "fc_types.h"

namespace fc {

// Time-based debouncer: the reported state only changes after the raw input
// has been continuously different from it for `stableMs`. Unlike a "lock-out
// after a change" debounce this never swallows a real edge: every change that
// lasts at least stableMs is reported, and shorter glitches are ignored.
class Debouncer {
 public:
  explicit Debouncer(uint32_t stableMs) : stableMs_(stableMs) {}

  void reset(bool state, uint64_t nowMs) {
    state_ = state;
    pending_ = false;
    edgeMs_ = nowMs;
  }

  // Feed one raw sample. Returns true when the debounced state just changed.
  bool update(bool raw, uint64_t nowMs) {
    if (raw == state_) {
      pending_ = false;
      return false;
    }
    if (!pending_) {
      pending_ = true;
      pendingSinceMs_ = nowMs;
    }
    if (nowMs - pendingSinceMs_ >= stableMs_) {
      state_ = raw;
      pending_ = false;
      edgeMs_ = pendingSinceMs_;  // when the input first showed the new state
      return true;
    }
    return false;
  }

  bool state() const { return state_; }
  // Time at which the raw input first showed the current state.
  uint64_t edgeMs() const { return edgeMs_; }

 private:
  uint32_t stableMs_;
  bool state_ = false;
  bool pending_ = false;
  uint64_t pendingSinceMs_ = 0;
  uint64_t edgeMs_ = 0;
};

struct DoorOutput {
  bool opened = false;      // a new opening was just counted
  bool closed = false;      // the door just closed
  bool eventReady = false;  // `event` is complete and must be queued
  DoorEventRec event = {0, 0, 0, 0, 0};
};

// Turns debounced door state into counted openings.
//  - An opening is counted when the door has been open for the debounce time.
//  - The event is emitted when the door closes (dur_ms = open time), or when
//    it has been open longer than heldOpenLimitMs (dur_ms = -1). After a
//    held-open event nothing more is emitted until the door closes and opens
//    again.
//  - If the door is already open at power-up, that opening is not counted
//    (we did not see it start); counting begins after the first close.
class DoorMonitor {
 public:
  DoorMonitor(uint32_t bootId, uint32_t debounceMs, uint32_t heldOpenLimitMs)
      : bootId_(bootId), heldLimitMs_(heldOpenLimitMs), deb_(debounceMs) {}

  void begin(bool rawOpen, uint64_t nowMs) {
    deb_.reset(rawOpen, nowMs);
    tracking_ = false;
    held_ = false;
  }

  // Call often (every few ms). epochNow = current UTC epoch, 0 if unknown.
  DoorOutput update(bool rawOpen, uint64_t nowMs, uint32_t epochNow) {
    DoorOutput out;
    bool changed = deb_.update(rawOpen, nowMs);
    if (changed && deb_.state()) {
      // Door opened.
      n_++;
      openMs_ = deb_.edgeMs();
      uint32_t lagS = (uint32_t)((nowMs - openMs_) / 1000);
      openEpoch_ = (epochNow > lagS) ? (epochNow - lagS) : 0;
      tracking_ = true;
      held_ = false;
      out.opened = true;
    } else if (changed && !deb_.state()) {
      // Door closed.
      out.closed = true;
      if (tracking_ && !held_) {
        uint64_t dur = deb_.edgeMs() - openMs_;
        if (dur > 0x7FFFFFFFULL) dur = 0x7FFFFFFFULL;
        fill(out, (int32_t)dur);
      }
      tracking_ = false;
      held_ = false;
    }
    if (tracking_ && !held_ && deb_.state() && heldLimitMs_ > 0 &&
        nowMs - openMs_ >= heldLimitMs_) {
      held_ = true;
      fill(out, -1);
    }
    return out;
  }

  bool isOpen() const { return deb_.state(); }
  bool heldOpen() const { return held_; }
  uint32_t openingsThisBoot() const { return n_; }

 private:
  void fill(DoorOutput& out, int32_t dur) {
    out.eventReady = true;
    out.event.boot = bootId_;
    out.event.n = n_;
    out.event.t = openEpoch_;
    out.event.dur_ms = dur;
    out.event.up_s = (uint32_t)(openMs_ / 1000);
  }

  uint32_t bootId_;
  uint32_t heldLimitMs_;
  Debouncer deb_;
  uint32_t n_ = 0;
  uint64_t openMs_ = 0;
  uint32_t openEpoch_ = 0;
  bool tracking_ = false;
  bool held_ = false;
};

}  // namespace fc
