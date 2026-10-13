#version 410
uniform sampler2D uTex;
uniform vec2 uDir;
uniform vec2 uRes;
out vec4 outColor;
void main() {
    vec2 uv = gl_FragCoord.xy / uRes;
    vec2 texel = uDir / uRes;
    vec3 c = texture(uTex, uv).rgb * 0.227027;
    c += texture(uTex, uv + texel * 1.0).rgb * 0.194596;
    c += texture(uTex, uv - texel * 1.0).rgb * 0.194596;
    c += texture(uTex, uv + texel * 2.0).rgb * 0.121622;
    c += texture(uTex, uv - texel * 2.0).rgb * 0.121622;
    c += texture(uTex, uv + texel * 3.0).rgb * 0.054054;
    c += texture(uTex, uv - texel * 3.0).rgb * 0.054054;
    c += texture(uTex, uv + texel * 4.0).rgb * 0.016216;
    c += texture(uTex, uv - texel * 4.0).rgb * 0.016216;
    outColor = vec4(c, 1.0);
}
