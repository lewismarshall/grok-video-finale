#version 410
in vec4 aPosSize;
in vec4 aColor;
out vec4 vColor;
uniform mat4 uView;
uniform mat4 uProj;
uniform vec2 uRes;
void main() {
    vec4 clip = uProj * uView * vec4(aPosSize.xyz, 1.0);
    if (clip.w < 0.08) {
        gl_Position = vec4(4.0, 4.0, 4.0, 1.0);
        gl_PointSize = 1.0;
        vColor = vec4(0.0);
        return;
    }
    gl_Position = clip;
    gl_PointSize = clamp(aPosSize.w * uRes.y / clip.w, 1.0, 22.0);
    vColor = aColor;
}
