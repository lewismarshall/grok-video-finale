#version 410
in vec4 vColor;
out vec4 outColor;
void main() {
    float d = length(gl_PointCoord - vec2(0.5));
    if (d > 0.5) discard;
    float a = smoothstep(0.5, 0.08, d);
    outColor = vec4(vColor.rgb * a * vColor.a, a);
}
