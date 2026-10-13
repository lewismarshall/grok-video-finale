#version 410

uniform vec2 uRes;
uniform float uTime;
uniform float uFov;
uniform float uAspect;
uniform vec3 uCamPos;
uniform vec3 uForward;
uniform vec3 uRight;
uniform vec3 uUp;

uniform vec3 uRocketPos;
uniform vec3 uRx;
uniform vec3 uRy;
uniform vec3 uRz;
uniform float uSquash;
uniform float uFlame;
uniform float uShowRocket;
uniform vec3 uLook;

uniform vec3 uAL0, uAL1, uAL2, uAL3, uAL4;
uniform vec3 uAR0, uAR1, uAR2, uAR3, uAR4;

uniform vec3 uArgon;
uniform vec3 uTri;
uniform vec3 uKnot;
uniform float uShowArgon;
uniform float uShowTri;
uniform float uShowKnot;
uniform float uChaos;

uniform vec3 uChairA;
uniform vec3 uChairB;
uniform float uShowChairs;

uniform vec3 uMoonC;
uniform float uMoonR;
uniform float uShowMoon;
uniform vec3 uMoon2;
uniform float uMoon2R;
uniform float uShowMoon2;

uniform vec3 uFlag;
uniform float uShowFlag;
uniform sampler2D uFlagTex;

uniform vec3 uBanana;
uniform float uBananaYaw;
uniform float uBananaSplit;
uniform float uShowBanana;
uniform float uShades;

uniform float uShockR;
uniform float uShockG;
uniform float uGround;

uniform mat4 uView;
uniform mat4 uProj;

out vec4 outColor;

struct Hit {
    float d;
    float id;
};

Hit H(float d, float id) {
    Hit h;
    h.d = d;
    h.id = id;
    return h;
}

Hit U(Hit a, Hit b) {
    if (a.d < b.d) return a;
    return b;
}

mat2 rot(float a) {
    float c = cos(a), s = sin(a);
    return mat2(c, -s, s, c);
}

float sdSphere(vec3 p, float r) { return length(p) - r; }

float sdBox(vec3 p, vec3 b) {
    vec3 q = abs(p) - b;
    return length(max(q, 0.0)) + min(max(q.x, max(q.y, q.z)), 0.0);
}

float sdCapsule(vec3 p, vec3 a, vec3 b, float r) {
    vec3 pa = p - a;
    vec3 ba = b - a;
    float h = clamp(dot(pa, ba) / max(dot(ba, ba), 1e-6), 0.0, 1.0);
    return length(pa - ba * h) - r;
}

float sdTorus(vec3 p, vec2 t) {
    vec2 q = vec2(length(p.xz) - t.x, p.y);
    return length(q) - t.y;
}

float sdCappedCone(vec3 p, float h, float r1, float r2) {
    vec2 q = vec2(length(p.xz), p.y);
    vec2 k1 = vec2(r2, h);
    vec2 k2 = vec2(r2 - r1, 2.0 * h);
    vec2 ca = vec2(q.x - min(q.x, (q.y < 0.0) ? r1 : r2), abs(q.y) - h);
    vec2 cb = q - k1 + k2 * clamp(dot(k1 - q, k2) / max(dot(k2, k2), 1e-6), 0.0, 1.0);
    float s = (cb.x < 0.0 && ca.y < 0.0) ? -1.0 : 1.0;
    return s * sqrt(min(dot(ca, ca), dot(cb, cb)));
}

float hash13(vec3 p) {
    p = fract(p * 0.1031);
    p += dot(p, p.zyx + 31.32);
    return fract((p.x + p.y) * p.z);
}

float vnoise(vec3 p) {
    vec3 i = floor(p);
    vec3 f = fract(p);
    f = f * f * (3.0 - 2.0 * f);
    float n000 = hash13(i);
    float n100 = hash13(i + vec3(1, 0, 0));
    float n010 = hash13(i + vec3(0, 1, 0));
    float n110 = hash13(i + vec3(1, 1, 0));
    float n001 = hash13(i + vec3(0, 0, 1));
    float n101 = hash13(i + vec3(1, 0, 1));
    float n011 = hash13(i + vec3(0, 1, 1));
    float n111 = hash13(i + vec3(1, 1, 1));
    return mix(
        mix(mix(n000, n100, f.x), mix(n010, n110, f.x), f.y),
        mix(mix(n001, n101, f.x), mix(n011, n111, f.x), f.y),
        f.z
    );
}

vec3 toRocket(vec3 p) {
    vec3 q = p - uRocketPos;
    float sq = max(uSquash, 0.45);
    q = vec3(dot(q, uRx), dot(q, uRy) / sq, dot(q, uRz));
    return q;
}

float rocketScale() { return max(uSquash, 0.45); }

Hit moonHit(vec3 p) {
    // Clean sphere. Craters live in the shading, so the normals stay a moon
    // and not a pile of shading ridges.
    return H(length(p - uMoonC) - uMoonR, 1.0);
}

Hit rocketHit(vec3 p) {
    vec3 q = toRocket(p);
    float sc = rocketScale();
    q /= 1.35;
    float body = sdCapsule(q, vec3(0.0, 0.48, 0.0), vec3(0.0, 1.12, 0.0), 0.23);
    float nose = sdSphere(q - vec3(0.0, 1.22, 0.0), 0.22);
    float dBody = body;
    float dNose = nose;
    float k = 0.09;
    float h = clamp(0.5 + 0.5 * (dNose - dBody) / k, 0.0, 1.0);
    float d = mix(dNose, dBody, h) - k * h * (1.0 - h);
    float id = dBody < dNose ? 3.0 : 4.0;

    float fins = 1e5;
    for (int i = 0; i < 3; i++) {
        vec3 f = q;
        f.xz = rot(float(i) * 2.094395) * f.xz;
        f -= vec3(0.30, 0.52, 0.0);
        fins = min(fins, sdBox(f, vec3(0.15, 0.20, 0.028)));
    }
    if (fins < d) { d = fins; id = 5.0; }

    float stripe = sdTorus(q - vec3(0.0, 0.86, 0.0), vec2(0.25, 0.022));
    if (stripe < d) { d = stripe; id = 25.0; }

    vec3 lookW = uLook - uRocketPos;
    vec3 lookL = normalize(vec3(dot(lookW, uRx), dot(lookW, uRy), dot(lookW, uRz)));
    vec3 eyeL = vec3(-0.10, 0.92, 0.22);
    vec3 eyeR = vec3(0.10, 0.92, 0.22);
    float eyes = min(sdSphere(q - eyeL, 0.075), sdSphere(q - eyeR, 0.075));
    if (eyes < d) { d = eyes; id = 6.0; }
    vec3 pupOff = vec3(clamp(lookL.x, -0.45, 0.45), clamp(lookL.y, -0.35, 0.35), 0.85);
    pupOff = normalize(pupOff) * 0.055;
    vec3 pupL = eyeL + pupOff;
    vec3 pupR = eyeR + pupOff;
    float pups = min(sdSphere(q - pupL, 0.032), sdSphere(q - pupR, 0.032));
    if (pups < d) { d = pups; id = 7.0; }

    float smile = sdTorus(q - vec3(0.0, 0.78, 0.20), vec2(0.09, 0.016));
    smile = max(smile, q.y - 0.78);
    if (smile < d) { d = smile; id = 8.0; }

    if (uFlame > 0.02) {
        vec3 f = q;
        float wob = sin(q.y * 22.0 - uTime * 28.0) * 0.03;
        f.x += wob;
        f.z += cos(q.y * 18.0 - uTime * 24.0) * 0.03;
        float len = 0.15 + 0.85 * uFlame;
        float fl = sdCappedCone(f - vec3(0.0, 0.22 - len * 0.5, 0.0), len * 0.5, 0.05, 0.16 + 0.05 * uFlame);
        if (fl < d) { d = fl; id = 9.0; }
    }
    return H(d * sc * 1.35, id);
}

Hit armHit(vec3 p) {
    float d = sdCapsule(p, uAL0, uAL1, 0.055);
    d = min(d, sdCapsule(p, uAL1, uAL2, 0.042));
    d = min(d, sdCapsule(p, uAL2, uAL3, 0.026));
    d = min(d, sdCapsule(p, uAL2, uAL4, 0.026));
    d = min(d, sdSphere(p - uAL1, 0.072));
    d = min(d, sdSphere(p - uAL2, 0.052));
    d = min(d, sdCapsule(p, uAR0, uAR1, 0.055));
    d = min(d, sdCapsule(p, uAR1, uAR2, 0.042));
    d = min(d, sdCapsule(p, uAR2, uAR3, 0.026));
    d = min(d, sdCapsule(p, uAR2, uAR4, 0.026));
    d = min(d, sdSphere(p - uAR1, 0.072));
    d = min(d, sdSphere(p - uAR2, 0.052));
    return H(d, 10.0);
}

Hit argonHit(vec3 p) {
    vec3 q = p - uArgon;
    float d = sdSphere(q, 0.16);
    float id = 11.0;
    float ring = sdTorus(q, vec2(0.40, 0.010));
    vec3 q2 = q;
    q2.xy = rot(0.7) * q2.xy;
    ring = min(ring, sdTorus(q2, vec2(0.62, 0.010)));
    vec3 q3 = q;
    q3.yz = rot(1.05) * q3.yz;
    ring = min(ring, sdTorus(q3, vec2(0.84, 0.010)));
    if (ring < d) { d = ring; id = 13.0; }
    if (length(q) < 1.7) {
        for (int i = 0; i < 6; i++) {
            float a = uTime * 1.3 + float(i) * 1.0472;
            float spread = 1.0 + uChaos * (0.4 + 0.35 * float(i));
            vec3 e = vec3(cos(a), 0.0, sin(a)) * 0.62 * spread;
            e.xy = rot(0.7) * e.xy;
            float de = sdSphere(q - e, 0.032);
            if (de < d) { d = de; id = 12.0; }
        }
        for (int i = 0; i < 2; i++) {
            float a = -uTime * 1.8 + float(i) * 3.1416;
            vec3 e = vec3(cos(a) * 0.40, 0.0, sin(a) * 0.40);
            float de = sdSphere(q - e, 0.03);
            if (de < d) { d = de; id = 12.0; }
        }
    }
    return H(d, id);
}

Hit triHit(vec3 p) {
    vec3 q = p - uTri;
    float d = 1e5;
    for (int i = 0; i < 6; i++) {
        float a = float(i) * 1.9 + uTime * 0.35;
        vec3 c = vec3(sin(a) * 0.20, cos(a * 1.3) * 0.16, cos(a) * 0.18);
        vec3 b = q - c;
        b.xy = rot(a) * b.xy;
        b.yz = rot(a * 0.6) * b.yz;
        d = min(d, sdBox(b, vec3(0.15, 0.11, 0.012)));
    }
    d = min(d, sdBox(q - vec3(-0.07, 0.08, 0.16), vec3(0.045, 0.035, 0.014)));
    d = min(d, sdBox(q - vec3(0.07, 0.08, 0.16), vec3(0.045, 0.035, 0.014)));
    return H(d, 14.0);
}

Hit knotHit(vec3 p) {
    vec3 q = p - uKnot;
    q.xz = rot(uTime * 0.6) * q.xz;
    q.xy = rot(uTime * 0.35) * q.xy;
    float d = sdTorus(q, vec2(0.42, 0.028));
    vec3 a = q;
    a.xy = rot(1.15) * a.xy;
    d = min(d, sdTorus(a, vec2(0.42, 0.026)));
    vec3 b = q;
    b.yz = rot(0.85) * b.yz;
    d = min(d, sdTorus(b, vec2(0.34, 0.024)));
    return H(d, 20.0);
}

Hit chairHit(vec3 p, vec3 c) {
    vec3 q = p - c;
    float seat = sdBox(q - vec3(0.0, 0.28, 0.0), vec3(0.24, 0.03, 0.22));
    float back = sdBox(q - vec3(0.0, 0.55, -0.19), vec3(0.24, 0.26, 0.025));
    float d = min(seat, back);
    d = min(d, sdCapsule(q, vec3(-0.18, 0.0, -0.16), vec3(-0.18, 0.26, -0.16), 0.02));
    d = min(d, sdCapsule(q, vec3(0.18, 0.0, -0.16), vec3(0.18, 0.26, -0.16), 0.02));
    d = min(d, sdCapsule(q, vec3(-0.18, 0.0, 0.16), vec3(-0.18, 0.26, 0.16), 0.02));
    d = min(d, sdCapsule(q, vec3(0.18, 0.0, 0.16), vec3(0.18, 0.26, 0.16), 0.02));
    return H(d, 17.0);
}

Hit flagHit(vec3 p) {
    vec3 q = p - uFlag;
    float pole = sdCapsule(q, vec3(0.0, 0.0, 0.0), vec3(0.0, 1.25, 0.0), 0.025);
    float wave = sin(q.x * 10.0 + uTime * 5.5) * 0.045 * smoothstep(0.02, 0.2, q.x);
    vec3 f = q;
    f.z -= wave;
    f.x -= 0.30;
    f.y -= 1.05;
    float cloth = sdBox(f, vec3(0.28, 0.16, 0.012));
    if (cloth < pole) return H(cloth, 15.0);
    return H(pole, 16.0);
}

float bananaPrim(vec3 q) {
    float d = sdCapsule(q, vec3(-0.16, 0.07, 0.0), vec3(0.14, -0.04, 0.0), 0.05);
    float stem = sdSphere(q - vec3(0.16, 0.12, 0.0), 0.028);
    return min(d, stem);
}

Hit bananaHit(vec3 p) {
    float yaw = radians(uBananaYaw);
    vec3 axis = p - uBanana;
    axis.xz = rot(yaw) * axis.xz;
    if (uBananaSplit < 0.02) {
        float d = bananaPrim(axis);
        if (sdSphere(axis - vec3(0.16, 0.12, 0.0), 0.028) < d) return H(d, 19.0);
        return H(d, 18.0);
    }
    vec3 left = axis - vec3(-uBananaSplit * 0.28, 0.02, 0.0);
    vec3 right = axis - vec3(uBananaSplit * 0.28, 0.0, 0.0);
    left.x += 0.08;
    right.x -= 0.08;
    float d1 = bananaPrim(left);
    float d2 = bananaPrim(right);
    return H(min(d1, d2), 18.0);
}

Hit shadesHit(vec3 p, vec3 face) {
    vec3 q = p - face - vec3(0.0, 0.08, 0.16);
    float s = max(uShades, 0.001);
    q /= s;
    float d = sdSphere(q - vec3(-0.10, 0.0, 0.0), 0.055);
    d = min(d, sdSphere(q - vec3(0.10, 0.0, 0.0), 0.055));
    d = min(d, sdCapsule(q, vec3(-0.05, 0.0, 0.0), vec3(0.05, 0.0, 0.0), 0.012));
    return H(d * s, 21.0);
}

Hit moon2Hit(vec3 p) {
    vec3 q = p - uMoon2;
    float d = length(q) - uMoon2R;
    vec3 h = q - vec3(0.0, uMoon2R * 0.92, 0.0);
    float hat = sdCappedCone(h - vec3(0.0, 0.16, 0.0), 0.16, 0.20, 0.01);
    float id = 2.0;
    if (hat < d) { d = hat; id = 22.0; }
    float pom = sdSphere(q - vec3(0.0, uMoon2R + 0.48, 0.0), 0.06);
    if (pom < d) { d = pom; id = 23.0; }
    return H(d, id);
}

Hit mapHit(vec3 p) {
    Hit h = H(1e5, 0.0);
    if (uShowMoon > 0.5) h = U(h, moonHit(p));
    if (uShowMoon2 > 0.5) h = U(h, moon2Hit(p));
    if (uShowRocket > 0.5) {
        h = U(h, rocketHit(p));
        h = U(h, armHit(p));
    }
    if (uShowArgon > 0.5) h = U(h, argonHit(p));
    if (uShowTri > 0.5) h = U(h, triHit(p));
    if (uShowKnot > 0.5) h = U(h, knotHit(p));
    if (uShowChairs > 0.5) {
        h = U(h, chairHit(p, uChairA));
        h = U(h, chairHit(p, uChairB));
    }
    if (uShowFlag > 0.5) h = U(h, flagHit(p));
    if (uShowBanana > 0.5) h = U(h, bananaHit(p));
    if (uShades > 0.04 && uShowArgon > 0.5) h = U(h, shadesHit(p, uArgon));
    if (uShades > 0.04 && uShowTri > 0.5) h = U(h, shadesHit(p, uTri));
    if (uShockG > 0.02) {
        vec3 q = p - vec3(uRocketPos.x, uGround + 0.04, uRocketPos.z);
        float sh = sdTorus(q, vec2(max(uShockR, 0.05), 0.025 + uShockR * 0.01));
        h = U(h, H(sh, 24.0));
    }
    return h;
}

float mapDist(vec3 p) { return mapHit(p).d; }

vec3 calcNormal(vec3 p) {
    vec2 e = vec2(1.0, -1.0) * 0.0035;
    return normalize(
        e.xyy * mapDist(p + e.xyy) +
        e.yyx * mapDist(p + e.yyx) +
        e.yxy * mapDist(p + e.yxy) +
        e.xxx * mapDist(p + e.xxx)
    );
}

float softShadow(vec3 ro, vec3 rd) {
    float res = 1.0;
    float t = 0.08;
    for (int i = 0; i < 7; i++) {
        float h = mapDist(ro + rd * t);
        if (h < 0.003) return 0.35;
        res = min(res, 14.0 * h / t);
        t += clamp(h, 0.04, 0.55);
        if (t > 8.0) break;
    }
    return clamp(res, 0.35, 1.0);
}

vec3 sky(vec3 rd) {
    float g = clamp(rd.y * 0.55 + 0.35, 0.0, 1.0);
    vec3 col = mix(vec3(0.004, 0.016, 0.038), vec3(0.03, 0.07, 0.14), g);
    float band = exp(-9.0 * abs(rd.y * 0.85 + rd.x * 0.18));
    col += band * vec3(0.04, 0.07, 0.12);
    vec3 cell = floor(rd * 240.0);
    float h = hash13(cell);
    float star = smoothstep(0.986, 1.0, h);
    float tw = 0.65 + 0.35 * sin(uTime * 2.2 + h * 50.0);
    vec3 scol = h > 0.996 ? vec3(1.0, 0.78, 0.55) : vec3(0.75, 0.86, 1.0);
    col += star * tw * scol;
    return col;
}

bool emissiveId(float id) {
    return id == 6.0 || id == 9.0 || id == 11.0 || id == 12.0 || id == 20.0 || id == 24.0 || id == 25.0 || id == 14.0;
}

vec3 shade(vec3 p, vec3 n, vec3 rd, float id) {
    vec3 light = normalize(vec3(0.45, 0.85, 0.35));
    vec3 key = vec3(1.0, 0.96, 0.9);
    vec3 fill = vec3(0.25, 0.45, 0.7);
    float diff = clamp(dot(n, light), 0.0, 1.0);
    float sha = 1.0;
    if (!emissiveId(id)) sha = softShadow(p + n * 0.03, light);
    float ao1 = clamp(mapDist(p + n * 0.09) / 0.09, 0.0, 1.0);
    float ao2 = clamp(mapDist(p + n * 0.22) / 0.22, 0.0, 1.0);
    float ao = 0.45 + 0.55 * min(ao1, ao2);
    vec3 halfv = normalize(light - rd);
    float spec = pow(clamp(dot(n, halfv), 0.0, 1.0), 48.0) * sha;

    vec3 alb = vec3(0.8);
    vec3 emis = vec3(0.0);
    float rough = 0.4;
    if (id == 1.0) {
        vec3 geo = normalize(p - uMoonC);
        n = normalize(mix(geo, n, 0.25));
        float dust = vnoise(geo * 9.0);
        float crater = smoothstep(0.62, 0.78, vnoise(geo * 4.0));
        alb = vec3(0.62, 0.64, 0.68) * (0.82 + 0.28 * dust) * (1.0 - 0.28 * crater);
        emis += pow(clamp(1.0 - geo.y, 0.0, 1.0), 3.0) * vec3(0.04, 0.08, 0.16);
    } else if (id == 2.0) {
        alb = vec3(0.68, 0.62, 0.66);
    } else if (id == 3.0) {
        alb = vec3(0.93, 0.94, 0.96);
        rough = 0.25;
    } else if (id == 4.0 || id == 5.0) {
        alb = vec3(1.0, 0.34, 0.24);
        emis = vec3(0.18, 0.03, 0.01);
    } else if (id == 25.0) {
        alb = vec3(0.35, 0.9, 1.0);
        emis = vec3(0.4, 1.3, 1.6);
    } else if (id == 6.0) {
        alb = vec3(1.0);
        emis = vec3(1.4, 1.25, 0.7);
    } else if (id == 7.0 || id == 8.0) {
        alb = vec3(0.08, 0.07, 0.1);
    } else if (id == 9.0) {
        alb = vec3(1.0, 0.45, 0.1);
        emis = vec3(3.2, 1.3, 0.25);
    } else if (id == 10.0) {
        alb = vec3(0.72, 0.74, 0.78);
        rough = 0.3;
    } else if (id == 11.0) {
        alb = vec3(0.85, 0.95, 1.0);
        emis = vec3(0.7, 1.1, 1.6);
    } else if (id == 12.0) {
        alb = vec3(1.0);
        emis = vec3(1.6, 2.2, 2.6);
    } else if (id == 13.0) {
        alb = vec3(0.6, 0.85, 1.0);
        emis = vec3(0.15, 0.35, 0.5);
    } else if (id == 14.0) {
        alb = vec3(0.45, 0.65, 1.0);
        emis = vec3(0.25, 0.45, 1.4);
    } else if (id == 15.0) {
        vec3 q = p - uFlag;
        float u = clamp(q.x / 0.56, 0.0, 1.0);
        float v = clamp((q.y - 0.89) / 0.32, 0.0, 1.0);
        if (dot(n, normalize(uCamPos - p)) < 0.0) u = 1.0 - u;
        alb = texture(uFlagTex, vec2(u, v)).rgb;
    } else if (id == 16.0) {
        alb = vec3(0.85, 0.86, 0.9);
    } else if (id == 17.0) {
        alb = vec3(0.92, 0.9, 0.84);
    } else if (id == 18.0) {
        alb = vec3(0.98, 0.86, 0.22);
    } else if (id == 19.0) {
        alb = vec3(0.35, 0.22, 0.1);
    } else if (id == 20.0) {
        alb = vec3(0.7, 0.5, 1.0);
        emis = vec3(0.7, 0.35, 1.5);
    } else if (id == 21.0) {
        alb = vec3(0.04, 0.04, 0.05);
        rough = 0.15;
    } else if (id == 22.0) {
        alb = vec3(1.0, 0.38, 0.32);
    } else if (id == 23.0) {
        alb = vec3(0.95, 0.95, 0.98);
    } else if (id == 24.0) {
        alb = vec3(0.6, 0.9, 1.0);
        emis = vec3(1.2, 1.8, 2.2) * uShockG;
    }

    vec3 col = alb * (0.06 + diff * sha * key + fill * clamp(dot(n, -light), 0.0, 1.0) * 0.35) * ao;
    col += spec * (0.55 - rough) * key;
    float fres = pow(1.0 - clamp(dot(n, -rd), 0.0, 1.0), 3.0);
    col += fres * vec3(0.12, 0.35, 0.5) * 0.45;
    col += emis;
    return col;
}

void main() {
    vec2 frag = gl_FragCoord.xy;
    vec2 ndc = (frag / uRes) * 2.0 - 1.0;
    float tany = tan(radians(uFov) * 0.5);
    vec3 rd = normalize(uForward + uRight * ndc.x * uAspect * tany + uUp * ndc.y * tany);
    vec3 ro = uCamPos;

    float t = 0.02;
    float id = 0.0;
    vec3 hitP = ro;
    bool hit = false;
    for (int i = 0; i < 52; i++) {
        vec3 p = ro + rd * t;
        Hit h = mapHit(p);
        if (h.d < 0.0025) {
            hit = true;
            id = h.id;
            hitP = p;
            break;
        }
        t += max(h.d * 0.92, 0.012);
        if (t > 70.0) break;
    }

    vec3 col;
    float depth = 1.0;
    if (!hit) {
        col = sky(rd);
        gl_FragDepth = 1.0;
    } else {
        vec3 n = calcNormal(hitP);
        col = shade(hitP, n, rd, id);
        float fog = 1.0 - exp(-0.012 * t);
        col = mix(col, sky(rd), fog);
        vec4 clip = uProj * uView * vec4(hitP, 1.0);
        gl_FragDepth = clamp(clip.z / clip.w * 0.5 + 0.5, 0.0, 1.0);
    }
    outColor = vec4(col, 1.0);
}
