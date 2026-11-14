// Door sampling task: reads the reed switch every few milliseconds in its
// own high-priority FreeRTOS task, so door edges are never missed while the
// main loop is busy with WiFi, HTTPS or flash writes.
#pragma once

#include <Arduino.h>

#include <fc_types.h>

struct DoorNotice {
  enum Kind : uint8_t { Opened, Closed, Event };
  Kind kind;
  fc::DoorEventRec event;  // valid when kind == Event
};

// Start the task. Call after the task watchdog has been configured.
void doorBegin(uint32_t bootId);

// Fetch the next notice from the door task, if any (never blocks).
bool doorPoll(DoorNotice& out);

bool doorIsOpen();               // debounced state
bool doorHeldOpen();             // open longer than the held-open limit
int doorRawLevel();              // raw pin level right now (HIGH/LOW)
uint32_t doorOpeningsThisBoot();
uint32_t doorNoticesLost();      // notices dropped because the main loop stalled (should stay 0)

// Bench test: pretend the door goes shut -> open for `ms` milliseconds ->
// shut, ignoring the real pin meanwhile. Goes through the same debounce and
// counting path as the real switch. Afterwards the real pin is read again as
// if the device had just started: if it says "open" (for example because no
// reed switch is connected, so the pull-up holds the pin HIGH) that is NOT
// counted as an opening. Works with or without a switch attached.
void doorSimulate(uint32_t ms);
bool doorSimulating();
