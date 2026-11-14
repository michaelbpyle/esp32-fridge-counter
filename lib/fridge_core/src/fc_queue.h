// Bounded store-and-forward queue of door events with a crash-safe journal.
#pragma once

#include <vector>

#include "fc_types.h"

namespace fc {

// Where the journal bytes live. The firmware implements this on LittleFS;
// the unit tests implement it in RAM (and inject faults).
class JournalStore {
 public:
  virtual ~JournalStore() {}
  // Read the whole journal. Return false only on a real I/O failure
  // (a missing journal is success with an empty vector).
  virtual bool readAll(std::vector<uint8_t>& out) = 0;
  // Append bytes durably (they must survive power loss once this returns).
  virtual bool append(const uint8_t* data, size_t len) = 0;
  // Atomically replace the whole journal with `data`.
  virtual bool replaceAll(const uint8_t* data, size_t len) = 0;
};

// CRC-16/CCITT-FALSE.
uint16_t crc16(const uint8_t* data, size_t len);

// FIFO of door events.
//
// RAM holds the live queue. Every change is also appended to a journal as a
// fixed-size, CRC-protected record: PUSH (one event) or ACK (n events were
// delivered and removed from the front). At boot the journal is replayed.
// One append per door event and one per acknowledged POST is the only flash
// traffic; nothing is written while idle. When the journal grows past
// `compactAtRecords` it is rewritten as a snapshot of the live queue.
//
// When full, the oldest event is dropped to make room for the newest.
class EventQueue {
 public:
  static const size_t kRecordSize = 24;

  EventQueue(size_t capacity, JournalStore* store, size_t compactAtRecords);

  // Replay the journal. Returns false if the store could not be read (the
  // queue then works in RAM only until a later write succeeds).
  bool load();

  // Add an event. Returns true if an older event had to be dropped.
  bool push(const DoorEventRec& ev);

  size_t size() const { return count_; }
  bool empty() const { return count_ == 0; }
  size_t capacity() const { return cap_; }
  const DoorEventRec& at(size_t i) const { return buf_[(head_ + i) % cap_]; }

  // Remove the `n` oldest events (after the server acknowledged them).
  void popFront(size_t n);

  // Diagnostics.
  bool storeHealthy() const { return storeOk_; }
  size_t journalRecords() const { return journalRecords_; }
  uint32_t corruptRecordsSeen() const { return corruptSeen_; }

 private:
  bool pushRam(const DoorEventRec& ev);
  void popRam(size_t n);
  void journal(uint8_t type, const uint8_t* payload20);
  bool compact();

  size_t cap_;
  JournalStore* store_;
  size_t compactAt_;
  std::vector<DoorEventRec> buf_;
  size_t head_ = 0;
  size_t count_ = 0;
  size_t journalRecords_ = 0;
  bool storeOk_ = false;
  bool needCompact_ = false;
  uint32_t corruptSeen_ = 0;
};

}  // namespace fc
