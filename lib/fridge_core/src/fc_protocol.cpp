#include "fc_protocol.h"

#include <math.h>
#include <stdio.h>
#include <string.h>

namespace fc {

namespace {

void appendU32(std::string& s, uint32_t v) {
  char b[12];
  snprintf(b, sizeof(b), "%lu", (unsigned long)v);
  s += b;
}

void appendI32(std::string& s, int32_t v) {
  char b[13];
  snprintf(b, sizeof(b), "%ld", (long)v);
  s += b;
}

void appendStr(std::string& s, const char* v) {
  s += '"';
  for (const char* p = v ? v : ""; *p; p++) {
    unsigned char c = (unsigned char)*p;
    if (c == '"' || c == '\\') {
      s += '\\';
      s += (char)c;
    } else if (c < 0x20) {
      char b[8];
      snprintf(b, sizeof(b), "\\u%04x", c);
      s += b;
    } else {
      s += (char)c;
    }
  }
  s += '"';
}

void key(std::string& s, const char* k) {
  s += '"';
  s += k;
  s += "\":";
}

}  // namespace

ResolvedTime resolveTime(uint32_t recBoot, uint32_t recT, uint32_t recUpS, uint32_t curBoot,
                         uint32_t curUptimeS, uint32_t nowEpoch) {
  ResolvedTime r;
  r.t = recT;
  r.ageKnown = false;
  r.ageS = 0;
  if (recBoot == curBoot) {
    r.ageKnown = true;
    r.ageS = (curUptimeS >= recUpS) ? (curUptimeS - recUpS) : 0;
    if (r.t == 0 && nowEpoch > r.ageS) r.t = nowEpoch - r.ageS;
  } else if (recT != 0 && nowEpoch >= recT) {
    r.ageKnown = true;
    r.ageS = nowEpoch - recT;
  }
  return r;
}

std::string buildPayload(const PayloadHeader& h, const DoorEventRec* events, size_t nEvents,
                         const ReadingRec* readings, size_t nReadings, const StatusInfo& st) {
  std::string s;
  s.reserve(256 + nEvents * 80 + nReadings * 110);
  s += '{';
  key(s, "device_id"); appendStr(s, h.deviceId); s += ',';
  key(s, "fw"); appendStr(s, h.fw); s += ',';
  key(s, "boot_id"); appendU32(s, h.bootId); s += ',';
  key(s, "uplink"); appendStr(s, h.uplink); s += ',';
  key(s, "sent_at"); appendU32(s, h.sentAt); s += ',';
  key(s, "uptime_s"); appendU32(s, h.uptimeS); s += ',';
  key(s, "door_total"); appendU32(s, h.doorTotal); s += ',';

  key(s, "events");
  s += '[';
  for (size_t i = 0; i < nEvents; i++) {
    const DoorEventRec& e = events[i];
    ResolvedTime rt = resolveTime(e.boot, e.t, e.up_s, h.bootId, h.uptimeS, h.sentAt);
    if (i) s += ',';
    s += '{';
    key(s, "boot"); appendU32(s, e.boot); s += ',';
    key(s, "n"); appendU32(s, e.n); s += ',';
    key(s, "t"); appendU32(s, rt.t); s += ',';
    if (rt.ageKnown) {
      key(s, "age_s"); appendU32(s, rt.ageS); s += ',';
    }
    key(s, "dur_ms"); appendI32(s, e.dur_ms);
    s += '}';
  }
  s += "],";

  key(s, "readings");
  s += '[';
  bool first = true;
  for (size_t i = 0; i < nReadings; i++) {
    const ReadingRec& r = readings[i];
    if (isnan(r.value) || isinf(r.value)) continue;  // not representable in JSON
    ResolvedTime rt = resolveTime(h.bootId, r.t, r.up_s, h.bootId, h.uptimeS, h.sentAt);
    if (!first) s += ',';
    first = false;
    s += '{';
    key(s, "t"); appendU32(s, rt.t); s += ',';
    key(s, "age_s"); appendU32(s, rt.ageS); s += ',';
    key(s, "sensor"); appendStr(s, r.sensor); s += ',';
    key(s, "metric"); appendStr(s, r.metric); s += ',';
    key(s, "value");
    char b[24];
    snprintf(b, sizeof(b), "%.2f", (double)r.value);
    s += b;
    s += '}';
  }
  s += "],";

  key(s, "status");
  s += '{';
  key(s, "rssi"); appendI32(s, st.rssi); s += ',';
  key(s, "heap"); appendU32(s, st.heap); s += ',';
  key(s, "door_open"); s += st.doorOpen ? "true" : "false"; s += ',';
  key(s, "queue"); appendU32(s, st.queue); s += ',';
  key(s, "dropped"); appendU32(s, st.dropped); s += ',';
  key(s, "reset_reason"); appendStr(s, st.resetReason);
  s += "}}";
  return s;
}

namespace {

// Find `"name"` followed by a colon; return index of the first value char.
bool findValue(const std::string& body, const char* name, size_t& pos) {
  std::string needle = std::string("\"") + name + "\"";
  size_t from = 0;
  while (true) {
    size_t k = body.find(needle, from);
    if (k == std::string::npos) return false;
    size_t i = k + needle.size();
    while (i < body.size() && (body[i] == ' ' || body[i] == '\t' || body[i] == '\r' || body[i] == '\n')) i++;
    if (i < body.size() && body[i] == ':') {
      i++;
      while (i < body.size() && (body[i] == ' ' || body[i] == '\t' || body[i] == '\r' || body[i] == '\n')) i++;
      pos = i;
      return i < body.size();
    }
    from = k + 1;
  }
}

bool readU32(const std::string& body, const char* name, uint32_t& out) {
  size_t i;
  if (!findValue(body, name, i)) return false;
  if (body[i] < '0' || body[i] > '9') return false;
  uint64_t v = 0;
  while (i < body.size() && body[i] >= '0' && body[i] <= '9') {
    v = v * 10 + (uint64_t)(body[i] - '0');
    if (v > 0xFFFFFFFFULL) return false;
    i++;
  }
  out = (uint32_t)v;
  return true;
}

}  // namespace

bool parseIngestResponse(const std::string& body, IngestResponse& out) {
  out = IngestResponse();
  size_t start = body.find_first_not_of(" \t\r\n");
  if (start == std::string::npos || body[start] != '{') return false;
  size_t i;
  if (!findValue(body, "ok", i)) return false;
  if (body.compare(i, 4, "true") != 0) return false;
  out.ok = true;
  readU32(body, "accepted", out.accepted);
  readU32(body, "duplicates", out.duplicates);
  readU32(body, "server_time", out.serverTime);
  return true;
}

PostAction classifyResponse(int httpStatus, bool bodyOk) {
  if (httpStatus == 200) return bodyOk ? PostAction::Ack : PostAction::RetryBackoff;
  if (httpStatus == 400) return PostAction::DropBatch;
  if (httpStatus == 401 || httpStatus == 403) return PostAction::RetryAuth;
  return PostAction::RetryBackoff;
}

uint32_t Backoff::next(uint32_t rnd) {
  uint32_t shift = failures_ < 20 ? failures_ : 20;
  uint64_t d = (uint64_t)baseMs_ << shift;
  if (d > maxMs_) d = maxMs_;
  if (failures_ < 1000) failures_++;
  // jitter: 75 % .. 125 %
  uint64_t span = d / 2;
  uint64_t j = span ? (rnd % (span + 1)) : 0;
  uint64_t out = d - d / 4 + j;
  return (uint32_t)(out < 1 ? 1 : out);
}

}  // namespace fc
