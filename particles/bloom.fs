#version 330

in vec2 fragTexCoord;
in vec4 fragColor;

out vec4 finalColor;

uniform sampler2D texture0;
uniform vec2 renderSize;

void main()
{
    vec4 sum = vec4(0.0);
    vec2 texelSize = 1.0 / renderSize;
    
    // Simple single-pass bloom (box blur approximation)
    // Sample a grid around the pixel to create a glow
    for (float x = -2.0; x <= 2.0; x+=1.0)
    {
        for (float y = -2.0; y <= 2.0; y+=1.0)
        {
            sum += texture(texture0, fragTexCoord + vec2(x, y) * texelSize * 2.0);
        }
    }
    
    vec4 blur = sum / 25.0;
    vec4 source = texture(texture0, fragTexCoord);
    
    // Combine: Original + Blur * Intensity
    finalColor = source + blur * 0.8;
}
