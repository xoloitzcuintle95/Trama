#define _POSIX_C_SOURCE 200809L
#include <gsr/plugin.h>
#define GL_GLEXT_PROTOTYPES
#include <GL/gl.h>
#include <GL/glext.h>
#include "media.h"
#include <errno.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

typedef struct {
    Media *media;
    GLuint program, vao, vbo, texture;
    int x, y, width;
    double started;
    bool first, failed;
} Overlay;

static double now(void) {
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return t.tv_sec + t.tv_nsec / 1e9;
}

static bool setting(const char *name, int fallback, int *out) {
    const char *s = getenv(name);
    if (!s) { *out = fallback; return true; }
    char *end;
    errno = 0;
    long n = strtol(s, &end, 10);
    if (errno || !*s || *end || n < 0 || n > 16384) {
        fprintf(stderr, "overlay: %s must be an integer between 0 and 16384\n", name);
        return false;
    }
    *out = (int)n;
    return true;
}

static GLuint shader(GLenum type, const char *prefix, const char *body) {
    GLuint s = glCreateShader(type);
    const char *sources[] = {prefix, body};
    glShaderSource(s, 2, sources, NULL);
    glCompileShader(s);
    GLint ok;
    glGetShaderiv(s, GL_COMPILE_STATUS, &ok);
    if (!ok) {
        char log[2048]; glGetShaderInfoLog(s, sizeof(log), NULL, log);
        fprintf(stderr, "overlay: shader: %s\n", log);
        glDeleteShader(s);
        return 0;
    }
    return s;
}

/* GSR has already captured the desktop into this framebuffer. Composite onto
   it without clearing. Separate alpha factors preserve an opaque desktop's
   alpha, including under partially transparent sources, for final conversion. */
static void draw(const gsr_plugin_draw_params *params, void *userdata) {
    Overlay *o = userdata;
    if (o->failed || !params->width || !params->height) return;
    if (o->first) o->started = now();
    int changed = media_advance(o->media, now() - o->started);
    if (changed < 0) { o->failed = true; return; }
    MediaFrame f = media_current(o->media);
    GLint program, vao, buffer, active, texture, unpack;
    GLint src_rgb, dst_rgb, src_alpha, dst_alpha, equation_rgb, equation_alpha;
    GLboolean blend = glIsEnabled(GL_BLEND), scissor = glIsEnabled(GL_SCISSOR_TEST);
    glGetIntegerv(GL_CURRENT_PROGRAM, &program);
    glGetIntegerv(GL_VERTEX_ARRAY_BINDING, &vao);
    glGetIntegerv(GL_ARRAY_BUFFER_BINDING, &buffer);
    glGetIntegerv(GL_ACTIVE_TEXTURE, &active);
    glGetIntegerv(GL_UNPACK_ALIGNMENT, &unpack);
    glGetIntegerv(GL_BLEND_SRC_RGB, &src_rgb);
    glGetIntegerv(GL_BLEND_DST_RGB, &dst_rgb);
    glGetIntegerv(GL_BLEND_SRC_ALPHA, &src_alpha);
    glGetIntegerv(GL_BLEND_DST_ALPHA, &dst_alpha);
    glGetIntegerv(GL_BLEND_EQUATION_RGB, &equation_rgb);
    glGetIntegerv(GL_BLEND_EQUATION_ALPHA, &equation_alpha);
    glActiveTexture(GL_TEXTURE0);
    glGetIntegerv(GL_TEXTURE_BINDING_2D, &texture);
    glEnable(GL_BLEND);
    glBlendEquationSeparate(GL_FUNC_ADD, GL_FUNC_ADD);
    glBlendFuncSeparate(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA, GL_ONE, GL_ONE_MINUS_SRC_ALPHA);
    glDisable(GL_SCISSOR_TEST);
    glBindTexture(GL_TEXTURE_2D, o->texture);
    glPixelStorei(GL_UNPACK_ALIGNMENT, 1);
    if (o->first)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, f.width, f.height, 0, GL_RGBA, GL_UNSIGNED_BYTE, f.rgba);
    else if (changed)
        glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, f.width, f.height, GL_RGBA, GL_UNSIGNED_BYTE, f.rgba);
    float left = 2.0f * o->x / params->width - 1.0f;
    float right = 2.0f * (o->x + o->width) / params->width - 1.0f;
    /* GSR's encoded row 0 is texture row 0 (GL lower row), without a readback
       flip. Define x/y in recording coordinates, not a window's framebuffer. */
    float top = -1.0f + 2.0f * o->y / params->height;
    float bottom = top + 2.0f * o->width * f.height / f.width / params->height;
    const GLfloat vertices[] = {
        left,top,0,0, left,bottom,0,1, right,top,1,0, right,bottom,1,1
    };
    glBindVertexArray(o->vao);
    glBindBuffer(GL_ARRAY_BUFFER, o->vbo);
    glBufferSubData(GL_ARRAY_BUFFER, 0, sizeof(vertices), vertices);
    glUseProgram(o->program);
    glDrawArrays(GL_TRIANGLE_STRIP, 0, 4);
    glUseProgram(program);
    glBindVertexArray(vao);
    glBindBuffer(GL_ARRAY_BUFFER, buffer);
    glBindTexture(GL_TEXTURE_2D, texture);
    glActiveTexture(active);
    glPixelStorei(GL_UNPACK_ALIGNMENT, unpack);
    glBlendFuncSeparate(src_rgb, dst_rgb, src_alpha, dst_alpha);
    glBlendEquationSeparate(equation_rgb, equation_alpha);
    if (!blend) glDisable(GL_BLEND);
    if (scissor) glEnable(GL_SCISSOR_TEST);
    o->first = false;
}

static bool damaged(void *userdata) {
    return !((Overlay *)userdata)->failed;
}

void gsr_plugin_deinit(void *userdata) {
    Overlay *o = userdata;
    if (!o) return;
    glDeleteProgram(o->program);
    glDeleteVertexArrays(1, &o->vao);
    glDeleteBuffers(1, &o->vbo);
    glDeleteTextures(1, &o->texture);
    media_close(o->media);
    free(o);
}

bool gsr_plugin_init(const gsr_plugin_init_params *params, gsr_plugin_init_return *ret) {
    const char *path = getenv("GSR_OVERLAY_FILE");
    if (!path || !*path || params->color_depth != GSR_PLUGIN_COLOR_DEPTH_8_BITS) {
        fprintf(stderr, "overlay: set GSR_OVERLAY_FILE; this prototype requires SDR 8-bit\n");
        return false;
    }
    Overlay *o = calloc(1, sizeof(*o));
    if (!o) return false;
    if (!setting("GSR_OVERLAY_X", 32, &o->x) || !setting("GSR_OVERLAY_Y", 32, &o->y) ||
        !setting("GSR_OVERLAY_WIDTH", 320, &o->width) || o->width == 0) goto error;
    o->media = media_open(path);
    if (!o->media) goto error;
    const char *prefix = params->graphics_api == GSR_PLUGIN_GRAPHICS_API_EGL_ES
        ? "#version 300 es\nprecision mediump float;\n" : "#version 130\n";
    GLuint vs = shader(GL_VERTEX_SHADER, prefix,
        "in vec2 position; in vec2 uv; out vec2 texcoord;\n"
        "void main(){gl_Position=vec4(position,0,1); texcoord=uv;}\n");
    GLuint fs = shader(GL_FRAGMENT_SHADER, prefix,
        "in vec2 texcoord; uniform sampler2D image; out vec4 color;\n"
        "void main(){color=texture(image,texcoord);}\n");
    if (!vs || !fs) { glDeleteShader(vs); glDeleteShader(fs); goto error; }
    o->program = glCreateProgram();
    glAttachShader(o->program, vs); glAttachShader(o->program, fs);
    glBindAttribLocation(o->program, 0, "position");
    glBindAttribLocation(o->program, 1, "uv");
    glLinkProgram(o->program);
    glDeleteShader(vs); glDeleteShader(fs);
    GLint ok;
    glGetProgramiv(o->program, GL_LINK_STATUS, &ok);
    if (!ok) {
        char log[2048]; glGetProgramInfoLog(o->program, sizeof(log), NULL, log);
        fprintf(stderr, "overlay: link: %s\n", log); goto error;
    }
    GLint vao, buffer, active, texture;
    glGetIntegerv(GL_VERTEX_ARRAY_BINDING, &vao);
    glGetIntegerv(GL_ARRAY_BUFFER_BINDING, &buffer);
    glGetIntegerv(GL_ACTIVE_TEXTURE, &active);
    glActiveTexture(GL_TEXTURE0);
    glGetIntegerv(GL_TEXTURE_BINDING_2D, &texture);
    glGenVertexArrays(1, &o->vao); glBindVertexArray(o->vao);
    glGenBuffers(1, &o->vbo); glBindBuffer(GL_ARRAY_BUFFER, o->vbo);
    glBufferData(GL_ARRAY_BUFFER, 16 * sizeof(float), NULL, GL_DYNAMIC_DRAW);
    glEnableVertexAttribArray(0); glEnableVertexAttribArray(1);
    glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 4*sizeof(float), (void *)0);
    glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 4*sizeof(float), (void *)(2*sizeof(float)));
    glGenTextures(1, &o->texture); glBindTexture(GL_TEXTURE_2D, o->texture);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
    glBindTexture(GL_TEXTURE_2D, texture); glActiveTexture(active);
    glBindVertexArray(vao); glBindBuffer(GL_ARRAY_BUFFER, buffer);
    o->first = true;
    ret->name = "local-media-overlay";
    ret->version = 1;
    ret->userdata = o;
    ret->draw = draw;
    ret->is_damaged = damaged;
    ret->clear_damage = NULL;
    return true;
error:
    gsr_plugin_deinit(o);
    return false;
}
