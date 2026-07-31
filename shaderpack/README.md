# Optional Iris shader-pack scaffold

This directory is a minimal pass-through composite pack based on Iris' official
GLSL 330 compatibility examples. Its effect is disabled by default. When enabled
in Iris settings, a **manual** visibility slider can darken the final image; this
is a diagnostic scaffold, not live service integration.

The actual Iris layout is `shaderpack/shaders/shaders.properties` (the
properties file belongs inside the `shaders` directory).

## Why there is no fabricated mod uniform

The current official Iris documentation says that shaderpack custom uniforms
are expressions composed from existing uniforms, literals, operators, vector
constructors, and documented functions. It does not document a stable public
Fabric extension through which an unrelated mod can register an arbitrary
per-frame float. Therefore this project does not call Iris internals and the
Fabric mod has no Iris dependency.

References checked on 2026-07-31:

- <https://shaders.properties/current/reference/shadersproperties/custom_uniforms/>
- <https://shaders.properties/current/reference/shadersproperties/overview/>
- <https://shaders.properties/current/guides/your-first-shaderpack/1_composite/>

The functioning visualization is the mod's debug HUD. It retains the last valid
result while work is pending and applies exponential smoothing. A future shader
bridge must first select and pin a documented Iris extension point. At that
point, `qmr_visibility.glsl` is the intended application seam; a one-float
uniform or tiny texture would keep per-frame transfers negligible.

## Static check

From the repository root:

```bash
scripts/check-shaders.sh
```

This validates file pairing, version directives, include targets, and balanced
braces. It is not a substitute for loading the pack in an actual Iris client,
which has not been done on the current Mac.

