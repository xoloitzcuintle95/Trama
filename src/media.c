#include "media.h"
#include <libavformat/avformat.h>
#include <libavcodec/avcodec.h>
#include <libswscale/swscale.h>
#include <libavutil/opt.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

struct Media {
    AVFormatContext *format;
    AVCodecContext *decoder;
    AVPacket *packet;
    AVFrame *frame;
    struct SwsContext *scale;
    int stream;
    bool draining, have_next, failed;
    uint8_t *current, *next;
    int width, height;
    double current_start, next_start, origin, next_fallback;
    bool have_origin;
    char *path;
    unsigned plays, completed;
    double offset;
};

static bool skip_blocks(FILE *file) {
    int size;
    while ((size = fgetc(file)) > 0)
        for (int i = 0; i < size; ++i) if (fgetc(file) == EOF) return false;
    return size == 0;
}

/* Parse GIF block boundaries, never search compressed bytes for a magic string.
   NETSCAPE count means repeats AFTER the initial play; zero means infinite.
   FFmpeg 6.1's demuxer treats finite counts as total plays, so handle loops here. */
static bool gif_plays(const char *path, unsigned *plays) {
    FILE *file = fopen(path, "rb");
    if (!file) return false;
    bool ok = false;
    unsigned char header[13], data[255];
    if (fread(header, 1, 13, file) != 13 ||
        (memcmp(header, "GIF87a", 6) && memcmp(header, "GIF89a", 6))) goto done;
    if (header[10] & 0x80)
        if (fseek(file, 3 * (1 << ((header[10] & 7) + 1)), SEEK_CUR)) goto done;
    *plays = 1;
    for (;;) {
        int tag = fgetc(file);
        if (tag == 0x3b) { ok = true; break; }
        if (tag == 0x2c) {
            if (fread(data, 1, 9, file) != 9) break;
            if (data[8] & 0x80)
                if (fseek(file, 3 * (1 << ((data[8] & 7) + 1)), SEEK_CUR)) break;
            if (fgetc(file) == EOF || !skip_blocks(file)) break;
        } else if (tag == 0x21) {
            int type = fgetc(file);
            if (type == EOF) break;
            if (type == 0xff) {
                int length = fgetc(file);
                if (length < 0 || fread(data, 1, length, file) != (size_t)length) break;
                bool loop = length == 11 && (!memcmp(data, "NETSCAPE2.0", 11) ||
                                               !memcmp(data, "ANIMEXTS1.0", 11));
                if (loop) {
                    length = fgetc(file);
                    if (length < 0 || fread(data, 1, length, file) != (size_t)length) break;
                    if (length != 3 || data[0] != 1) break;
                    unsigned repeats = data[1] | ((unsigned)data[2] << 8);
                    *plays = repeats ? repeats + 1 : 0;
                }
            }
            if (!skip_blocks(file)) break;
        } else break;
    }
done:
    fclose(file);
    return ok;
}

static int open_format(Media *m) {
    AVDictionary *options = NULL;
    av_dict_set(&options, "protocol_whitelist", "file", 0);
    av_dict_set(&options, "ignore_loop", "1", 0);
    /* Preserve 10 ms GIF delays; explicit zero/absent delay uses FFmpeg's 100 ms. */
    av_dict_set(&options, "min_delay", "0", 0);
    int result = avformat_open_input(&m->format, m->path, NULL, &options);
    av_dict_free(&options);
    return result;
}

static int fail(int error) {
    char message[AV_ERROR_MAX_STRING_SIZE];
    av_strerror(error, message, sizeof(message));
    fprintf(stderr, "overlay: decode: %s\n", message);
    return -1;
}

/* FFmpeg owns GIF disposal and transparent palette. Only two
   RGBA canvases are retained; long animations don't expand into a frame cache. */
static int read_next(Media *m) {
    for (;;) {
        int result = avcodec_receive_frame(m->decoder, m->frame);
        if (result == 0) break;
        if (result == AVERROR_EOF) {
            ++m->completed;
            if (m->plays && m->completed >= m->plays) return 0;
            m->offset = m->next_fallback - m->origin;
            avformat_close_input(&m->format);
            result = open_format(m);
            if (result < 0) return fail(result);
            avcodec_flush_buffers(m->decoder);
            m->draining = false;
            continue;
        }
        if (result != AVERROR(EAGAIN)) return fail(result);
        if (m->draining) return fail(AVERROR_INVALIDDATA);
        do {
            result = av_read_frame(m->format, m->packet);
            if (result < 0) break;
            if (m->packet->stream_index == m->stream) break;
            av_packet_unref(m->packet);
        } while (true);
        if (result < 0) {
            if (result != AVERROR_EOF) return fail(result);
            m->draining = true;
            result = avcodec_send_packet(m->decoder, NULL);
        } else {
            result = avcodec_send_packet(m->decoder, m->packet);
            av_packet_unref(m->packet);
        }
        if (result < 0) return fail(result);
    }
    AVFrame *f = m->frame;
    if (!m->width) {
        /* Explicit proof-of-concept limit: at most 4096x4096 per canvas. */
        if (f->width <= 0 || f->height <= 0 || f->width > 4096 || f->height > 4096)
            return fail(AVERROR(EINVAL));
        m->width = f->width;
        m->height = f->height;
        size_t size = (size_t)m->width * m->height * 4;
        m->current = malloc(size);
        m->next = malloc(size);
        if (!m->current || !m->next) return fail(AVERROR(ENOMEM));
    }
    if (f->width != m->width || f->height != m->height)
        return fail(AVERROR(EINVAL));
    m->scale = sws_getCachedContext(m->scale, f->width, f->height, f->format,
        f->width, f->height, AV_PIX_FMT_RGBA, SWS_POINT, NULL, NULL, NULL);
    if (!m->scale) return fail(AVERROR(ENOMEM));
    uint8_t *destination[] = {m->next};
    int stride[] = {m->width * 4};
    if (sws_scale(m->scale, (const uint8_t *const *)f->data, f->linesize,
                  0, f->height, destination, stride) != m->height)
        return fail(AVERROR_INVALIDDATA);
    double base = av_q2d(m->format->streams[m->stream]->time_base);
    double start = f->best_effort_timestamp == AV_NOPTS_VALUE ? m->next_fallback - m->offset
        : f->best_effort_timestamp * base;
    if (!m->have_origin) {
        m->origin = start;
        m->have_origin = true;
    }
    m->next_start = start - m->origin + m->offset;
    double duration = f->duration > 0 ? f->duration * base : 0.01;
    m->next_fallback = start + duration + m->offset;
    av_frame_unref(f);
    return 1;
}

Media *media_open(const char *path) {
    Media *m = calloc(1, sizeof(*m));
    if (!m) return NULL;
    size_t length = strlen(path) + 1;
    m->path = malloc(length);
    if (!m->path) goto error;
    memcpy(m->path, path, length);
    m->plays = 1;
    int result = open_format(m);
    if (result < 0) { fail(result); goto error; }
    if (!strcmp(m->format->iformat->name, "gif") && !gif_plays(path, &m->plays)) {
        fail(AVERROR_INVALIDDATA); goto error;
    }
    result = avformat_find_stream_info(m->format, NULL);
    if (result < 0) { fail(result); goto error; }
    const AVCodec *codec = NULL;
    m->stream = av_find_best_stream(m->format, AVMEDIA_TYPE_VIDEO, -1, -1, &codec, 0);
    if (m->stream < 0) { fail(m->stream); goto error; }
    m->decoder = avcodec_alloc_context3(codec);
    if (!m->decoder) goto error;
    result = avcodec_parameters_to_context(m->decoder, m->format->streams[m->stream]->codecpar);
    if (result < 0) { fail(result); goto error; }
    m->decoder->thread_count = 1;
    if ((result = avcodec_open2(m->decoder, codec, NULL)) < 0) { fail(result); goto error; }
    m->frame = av_frame_alloc();
    m->packet = av_packet_alloc();
    if (!m->frame || !m->packet || read_next(m) != 1) goto error;
    uint8_t *swap = m->current; m->current = m->next; m->next = swap;
    m->current_start = m->next_start;
    result = read_next(m);
    if (result < 0) goto error;
    m->have_next = result == 1;
    return m;
error:
    media_close(m);
    return NULL;
}

int media_advance(Media *m, double seconds) {
    if (m->failed || !isfinite(seconds) || seconds < m->current_start) return -1;
    int changed = 0;
    /* Bound catch-up work after long recording pauses. Subsequent draws catch up. */
    unsigned steps = 0;
    while (m->have_next && seconds >= m->next_start && steps++ < 256) {
        if (m->next_start <= m->current_start) {
            m->failed = true;
            return fail(AVERROR_INVALIDDATA);
        }
        uint8_t *swap = m->current; m->current = m->next; m->next = swap;
        m->current_start = m->next_start;
        changed = 1;
        int result = read_next(m);
        if (result < 0) { m->failed = true; return -1; }
        m->have_next = result == 1;
    }
    return changed;
}

MediaFrame media_current(const Media *m) {
    return (MediaFrame){m->current, m->width, m->height, m->current_start};
}

void media_close(Media *m) {
    if (!m) return;
    free(m->current); free(m->next);
    free(m->path);
    sws_freeContext(m->scale);
    av_packet_free(&m->packet);
    av_frame_free(&m->frame);
    avcodec_free_context(&m->decoder);
    avformat_close_input(&m->format);
    free(m);
}
