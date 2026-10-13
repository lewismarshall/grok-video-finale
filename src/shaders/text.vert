#version 410
in vec2 aPos;
in vec2 aUV;
out vec2 vUV;
uniform vec2 uRes;
void main() {
    vec2 ndc;
    ndc.x = (aPos.x / uRes.x) * 2.0 - 1.0;
    ndc.y = 1.0 - (aPos.y / uRes.y) * 2.0;
    gl_Position = vec4(ndc, 0.0, 1.0);
    vUV = aUV;
}
