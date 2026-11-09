#ifndef OVERLAY_MEDIA_H
#define OVERLAY_MEDIA_H
#include <stdbool.h>
#include <stdint.h>

/* Local image/animation source, independent of GSR and OpenGL. */
typedef struct Media Media;
typedef struct {
    const uint8_t *rgba;
    int width, height;
    double start;
} MediaFrame;
Media *media_open(const char *path);
/* Monotonic playback time in seconds, relative to the first frame.
   Returns 1 when changed, 0 otherwise, -1 on decode error. Holds last frame at EOF. */
int media_advance(Media *media, double seconds);
MediaFrame media_current(const Media *media);
void media_close(Media *media);
#endif
