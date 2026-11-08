# Target laptop acceptance — all pending

This cloud host has no /dev/snd and no PipeWire or mpv executable. Browser rendering
in headless Chromium proves neither physical desktop output nor audio behavior.

Follow DEVELOPMENT_PLAN.md stages 2, 4–8 and the acceptance matrix before deployment:
1. Inventory the actual graphical session, PipeWire graph, stable microphone identity,
   CPU/RAM, and output devices. Do not alter active audio routing during use.
2. Implement capture/worker adapters, then test labeled speech, quiet speech, noise,
   microphone disconnect/reconnect and a 30-minute continuous session. Measure WER,
   meaning preservation, endpoint latency, backlog, dropped audio and memory.
3. Implement private HTTPS authorization, then test an authorized phone on cellular
   against home Wi-Fi, network switches, browser backgrounding and unauthorized access.
4. Integrate mpv and verify actual screen/speakers, observed pause/seek/volume/stop,
   expired commands and local mute/stop during fullscreen playback.
5. Configure and inspect echo reference routing with operator approval. Test speech,
   playback alone, and both at intended seating distance/volume. A room television is
   a separate adverse source. Record aggregate results, not private transcripts.
6. Implement user services and verify login/reboot/suspend/recovery, SQLite restore and
   rollback. Suspended laptops cannot record.
7. Measure the full 8-hour and 24-hour qualification runs. Do not release until gates pass.

No system service, remote desktop, VPN client, audio route, auto-login, or reboot setting
has been installed or modified by this implementation.
