#version 410
uniform sampler2D uTex;
uniform float uAlpha;
in vec2 vUV;
out vec4 outColor;
void main() {
    vec4 c = texture(uTex, vUV);
    c.a *= uAlpha;
    outColor = c;
}
