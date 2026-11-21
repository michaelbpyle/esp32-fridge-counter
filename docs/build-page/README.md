# Build page source

Source for the private status page "Fridge Counter Build"
(<https://claude.ai/artifact/WsArBQkyjb76iJjARBP9BY>).

- `template.html` is the page, with `{{IMG:name}}` placeholders where pictures go.
- `build.py` replaces the placeholders with the pictures and writes
  `fridge-counter-build.html` next to itself. Run it with `python build.py`.
- `wiring.png` and `live-fridge.png` are screenshots used by the page. The other pictures
  come from `cad\demo-door\pictures\` and `cad\enclosure\pictures\`.

To update the page, edit `template.html`, run `build.py`, and publish the output to the same
artifact address.
