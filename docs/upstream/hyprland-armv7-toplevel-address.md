# Toplevel mapping addresses are sign-extended on 32-bit ARM

Submitted on 2026-11-16 with the user's approval:
[hyprwm/Hyprland#17017](https://github.com/hyprwm/Hyprland/issues/17017).
The issue was closed automatically because Hyprland accepts new reports
through Discussions. On 2026-11-18, the repository's
[AI policy](https://github.com/hyprwm/.github/blob/main/policies/AI_USAGE.md),
[AGENTS.md](https://github.com/hyprwm/Hyprland/blob/main/AGENTS.md) and
[issue guidelines](https://wiki.hypr.land/contributing-and-debugging/issue-guidelines/)
were checked: an AI agent must not write or publish a Discussion. A human
must independently review the observations and submit their own report.

## Environment and observed behaviour

- ASUS Nexus 7 2013 (flo), APQ8064 / Adreno 320, postmarketOS armv7.
- Hyprland 0.54.3, commit `521ece463c4a9d3d128670688a34756805a4328f`.
- Quickshell 0.3.2, using both Hyprland IPC and
  `hyprland_toplevel_mapping_v1` to associate foreign toplevels.

For the same window, Hyprland IPC reports address `a8802720` while the
toplevel mapping protocol reports `ffffffffa8802720` (high word
`0xffffffff`, low word `0xa8802720`). Quickshell consequently creates two
toplevel entries for one real window. On close, the entry identified by
the IPC address disappears, but the other remains in the overview. We
observed six shell entries while there were no remaining open windows.

Expected: both interfaces identify the same window. On a 32-bit build,
the high word of its protocol address should be zero.

## Source analysis

Both mapping callbacks in
[`src/protocols/ToplevelMapping.cpp` at v0.54.3](https://github.com/hyprwm/Hyprland/blob/v0.54.3/src/protocols/ToplevelMapping.cpp)
cast a window pointer directly to `uint64_t`:

```cpp
rc<uint64_t>(WINDOW.get())
```

The same expression is present in
[`main`, inspected on 2026-11-16](https://github.com/hyprwm/Hyprland/blob/main/src/protocols/ToplevelMapping.cpp).
Runtime reproduction on main has not been performed. Direct pointer
widening is the suspected cause of the observed sign extension; using an
unsigned pointer-sized intermediate avoids relying on that conversion.

Proposed change in both `get_window_for_toplevel` and
`get_window_for_toplevel_wlr` callbacks:

```cpp
else {
    const auto ADDRESS = static_cast<uint64_t>(rc<uintptr_t>(WINDOW.get()));
    NEWHANDLE->m_resource->sendWindowAddress(ADDRESS >> 32 & 0xFFFFFFFF,
                                           ADDRESS & 0xFFFFFFFF);
}
```

This proposal has not yet been built or tested in Hyprland. On a 64-bit
target it preserves the original pointer value.

## Reproduction

1. Run the unpatched Hyprland 0.54.3 and Quickshell 0.3.2 on armv7.
2. Use a Quickshell configuration exposing `Hyprland.toplevels.values`
   and foreign-toplevel mapping (flo-shell overview was the reproducer).
3. Open several Wayland applications and compare each shell entry's
   address with `hyprctl -j clients`.
4. For a pointer whose low word has bit 31 set, observe that the protocol
   address starts with `ffffffff`, unlike IPC.
5. Close the applications. Observe the stale duplicate entries.

Suggested upstream verification: test both protocol callbacks on 32-bit
and 64-bit builds, with pointer bit 31 both set and clear, and compare
their combined 64-bit result with the IPC address.

## Local workaround

The deployed Quickshell 0.3.2-r1 normalises addresses only when
`QT_POINTER_SIZE == 4`, `addressHi == 0xffffffff` and bit 31 of
`addressLo` is set. After applying it, shell window counts agree with
`hyprctl clients`, including after all windows close. This supports the
address mismatch diagnosis but is not a substitute for testing the
proposed compositor change.
