#version 330

in vec2 fragTexCoord;
in vec4 fragColor;

out vec4 finalColor;

uniform sampler2D texture0;
uniform vec2 center;
uniform float radius;
uniform float force;
uniform float aspectRatio;

void main()
{
    vec2 uv = fragTexCoord;
    vec2 dir = uv - center;
    dir.x *= aspectRatio;
    
    float dist = length(dir);
    float width = 0.08;
    
    if (dist > 0.0 && dist < radius + width && dist > radius - width) {
        float diff = (dist - radius) / width;
        float offset = (1.0 - abs(diff)) * force;
        
        vec2 offsetVec = normalize(dir) * offset;
        offsetVec.x /= aspectRatio;
        uv -= offsetVec;
    }
    
    finalColor = texture(texture0, uv) * fragColor;
}