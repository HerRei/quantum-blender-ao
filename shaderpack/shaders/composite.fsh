#version 330 compatibility

#include "/lib/qmr_visibility.glsl"

uniform sampler2D colortex0;

in vec2 texcoord;

/* RENDERTARGETS: 0 */
layout(location = 0) out vec4 color;

// Iris exposes these as shader-pack settings. They are manual diagnostics only.
#define QMR_EXPERIMENTAL_LIGHTING 0 // [0 1]
#define QMR_MANUAL_VISIBILITY 100 // [0 10 20 30 40 50 60 70 80 90 100]
#define QMR_BLEND_PERCENT 35 // [0 10 20 30 40 50 60 70 80 90 100]

void main() {
    color = texture(colortex0, texcoord);
    float enabled = float(QMR_EXPERIMENTAL_LIGHTING);
    float visibility = float(QMR_MANUAL_VISIBILITY) / 100.0;
    float blendAmount = enabled * float(QMR_BLEND_PERCENT) / 100.0;
    color.rgb = qmrApplyAmbientVisibility(color.rgb, visibility, blendAmount);
}

