# CutAndShake — Native Cocoa / Objective-C plugin

This folder contains the Xcode project that builds a native
Objective-C + Interface Builder version of the *CutAndShake*
Glyphs filter plugin.  It is a direct port of the Python plugin
in `../CutAndShake.glyphsFilter` and produces a `.glyphsFilter`
bundle with identical behaviour and the same bundle identifier
(`com.mekkablue.CutAndShake`).

## Project layout

```
Cocoa/
├── CutAndShake.xcodeproj/       Xcode project
│   └── project.pbxproj
├── CutAndShake/
│   ├── CutAndShake.h            Class interface + IBOutlets
│   ├── CutAndShake.m            Filter implementation
│   ├── Info.plist               Bundle metadata
│   └── Base.lproj/
│       └── IBdialog.xib         Dialog layout (Interface Builder)
│   ├── en.lproj/IBdialog.strings
│   ├── de.lproj/IBdialog.strings
│   ├── fr.lproj/IBdialog.strings
│   ├── es.lproj/IBdialog.strings
│   └── zh_CN.lproj/IBdialog.strings
└── LocalConfig.xcconfig         Local build overrides (not in git)
```

## Requirements

| Requirement | Version |
|-------------|---------|
| macOS       | 12 Monterey or later |
| Xcode       | 15 or later |
| Glyphs      | 4.x |

`GSFilterPlugin` moved from the `GlyphsCore` framework to `GlyphsApp`
in Glyphs 4, and `GSFilterPlugin` no longer carries a `_view` ivar, so
the plugin declares its own. A build made against Glyphs 3 headers will
not load in Glyphs 4: dyld rejects the bundle over the missing
`_OBJC_IVAR_$_GSFilterPlugin._view` symbol.

## Building

1. Open `CutAndShake.xcodeproj` in Xcode.
2. Set the active scheme to **CutAndShake**.
3. Make sure `GLYPHS_APP_PATH` resolves correctly.
   The project uses `$(GLYPHS_APP_PATH)/Contents/Frameworks` for
   both the framework and header search paths.
   If Glyphs 4 is installed in a non-standard location, copy
   `LocalConfig.xcconfig` into place and set the path there, then
   add the xcconfig to the project's build configuration.
4. Build the *Release* configuration (⌘B). It builds
   `$(ARCHS_STANDARD)` with `ONLY_ACTIVE_ARCH = NO`, so the product is
   universal (arm64 + x86_64). The product is placed in the standard
   Derived Data folder as `CutAndShake.glyphsFilter`.
5. Copy the bundle to
   `~/Library/Application Support/Glyphs 4/Plugins/`
   and restart Glyphs.

## How it works

| Step | Code |
|------|------|
| **Cut** | `randomCutLayer:numberOfCuts:` makes *N* random horizontal **or** vertical straight cuts through the layer using `+[GlyphsToolKnife cutPathsInLayer:forPoint:endPoint:]` (Glyphs 3 called that class `GlyphsToolOther`; both are looked up at runtime). |
| **Move** | `randomMovePaths:maxMove:` translates each resulting path fragment by a random (dx, dy) whose magnitude ≤ *maxMove* units. |
| **Rotate** | `randomRotatePaths:maxRotate:` rotates each path fragment around its own bounding-box centre by a random angle ≤ *maxRotate* degrees. |

Parameters are stored in `NSUserDefaults` and can be supplied via a
Glyphs *Custom Parameter* at export:

```
CutAndShake; cuts:5; move:50; rotate:20
```

## Linking note

The plugin uses `-undefined dynamic_lookup` so that `GlyphsCore` and
`GlyphsApp` symbols are resolved at runtime from the hosting Glyphs
process. **Do not embed** either framework in the plugin bundle.

Because the symbols are resolved at load time, a single missing one —
a class, or an ivar of a superclass — makes Glyphs drop the plugin
silently. `llvm-nm -u CutAndShake.glyphsFilter/Contents/MacOS/CutAndShake`
lists what the bundle expects the host to provide.
