#version 410

uniform sampler2D uScene;
uniform sampler2D uBloom;
uniform sampler2D uPhoto;
uniform sampler2D uBands;
uniform vec2 uRes;
uniform float uPhotoMix;
uniform float uGlitch;
uniform float uHole;
uniform float uHud;
uniform float uCard;
uniform float uStreaks;
uniform float uTime;
uniform vec2 uBlur;

out vec4 outColor;

float hash12(vec2 p) {
    vec3 p3 = fract(vec3(p.xyx) * 0.1031);
    p3 += dot(p3, p3.yzx + 33.33);
    return fract((p3.x + p3.y) * p3.z);
}

vec3 tonemap(vec3 x) {
    x *= 1.15;
    const float a = 2.51, b = 0.03, c = 2.43, d = 0.59, e = 0.14;
    return clamp((x * (a * x + b)) / (x * (c * x + d) + e), 0.0, 1.0);
}

vec3 sampleScene(vec2 uv) {
    vec3 s = texture(uScene, uv).rgb;
    vec3 bl = texture(uBloom, uv).rgb;
    return tonemap(s + bl * 0.9);
}

void main() {
    vec2 uv = gl_FragCoord.xy / uRes;
    vec2 px = vec2(gl_FragCoord.x, uRes.y - gl_FragCoord.y);

    vec2 sceneUV = uv;
    sceneUV -= uBlur * 0.0;
    vec3 sceneCol = sampleScene(uv);
    // Directional shutter, cheap and only visible when the camera is moving.
    if (dot(uBlur, uBlur) > 1e-8) {
        sceneCol = 0.4 * sceneCol;
        sceneCol += 0.2 * sampleScene(uv + uBlur);
        sceneCol += 0.2 * sampleScene(uv - uBlur);
        sceneCol += 0.1 * sampleScene(uv + uBlur * 2.0);
        sceneCol += 0.1 * sampleScene(uv - uBlur * 2.0);
    }
    if (uStreaks > 0.01) {
        vec2 d = uv - vec2(0.5, 0.48);
        float ang = atan(d.y, d.x);
        float r = length(d);
        float line = smoothstep(0.55, 0.97, fract(ang * 9.0 - uTime * 1.5));
        sceneCol += line * smoothstep(0.15, 0.75, r) * uStreaks * vec3(0.35, 0.55, 0.7);
    }

    // Photo was uploaded bottom-row-first, so GL uv matches the screen.
    float slice = floor(uv.y * 42.0);
    float shift = (hash12(vec2(slice, floor(uTime * 18.0))) - 0.5) * uGlitch * 0.08;
    vec2 guv = uv;
    guv.x += shift;
    vec3 photo = texture(uPhoto, guv).rgb;
    photo.r = texture(uPhoto, guv + vec2(uGlitch * 0.008, 0.0)).r;
    photo.b = texture(uPhoto, guv - vec2(uGlitch * 0.008, 0.0)).b;

    vec2 holeC = vec2(0.50, 0.60);
    vec2 hd = (uv - holeC) * vec2(uRes.x / uRes.y, 1.0);
    float hdlen = length(hd);
    float hole = smoothstep(uHole + 0.02, uHole - 0.01, hdlen);
    float rim = exp(-pow((hdlen - uHole) * 28.0, 2.0)) * smoothstep(0.0, 0.05, uHole);
    photo += rim * vec3(1.0, 0.45, 0.18) * 0.9;

    vec3 picture = mix(sceneCol, photo, clamp(uPhotoMix, 0.0, 1.0) * (1.0 - hole));
    if (uPhotoMix > 0.98 && uGlitch < 0.001 && uHole < 0.001) {
        picture = texture(uPhoto, uv).rgb;
    }

    // Shrink the shot into the orbital icon the end card borrows from the trilogy.
    float k = clamp(uCard, 0.0, 1.0);
    if (k > 0.001) {
        vec2 center = mix(vec2(960.0, 540.0), vec2(960.0, 268.0), k);
        float rad = mix(1200.0, 198.0, k);
        vec2 duv = vec2(
            (px.x - center.x) / (2.0 * rad) + 0.5,
            (center.y - px.y) / (2.0 * rad) + 0.5
        );
        vec3 icon = sampleScene(clamp(duv, 0.0, 1.0));
        float inside = 1.0 - smoothstep(rad - 1.5, rad + 10.0, length(px - center));
        vec3 bg = vec3(0.008, 0.016, 0.034);
        vec3 cardLook = mix(bg, icon, inside);
        // Soft ring, same cyan as the broadcast chrome.
        float ring = exp(-pow((length(px - center) - rad) * 0.08, 2.0));
        cardLook += ring * vec3(0.15, 0.55, 0.75) * k;
        picture = mix(picture, cardLook, smoothstep(0.0, 0.25, k));
    }

    float vig = smoothstep(1.15, 0.28, length((uv - 0.5) * vec2(1.2, 1.0)));
    picture *= mix(1.0, vig, 0.45 * (1.0 - uPhotoMix));
    if (uPhotoMix < 0.98) {
        picture += (hash12(gl_FragCoord.xy + fract(uTime) * 17.0) - 0.5) / 255.0;
    }

    // Broadcast brackets.
    float hud = uHud * (1.0 - smoothstep(0.2, 0.85, k) * 0.2);
    if (hud > 0.01) {
        float thick = 1.6;
        float len = 26.0;
        vec2 corners[4] = vec2[](vec2(36.0, 32.0), vec2(1884.0, 32.0), vec2(36.0, 1048.0), vec2(1884.0, 1048.0));
        vec2 flips[4] = vec2[](vec2(1.0, 1.0), vec2(-1.0, 1.0), vec2(1.0, -1.0), vec2(-1.0, -1.0));
        float br = 0.0;
        for (int i = 0; i < 4; i++) {
            vec2 d = (px - corners[i]) * flips[i];
            float h = step(0.0, d.x) * step(d.x, len) * step(abs(d.y), thick);
            float v = step(0.0, d.y) * step(d.y, len) * step(abs(d.x), thick);
            br = max(br, max(h, v));
        }
        float top = step(abs(px.y - 64.0), 0.7) * step(48.0, px.x) * step(px.x, 1872.0);
        float bot = step(abs(px.y - 1016.0), 0.7) * step(48.0, px.x) * step(px.x, 1872.0);
        vec3 cyan = vec3(0.25, 0.85, 1.0);
        picture = mix(picture, cyan, max(br, max(top, bot) * 0.65) * hud);

        if (k < 0.65 && px.x > 1568.0 && px.x < 1890.0 && px.y > 960.0 && px.y < 1012.0) {
            float idx = floor((px.x - 1576.0) / 9.0);
            if (idx >= 0.0 && idx < 32.0) {
                float x0 = 1576.0 + idx * 9.0;
                float bh = texture(uBands, vec2((idx + 0.5) / 32.0, 0.5)).r * 42.0 * hud;
                if (px.x >= x0 && px.x < x0 + 6.0 && px.y > 1006.0 - bh && px.y < 1006.0) {
                    vec3 bar = mix(vec3(0.2, 0.85, 1.0), vec3(1.0, 0.45, 0.3), clamp(bh / 42.0, 0.0, 1.0));
                    picture = mix(picture, bar, hud);
                }
            }
        }
    }

    outColor = vec4(picture, 1.0);
}
