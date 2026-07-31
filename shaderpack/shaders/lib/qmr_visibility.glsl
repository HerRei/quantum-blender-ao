#ifndef QMR_VISIBILITY_GLSL
#define QMR_VISIBILITY_GLSL

vec3 qmrApplyAmbientVisibility(vec3 baseColor, float visibility, float blendAmount) {
    float boundedVisibility = clamp(visibility, 0.0, 1.0);
    float boundedBlend = clamp(blendAmount, 0.0, 1.0);
    return baseColor * mix(1.0, boundedVisibility, boundedBlend);
}

#endif

