#version 410
uniform sampler2D uTex;
uniform vec2 uRes;
out vec4 outColor;
void main() {
    vec2 uv = gl_FragCoord.xy / uRes;
    vec3 c = texture(uTex, uv).rgb;
    vec3 b = max(c - vec3(0.62), 0.0);
    outColor = vec4(b, 1.0);
}
