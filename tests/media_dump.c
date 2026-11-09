#include "../src/media.h"
#include <stdio.h>
#include <stdlib.h>
int main(int argc, char **argv) {
    if (argc != 3) return 2;
    Media *m = media_open(argv[1]);
    if (!m) return 1;
    if (media_advance(m, strtod(argv[2], NULL)) < 0) { media_close(m); return 1; }
    MediaFrame f = media_current(m);
    fprintf(stderr, "%d %d %.9f\n", f.width, f.height, f.start);
    size_t size = (size_t)f.width * f.height * 4;
    int result = fwrite(f.rgba, 1, size, stdout) == size ? 0 : 1;
    media_close(m);
    return result;
}
