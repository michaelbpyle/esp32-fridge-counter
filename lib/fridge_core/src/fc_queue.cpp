#include "fc_queue.h"

#include <string.h>

namespace fc {

namespace {

const uint8_t kTypePush = 0xE1;
const uint8_t kTypeAck = 0xA7;

void put32(uint8_t* p, uint32_t v) {
  p[0] = (uint8_t)(v);
  p[1] = (uint8_t)(v >> 8);
  p[2] = (uint8_t)(v >> 16);
  p[3] = (uint8_t)(v >> 24);
}

uint32_t get32(const uint8_t* p) {
  return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) |
         ((uint32_t)p[3] << 24);
}

void packEvent(const DoorEventRec& ev, uint8_t* p20) {
  put32(p20 + 0, ev.boot);
  put32(p20 + 4, ev.n);
  put32(p20 + 8, ev.t);
  put32(p20 + 12, (uint32_t)ev.dur_ms);
  put32(p20 + 16, ev.up_s);
}

DoorEventRec unpackEvent(const uint8_t* p20) {
  DoorEventRec ev;
  ev.boot = get32(p20 + 0);
  ev.n = get32(p20 + 4);
  ev.t = get32(p20 + 8);
  ev.dur_ms = (int32_t)get32(p20 + 12);
  ev.up_s = get32(p20 + 16);
  return ev;
}

// Record layout (24 bytes): [0] type, [1] 0x00, [2..3] CRC16 over bytes
// 0,1 and 4..23 (little-endian), [4..23] payload.
void buildRecord(uint8_t type, const uint8_t* payload20, uint8_t* rec) {
  rec[0] = type;
  rec[1] = 0;
  memcpy(rec + 4, payload20, 20);
  uint8_t tmp[22];
  tmp[0] = rec[0];
  tmp[1] = rec[1];
  memcpy(tmp + 2, rec + 4, 20);
  uint16_t c = crc16(tmp, sizeof(tmp));
  rec[2] = (uint8_t)(c);
  rec[3] = (uint8_t)(c >> 8);
}

bool checkRecord(const uint8_t* rec) {
  if (rec[0] != kTypePush && rec[0] != kTypeAck) return false;
  uint8_t tmp[22];
  tmp[0] = rec[0];
  tmp[1] = rec[1];
  memcpy(tmp + 2, rec + 4, 20);
  uint16_t c = crc16(tmp, sizeof(tmp));
  return rec[2] == (uint8_t)(c) && rec[3] == (uint8_t)(c >> 8);
}

}  // namespace

uint16_t crc16(const uint8_t* data, size_t len) {
  uint16_t crc = 0xFFFF;
  for (size_t i = 0; i < len; i++) {
    crc ^= (uint16_t)data[i] << 8;
    for (int b = 0; b < 8; b++) {
      crc = (crc & 0x8000) ? (uint16_t)((crc << 1) ^ 0x1021) : (uint16_t)(crc << 1);
    }
  }
  return crc;
}

EventQueue::EventQueue(size_t capacity, JournalStore* store, size_t compactAtRecords)
    : cap_(capacity ? capacity : 1), store_(store), compactAt_(compactAtRecords) {
  buf_.resize(cap_);
  if (compactAt_ < cap_ + 8) compactAt_ = cap_ + 8;
}

bool EventQueue::pushRam(const DoorEventRec& ev) {
  bool dropped = false;
  if (count_ == cap_) {
    head_ = (head_ + 1) % cap_;
    count_--;
    dropped = true;
  }
  buf_[(head_ + count_) % cap_] = ev;
  count_++;
  return dropped;
}

void EventQueue::popRam(size_t n) {
  if (n > count_) n = count_;
  head_ = (head_ + n) % cap_;
  count_ -= n;
  if (count_ == 0) head_ = 0;
}

bool EventQueue::load() {
  head_ = 0;
  count_ = 0;
  journalRecords_ = 0;
  needCompact_ = false;
  storeOk_ = false;
  if (!store_) return false;

  std::vector<uint8_t> bytes;
  if (!store_->readAll(bytes)) return false;
  storeOk_ = true;

  size_t off = 0;
  while (off + kRecordSize <= bytes.size()) {
    const uint8_t* rec = &bytes[off];
    if (!checkRecord(rec)) {
      // Torn or corrupt record: everything after it is untrustworthy.
      corruptSeen_++;
      needCompact_ = true;
      break;
    }
    if (rec[0] == kTypePush) {
      pushRam(unpackEvent(rec + 4));
    } else {
      popRam(get32(rec + 4));
    }
    journalRecords_++;
    off += kRecordSize;
  }
  if (off != bytes.size()) needCompact_ = true;  // trailing partial record

  // Rewrite a damaged or bloated journal now so later appends land on a
  // clean record boundary.
  if (needCompact_ || journalRecords_ > count_ + 64) compact();
  return true;
}

bool EventQueue::compact() {
  if (!store_) return false;
  std::vector<uint8_t> snap(count_ * kRecordSize);
  uint8_t payload[20];
  for (size_t i = 0; i < count_; i++) {
    packEvent(at(i), payload);
    buildRecord(kTypePush, payload, &snap[i * kRecordSize]);
  }
  bool ok = store_->replaceAll(snap.empty() ? (const uint8_t*)"" : &snap[0], snap.size());
  if (ok) {
    journalRecords_ = count_;
    needCompact_ = false;
  } else {
    needCompact_ = true;
  }
  storeOk_ = ok;
  return ok;
}

void EventQueue::journal(uint8_t type, const uint8_t* payload20) {
  if (!store_) return;
  // If an earlier write failed, the journal no longer matches RAM: only a
  // full snapshot can bring it back in step.
  if (needCompact_ || journalRecords_ + 1 > compactAt_) {
    compact();  // the snapshot already includes this change
    return;
  }
  uint8_t rec[kRecordSize];
  buildRecord(type, payload20, rec);
  if (store_->append(rec, sizeof(rec))) {
    journalRecords_++;
    storeOk_ = true;
  } else {
    storeOk_ = false;
    needCompact_ = true;
  }
}

bool EventQueue::push(const DoorEventRec& ev) {
  bool dropped = pushRam(ev);
  uint8_t payload[20];
  packEvent(ev, payload);
  journal(kTypePush, payload);
  return dropped;
}

void EventQueue::popFront(size_t n) {
  if (n > count_) n = count_;
  if (n == 0) return;
  popRam(n);
  if (count_ == 0 && journalRecords_ >= 32) {
    // Queue drained: an empty snapshot is cheaper than a growing journal.
    compact();
    return;
  }
  uint8_t payload[20];
  memset(payload, 0, sizeof(payload));
  put32(payload, (uint32_t)n);
  journal(kTypeAck, payload);
}

}  // namespace fc
