// Event-queue journal stored as a file on the LittleFS data partition.
#pragma once

#include <Arduino.h>
#include <FS.h>
#include <LittleFS.h>

#include <sys/stat.h>

#include <fc_queue.h>

class LittleFsJournal : public fc::JournalStore {
 public:
  // Mount the filesystem (formats it on the very first boot).
  bool begin() {
    mounted_ = LittleFS.begin(true);
    if (mounted_ && exists(kTmp)) LittleFS.remove(kTmp);
    return mounted_;
  }
  bool mounted() const { return mounted_; }

  bool readAll(std::vector<uint8_t>& out) override {
    out.clear();
    if (!mounted_) return false;
    if (!exists(kPath)) return true;
    File f = LittleFS.open(kPath, "r");
    if (!f) return false;
    size_t len = f.size();
    out.resize(len);
    size_t got = len ? f.read(&out[0], len) : 0;
    f.close();
    out.resize(got);
    return got == len;
  }

  bool append(const uint8_t* data, size_t len) override {
    if (!mounted_) return false;
    File f = LittleFS.open(kPath, "a");
    if (!f) return false;
    size_t wrote = f.write(data, len);
    f.close();  // close = commit: LittleFS guarantees old-or-new, never torn
    return wrote == len;
  }

  bool replaceAll(const uint8_t* data, size_t len) override {
    if (!mounted_) return false;
    File f = LittleFS.open(kTmp, "w");
    if (!f) return false;
    size_t wrote = len ? f.write(data, len) : 0;
    f.close();
    if (wrote != len) {
      LittleFS.remove(kTmp);
      return false;
    }
    // rename() replaces the old journal atomically.
    return LittleFS.rename(kTmp, kPath);
  }

  
 private:
  // LittleFS.exists() logs an error for a missing file; stat() is silent.
  static bool exists(const char* path) {
    struct stat st;
    String full = String("/littlefs") + path;
    return stat(full.c_str(), &st) == 0;
  }

  static constexpr const char* kPath = "/queue.jnl";
  static constexpr const char* kTmp = "/queue.tmp";
  bool mounted_ = false;
};
